# Design: conditional `FileMetadata` and OpenAPI schema generation

Context: [PR #1278](https://github.com/wemake-services/django-modern-rest/pull/1278),
[issue #1275](https://github.com/wemake-services/django-modern-rest/issues/1275).

`FileMetadata` should support conditional file bodies based on `Content-Type`,
just like regular `Body` does. Runtime support mostly exists (parsing +
`__dmr_force_list__` resolution per conditional model). The open design
question is OpenAPI schema generation: `OctetStreamParser`
(`application/octet-stream`) requires a fundamentally different schema shape —
a single file, with no intermediate object schema, just a bare
`{"type": "string", "format": "binary"}` media schema.

## Where the tension actually is

The whole file-schema shape is decided in one place:
`FileMetadataComponent.get_schema` (`dmr/components.py:911`) builds
`content={parser.content_type: self.schema_metadata.media_type(...)}`, and
`FileBody.media_type` (`dmr/files.py:48`) unconditionally assumes the model is
an *object* — it resolves the ref and rewrites every property to
`format: binary`. For `application/octet-stream` the correct media schema is a
bare `{"type": "string", "format": "binary"}` — no `type: object`, no
`properties`, no `required`, no `title`, no `encoding` (`encoding` is only
meaningful for `multipart/*` and `application/x-www-form-urlencoded`).

Meanwhile the *runtime* model must stay an object, because
`extract_files_metadata` (`dmr/internal/django.py:188`) returns
`{field_name: {...metadata}}` — hence the `OctetFileModel[_ModelT]` wrapper
with the single `uploaded_file` field. So the design problem is precisely:
**the schema generator must erase one wrapper level that validation still
needs**, and it must know *per content type* when to do that.

One observation that matters for the "should we support it at all" question:
`FileBody.media_type` already receives the `parser` as an argument, and
`FileResponseSpec.get_schema` (`dmr/files.py:163-181`) already does exactly
this collapse on the *response* side — it replaces the media schema with
`Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.BINARY)` and calls
`registries.schema.try_unregister(...)` to remove the fake model from
`components/schemas`. So a request-side equivalent is not a new concept; it is
filling in a symmetry gap.

---

## Option 0 — declare it out of scope

Ship PR #1278 as runtime-only support (parsing + `__dmr_force_list__`
resolution), keep `OctetStreamParser` in `tests/infra/`, and document that
schema generation for raw single-file uploads emits the wrapper-object schema
(or nothing). `docs/pages/components/files.rst:15-19` already says raw
single-file uploads are "not supported yet, users can implement their own
`Parser`".

The honest downside: a user who follows that advice gets a *silently wrong*
OpenAPI schema — codegen clients would try to send a JSON object
`{"uploaded_file": ...}` as the octet-stream body. Wrong-but-generated is
worse than absent, so if this option is picked, at least emit nothing for
content types whose parser is raw, rather than the wrapper object.

### Example

```rst
.. docs/pages/components/files.rst

.. warning::
   Raw single-file uploads (``application/octet-stream``) are parsed at
   runtime, but are **excluded from the generated OpenAPI schema**.
   Implement a custom ``ComponentParser.get_schema`` if you need it.
```

```python
# dmr/components.py, FileMetadataComponent.get_schema — skip raw parsers:
content = {
    parser.content_type: self.schema_metadata.media_type(...)
    for parser in metadata.parsers.values()
    if not isinstance(parser, SupportsRawFileParsing)  # emit nothing
}
```

---

## Option A — parser-owned `FileBody` (recommended)

Give `SupportsFileParsing` an optional class attribute, e.g.
`schema_metadata: ClassVar[type[FileBody]] = FileBody`, and make
`FileMetadataComponent.get_schema` consult the parser's class before falling
back to its own. Then ship a `RawFileBody(FileBody)` whose `media_type`
ignores the model shape entirely and returns a bare binary schema, and whose
registration step unregisters the wrapper model (copying the
`FileResponseSpec` precedent). `OctetStreamParser` — whether it stays
user-land or moves back into `dmr/parsers.py` — just sets
`schema_metadata = RawFileBody`.

Why this one: the schema shape is intrinsically a property of the *media
type*, not of any particular endpoint or model — `application/octet-stream`
bodies are raw bytes always. Declaring it once on the parser makes every
endpoint correct with zero per-endpoint annotation, and parsers already
contribute OpenAPI-adjacent information via `provide_response_specs`
(`dmr/parsers.py:71`), so this does not break the layering. It also composes
with the existing `FileMetadataComponent(schema_metadata=...)` hook rather
than replacing it.

### Example

```python
# dmr/files.py
@dataclasses.dataclass(slots=True, frozen=True)
class RawFileBody(FileBody):
    """Schema for raw single-file bodies (e.g. ``application/octet-stream``)."""

    @override
    @classmethod
    def media_type(
        cls,
        schema: Reference | Schema,
        model: Any,
        model_meta: tuple[Any, ...],
        parser: Parser,
        context: 'OpenAPIContext',
    ) -> MediaType:
        # The wrapper object exists only for runtime validation of
        # `request.FILES` metadata; the wire format is raw bytes:
        return MediaType(
            schema=Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.BINARY),
        )


# dmr/parsers.py
class SupportsFileParsing(...):
    #: `FileBody` subclass used for OpenAPI schema of this content type.
    schema_metadata: ClassVar[type[FileBody]] = FileBody


class OctetStreamParser(SupportsFileParsing, Parser):
    content_type = 'application/octet-stream'
    schema_metadata: ClassVar[type[FileBody]] = RawFileBody
    ...


# dmr/components.py, FileMetadataComponent.get_schema
content = {
    parser.content_type: getattr(
        parser, 'schema_metadata', self.schema_metadata,
    ).media_type(
        conditional_schemas.get(parser.content_type, schema),
        model, model_meta, parser, context,
    )
    for parser in metadata.parsers.values()
}
```

Usage stays exactly as in the PR — no per-endpoint annotation needed:

```python
_Files: TypeAlias = Annotated[
    _UploadedFiles | OctetFileModel[_OctetFileMeta],
    conditional_type({
        'multipart/form-data': _UploadedFiles,
        ContentType.octet_stream: OctetFileModel[_OctetFileMeta],
    }),
]

class MyController(Controller[...]):
    def post(self, files: FileMetadata[_Files]) -> ...: ...
```

---

## Option B — schema override via `MediaTypeMetadata` on the conditional model

`FileBody.media_type` already looks up `MediaTypeMetadata` on the
per-content-type conditional model (`dmr/files.py:67-74`), and
`conditional_type` mapping values pass through `Annotated` metadata. Extend
`MediaTypeMetadata` with an optional `schema: Schema | None` field that, when
set, replaces the generated media schema wholesale.

Smallest new API surface — one dataclass field — and fully general (users can
override any media schema, not just files). Downsides: per-usage boilerplate
at every endpoint, and the unregistration handling plus a guard skipping the
property-rewrite path are still needed separately. Worth doing *in addition*
to Option A eventually as a general escape hatch, but as the only mechanism it
puts the burden in the wrong place.

### Example

```python
# dmr/openapi/objects/media_type.py
@dataclasses.dataclass(slots=True, frozen=True)
class MediaTypeMetadata:
    ...
    #: When set, replaces the generated schema for this media type entirely:
    schema: Schema | None = None


# user code
_Files: TypeAlias = Annotated[
    _UploadedFiles | OctetFileModel[_OctetFileMeta],
    conditional_type({
        'multipart/form-data': _UploadedFiles,
        ContentType.octet_stream: Annotated[
            OctetFileModel[_OctetFileMeta],
            MediaTypeMetadata(
                schema=Schema(
                    type=OpenAPIType.STRING,
                    format=OpenAPIFormat.BINARY,
                ),
            ),
        ],
    }),
]
```

---

## Option C — per-content-type `schema_metadata` mapping on the component

Let `FileMetadataComponent` accept `Mapping[str, type[FileBody]]` keyed by
content type.

Pass on this: the public `FileMetadata` alias never exposes component
constructor args (no test or doc ever constructs
`FileMetadataComponent(CustomFileBody)`), and it forces users to declare the
content-type mapping *twice* — once in `conditional_type`, once here — with a
desync failure mode.

### Example

```python
# What it would look like (not recommended):
_FilesComponent = FileMetadataComponent(
    schema_metadata={
        'multipart/form-data': FileBody,
        ContentType.octet_stream: RawFileBody,  # duplicated mapping!
    },
)

_Files: TypeAlias = Annotated[
    _UploadedFiles | OctetFileModel[_OctetFileMeta],
    conditional_type({  # ...same keys again here
        'multipart/form-data': _UploadedFiles,
        ContentType.octet_stream: OctetFileModel[_OctetFileMeta],
    }),
    _FilesComponent,
]
```

---

## Option D — global schema registry override

`OpenAPIContext.register_schema(annotation, SchemaCallback)`
(`dmr/openapi/core/context.py:100-126`) already exists and is type-driven, so
a user could map `OctetFileModel[X]` → bare binary today.

But it is per-parametrization, global, and it interacts badly with
`FileBody.media_type`'s property-rewrite (which would then operate on a schema
with no properties and still stamp `properties={}` / keep `required`). Fine as
an undocumented workaround; wrong as the supported answer.

