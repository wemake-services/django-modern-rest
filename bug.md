# Bugs found while investigating conditional `FileMetadata` schemas

Found while working on [PR #1278](https://github.com/wemake-services/django-modern-rest/pull/1278) /
[issue #1275](https://github.com/wemake-services/django-modern-rest/issues/1275).
These bite regardless of which schema-generation design is chosen.

---

## Bug 1 — content-type key mismatch between runtime and OpenAPI (main bug)

### Description

The `conditional_type({...})` mapping keys are matched against two different
strings depending on the code path:

- **OpenAPI generation** uses the bare `parser.content_type`, e.g.
  `'multipart/form-data'`:
  - `FileMetadataComponent.get_schema` — `dmr/components.py:911-950`,
    `conditional_schemas.get(parser.content_type, schema)`;
  - parsers are keyed by bare content type in `metadata.parsers`
    (`dmr/validation/endpoint_metadata.py:415-436`).
- **Runtime** matches the raw `Content-Type` request header, *including
  parameters*:
  - `SerializerContext._validate_context` — `dmr/internal/context.py:182-190`,
    `self._conditional_combined_models.get(request.headers['Content-Type'])`;
  - `FileMetadataComponent.provide_context_data` — `dmr/components.py:861-862`,
    `conditional_types.get(parser.content_type, field_model)` (bare key here,
    but the *test* keys the mapping by the full header, see below).

For multipart the real header always carries a boundary parameter — Django's
test constant `MULTIPART_CONTENT` is
`'multipart/form-data; boundary=BoUnDaRyStRiNg'` (`django/test/client.py:43`).
So a single mapping cannot satisfy both consumers:

- Key the mapping by `MULTIPART_CONTENT` (what the current tests do) → runtime
  matches, but `conditional_schemas.get('multipart/form-data')` **misses** and
  schema generation falls back to the union schema. This is visible in the
  current snapshot: the `multipart/form-data` media type renders as
  `{"anyOf": [...], "properties": {}}` instead of the multipart model
  (`tests/test_unit/test_openapi/__snapshots__/test_files_snapshots.ambr:318-329`).
- Key the mapping by bare `'multipart/form-data'` → schema generation matches,
  but runtime model selection and `__dmr_force_list__` resolution **miss** and
  fall back to the default model.

Note the existing content negotiation already solves this correctly:
`RequestNegotiator._decide` (`dmr/negotiation.py:88-111`) strips/matches media
type parameters via `dmr/internal/media_compat.py`. The conditional-type
lookups just don't use it.

### Repro

```python
from typing import Annotated, TypeAlias

import pydantic
from django.test.client import MULTIPART_CONTENT, RequestFactory

from dmr.components import FileMetadata
from dmr.controller import Controller
from dmr.negotiation import conditional_type


class _MultipartFiles(pydantic.BaseModel):
    first: dict
    second: dict


class _OctetFile(pydantic.BaseModel):
    uploaded_file: dict


_Files: TypeAlias = Annotated[
    _MultipartFiles | _OctetFile,
    conditional_type({
        # Keyed by the full header so that *runtime* matching works:
        MULTIPART_CONTENT: _MultipartFiles,
        'application/octet-stream': _OctetFile,
    }),
]


class FilesController(Controller[...]):
    def post(self, parsed_file_metadata: FileMetadata[_Files]) -> ...:
        ...


# 1) OpenAPI: generate the schema for this controller (or run the
#    existing snapshot test) and inspect
#    paths./...post.requestBody.content['multipart/form-data'].schema
#    EXPECTED: the _MultipartFiles object schema with binary properties.
#    ACTUAL:   {"anyOf": [...], "properties": {}} — the union fallback,
#    because conditional_schemas.get('multipart/form-data') missed the
#    MULTIPART_CONTENT key.

# 2) Runtime (flip side): re-key the mapping with bare
#    'multipart/form-data' instead of MULTIPART_CONTENT and POST a
#    multipart request:
#      RequestFactory().post('/', data={...})  # sends the boundary header
#    Now SerializerContext._validate_context picks the *default* combined
#    model, and __dmr_force_list__ from _MultipartFiles is ignored.
```

### Suggested fix

One shared normalization rule (strip media-type parameters, reusing
`dmr/internal/media_compat.py` like `RequestNegotiator._decide` does) applied
in all four lookup sites: `SerializerContext._build_type_map` /
`_validate_context`, `FileMetadataComponent.provide_context_data`, and
`FileMetadataComponent.get_schema`.

---

## Bug 2 — schema registration asymmetry + duplicate components from forced `title`

### Description

`FileMetadataComponent.get_schema` (`dmr/components.py:911-950`) inlines the
main model with `skip_registration=True`, but *registers* every conditional
model into `components/schemas`. The conditional wrapper models (like
`OctetFileModel[...]`) are validation-only artifacts and should not leak into
the public schema — the response side already handles this with
`registries.schema.try_unregister(...)` (`dmr/files.py:177-180`).

Additionally, forcing a pydantic `title` on a *generic* wrapper
(`model_config = ConfigDict(title='OctetFileModel_WithMeta')` in
`tests/infra/octet.py`) makes the registry produce **two identical component
schemas for one type**: `OctetFileModel_WithMeta` (from
`schema_name` = JSON-schema title, `dmr/plugins/pydantic/schema.py:36-42`) and
`OctetFileModel__OctetFileMeta_` (pydantic's `$defs` key). Worse, two
different parametrizations (`OctetFileModel[A]`, `OctetFileModel[B]`) would
share the forced title and hit `Different schemas under a single name` in
`SchemaRegistry.register` (`dmr/openapi/core/registry.py:70-87`).

### Repro

```python
# 1) Duplicate components: run the current branch's snapshot test
#    tests/test_unit/test_openapi/test_files_snapshots.py and inspect
#    components/schemas in the output (.ambr): both
#    'OctetFileModel_WithMeta' and 'OctetFileModel__OctetFileMeta_'
#    are present with identical bodies.

# 2) Name collision: declare two endpoints using two parametrizations
#    of the titled generic:
class _MetaA(pydantic.BaseModel):
    uploaded_file: dict

class _MetaB(pydantic.BaseModel):
    uploaded_file: list

# OctetFileModel has ConfigDict(title='OctetFileModel_WithMeta')
FileMetadata[OctetFileModel[_MetaA]]  # endpoint 1
FileMetadata[OctetFileModel[_MetaB]]  # endpoint 2
# Generating the OpenAPI schema raises:
#   Different schemas under a single name 'OctetFileModel_WithMeta'
```

### Suggested fix

Do not force a `title` on the generic wrapper. Whatever design is chosen for
raw-file schemas, unregister the wrapper model after collapsing the media
schema (same `try_unregister` pattern as `FileResponseSpec.get_schema`), and
make registration symmetric between the main and conditional models.

---

## Bug 3 — `Body` + `FileMetadata` `allOf` merge is meaningless for raw bodies

### Description

`ComponentParserGenerator._merge_contents`
(`dmr/openapi/generators/component_parsers.py:173-192`) combines `Body` and
`FileMetadata` request bodies into `allOf` per media type. The path is
guarded by `# pragma: no cover` with a TODO admitting it is untested for
conditional file types (lines 184-186).

For a raw content type (`application/octet-stream`) this merge can never be
correct: the request body is a single byte stream, it cannot simultaneously
satisfy a JSON `Body` model and be a raw file. Once raw-file schemas collapse
to `{"type": "string", "format": "binary"}`, wrapping that into
`allOf` with an object schema produces an unsatisfiable schema.

### Repro

```python
class _Payload(pydantic.BaseModel):
    name: str

class FilesController(Controller[...]):
    # Declaring both components on one endpoint whose parsers include a
    # raw octet-stream parser:
    def post(
        self,
        body: Body[_Payload],
        parsed_file_metadata: FileMetadata[OctetFileModel[_Meta]],
    ) -> ...:
        ...

# Generated requestBody.content['application/octet-stream'].schema becomes
#   {"allOf": [<binary string schema>, {"$ref": ..._Payload}]}
# which no request can ever satisfy.
```

### Suggested fix

Import-time validation error (in `FileMetadataComponent.validate` or the
merge itself): a content type parsed by a raw single-file parser may not carry
both `Body` and `FileMetadata` components.

---

## Minor issues

- `dmr/components.py:813` references docs label `conditional-file-types`,
  which does not exist anywhere in `docs/` (only `.. _conditional-types:` at
  `docs/pages/negotiation.rst:221`) — Sphinx dangling reference.
- `docs/pages/components/files.rst:11-19` still claims raw single-file
  uploads are unsupported; needs updating once this lands.
- Working-tree debris on the branch: stray `assert False` at
  `tests/test_unit/test_components/test_file_metadata.py:678`.
