import json
from typing import Any, final

from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.utils.module_loading import import_string
from typing_extensions import override


@final
class Command(BaseCommand):
    """
    Management command to export an OpenAPI schema as JSON or YAML.

    .. versionadded:: 0.8.0
    .. versionchanged:: 0.9.0
        Added ``--no-ensure-ascii`` option.

    """

    help = 'Export an OpenAPI schema.'

    @override
    def add_arguments(self, parser: CommandParser) -> None:
        """Add schema, format, indent, and sort-keys arguments."""
        parser.add_argument(
            'schema',
            help='Import path to the OpenAPI schema.',
        )
        parser.add_argument(
            '--format',
            choices=['json', 'yaml'],
            default='json',
            dest='format',
            help='Desired output format. Default: %(default)s',
        )
        # All defaults match the `json.dumps` defaults:
        parser.add_argument(
            '--indent',
            type=int,
            default=0,
            dest='indent',
            help=(
                'How many spaces we should use for pretty print indentation. '
                'Default: %(default)s'
            ),
        )
        parser.add_argument(
            '--sort-keys',
            action='store_true',
            default=False,
            dest='sort_keys',
            help='Should we sort dictionaries based on keys.',
        )
        parser.add_argument(
            '--no-ensure-ascii',
            action='store_true',
            default=False,
            dest='no_ensure_ascii',
            help='Should we properly escape all non-ascii symbols.',
        )

    @override
    def handle(self, *args: Any, **options: Any) -> None:  # noqa: WPS110
        """Load schema by import path and write it to stdout as JSON or YAML."""
        schema_path = options['schema']

        converted_schema = import_string(
            schema_path.replace(':', '.'),
        ).convert()

        if options['format'] == 'yaml':
            try:
                import yaml  # noqa: PLC0415
            except ImportError as exc:  # pragma: no cover
                raise CommandError(
                    'Looks like `pyyaml` is not installed, consider using '
                    "`pip install 'django-modern-rest[openapi]'`",
                ) from exc

            self.stdout.write(
                yaml.safe_dump(
                    converted_schema,
                    indent=options['indent'],
                    sort_keys=options['sort_keys'],
                ),
            )
        else:
            self.stdout.write(
                json.dumps(
                    converted_schema,
                    indent=options['indent'],
                    sort_keys=options['sort_keys'],
                    ensure_ascii=not options['no_ensure_ascii'],
                ),
            )