### Example

```python
# user code, at OpenAPI setup time — once per parametrization:
context.register_schema(
    OctetFileModel[_OctetFileMeta],
    Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.BINARY),
    override=True,
)
```

---

## Option E — implicit detection (rejected)

"If the parser is raw and the model has exactly one file field, collapse it."
No API at all, but it is magic: the behavior changes based on field count, and
a two-field model would silently produce a different schema shape.

### Example

```python
# What the magic would look like (rejected):
@classmethod
def media_type(cls, schema, model, model_meta, parser, context) -> MediaType:
    resolved = context.registries.schema.maybe_resolve_reference(schema)
    is_single_field = len(resolved.properties or {}) == 1
    if isinstance(parser, SupportsRawFileParsing) and is_single_field:
        # Silently changes shape when a second field is added:
        return MediaType(
            schema=Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.BINARY),
        )
    ...  # regular object treatment
```

---

## Cross-cutting work needed regardless of the choice

See `bug.md` for full descriptions and repros. Summary:

1. **Content-type key normalization** — OpenAPI lookups use bare
   `parser.content_type`, runtime matches the raw `Content-Type` header
   (with parameters, e.g. multipart boundary). One shared normalization rule
   must serve both.
2. **Registration asymmetry + title hack** — the main model is inlined
   (`skip_registration=True`) but conditional models are registered; forcing a
   pydantic `title` on a generic wrapper yields duplicate component schemas
   and risks `Different schemas under a single name`.
3. **`Body` + `FileMetadata` `allOf` merge guard** — merging a raw-binary
   media schema into `allOf` is meaningless; a raw content type carrying both
   `Body` and `FileMetadata` deserves an import-time validation error.
4. **Docs** — `dmr/components.py:813` references a nonexistent
   `conditional-file-types` label; `docs/pages/components/files.rst` still
   claims single-file uploads are unsupported.

## Bottom line

Support the case, but split it: land PR #1278's runtime support plus the
normalization fix first, then add the parser-owned `FileBody` hook (Option A)
with a shipped `RawFileBody` as the supported way to get bare
`format: binary` schemas — it matches the existing response-side design,
requires no per-endpoint annotation, and keeps `OctetStreamParser` viable as
either a built-in or a documented user-land recipe. Option B's
`MediaTypeMetadata.schema` override is the best second choice if a general
escape hatch is preferred over a file-specific hook.
