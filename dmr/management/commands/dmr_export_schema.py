import json
from typing import Any, final

from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.utils.module_loading import import_string
from typing_extensions import override


@final
class Command(BaseCommand):
    """Management command to export an OpenAPI schema as JSON or YAML."""

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
        )
        parser.add_argument(
            '--indent',
            type=int,
            default=None,
        )
        parser.add_argument(
            '--sort-keys',
            action='store_true',
            default=False,
        )

    @override
    def handle(self, *args: Any, **options: Any) -> None:  # noqa: WPS110
        """Load schema by import path and write it to stdout as JSON or YAML."""
        schema_path = options['schema']
        indent = options['indent']
        sort_keys = options['sort_keys']

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
                    sort_keys=sort_keys,
                    indent=indent,
                ),
            )
        else:
            self.stdout.write(
                json.dumps(
                    converted_schema,
                    indent=indent,
                    sort_keys=sort_keys,
                ),
            )
