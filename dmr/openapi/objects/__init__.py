# Parts of the code in this directory is taken from
# https://github.com/litestar-org/litestar/tree/main/litestar/openapi/spec
# under MIT license.

# Original license:
# https://github.com/litestar-org/litestar/blob/main/LICENSE

# The MIT License (MIT)

# Copyright (c) 2021, 2022, 2023, 2024, 2025, 2026 Litestar Org.

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from django_modern_rest.openapi.objects.callback import Callback as Callback
from django_modern_rest.openapi.objects.components import (
    Components as Components,
)
from django_modern_rest.openapi.objects.contact import Contact as Contact
from django_modern_rest.openapi.objects.discriminator import (
    Discriminator as Discriminator,
)
from django_modern_rest.openapi.objects.encoding import Encoding as Encoding
from django_modern_rest.openapi.objects.enums import (
    OpenAPIFormat as OpenAPIFormat,
)
from django_modern_rest.openapi.objects.enums import (
    OpenAPIType as OpenAPIType,
)
from django_modern_rest.openapi.objects.example import Example as Example
from django_modern_rest.openapi.objects.external_documentation import (
    ExternalDocumentation as ExternalDocumentation,
)
from django_modern_rest.openapi.objects.header import (
    Header as Header,
)
from django_modern_rest.openapi.objects.info import Info as Info
from django_modern_rest.openapi.objects.license import License as License
from django_modern_rest.openapi.objects.link import Link as Link
from django_modern_rest.openapi.objects.media_type import (
    MediaType as MediaType,
)
from django_modern_rest.openapi.objects.oauth_flow import OAuthFlow as OAuthFlow
from django_modern_rest.openapi.objects.oauth_flows import (
    OAuthFlows as OAuthFlows,
)
from django_modern_rest.openapi.objects.open_api import OpenAPI as OpenAPI
from django_modern_rest.openapi.objects.operation import Operation as Operation
from django_modern_rest.openapi.objects.parameter import Parameter as Parameter
from django_modern_rest.openapi.objects.path_item import PathItem as PathItem
from django_modern_rest.openapi.objects.paths import Paths as Paths
from django_modern_rest.openapi.objects.reference import Reference as Reference
from django_modern_rest.openapi.objects.request_body import (
    RequestBody as RequestBody,
)
from django_modern_rest.openapi.objects.response import (
    Response as Response,
)
from django_modern_rest.openapi.objects.responses import Responses as Responses
from django_modern_rest.openapi.objects.schema import Schema as Schema
from django_modern_rest.openapi.objects.security_requirement import (
    SecurityRequirement as SecurityRequirement,
)
from django_modern_rest.openapi.objects.security_scheme import (
    SecurityScheme as SecurityScheme,
)
from django_modern_rest.openapi.objects.server import Server as Server
from django_modern_rest.openapi.objects.server_variable import (
    ServerVariable as ServerVariable,
)
from django_modern_rest.openapi.objects.tag import Tag as Tag
from django_modern_rest.openapi.objects.xml import XML as XML
