from http import HTTPStatus
from typing import Any, Final, final

import pydantic
from django.http import HttpRequest, JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from typing_extensions import override

from dmr.decorators import dispatch_decorator

EXTERNAL_FUNC_OPENAPI: Final = """
{
  "get": {
    "operationId": "externalViews_externalFunction",
    "summary": "Health/status check endpoint",
    "responses": {
      "200": {
        "description": "Successful response",
        "content": {
          "application/json": {
            "schema": {
              "type": "object",
              "properties": {
                "status": {
                  "type": "integer",
                  "example": 200
                }
              },
              "required": [
                "status"
              ]
            }
          }
        }
      }
    }
  }
}
"""


@csrf_exempt
async def external_function(request: HttpRequest) -> JsonResponse:
    if request.method != 'GET':
        return JsonResponse(
            {},
            status=HTTPStatus.METHOD_NOT_ALLOWED,
            headers={'Allow': 'GET'},
        )
    return JsonResponse({'status': int(HTTPStatus.OK)})


# This OpenAPI has a trick: once user is defined as a schema,
# the second time as ref.
# We do this to test the external components registration.
EXTERNAL_CLASS_OPENAPI: Final = """
{
  "post": {
    "operationId": "externalViews_externalClassPost",
    "summary": "Echoes back the parsed JSON request body",
    "requestBody": {
      "required": true,
      "content": {
        "application/json": {
          "schema": {
            "type": "object",
            "properties": {
              "email": {
                "type": "string"
              }
            },
            "required": [
              "email"
            ]
          }
        }
      }
    },
    "responses": {
      "200": {
        "description": "Successful response - returns the parsed request body",
        "content": {
          "application/json": {
            "schema": {
              "$ref": "#/components/responses/ExternalClass_User"
            }
          }
        }
      },
      "400": {
        "description": "Invalid JSON in request body"
      }
    }
  }
}
"""

EXTERNAL_CLASS_COMPONENTS: Final = """
{
  "responses": {
    "ExternalClass_User": {
      "description": "Invalid JSON in request body",
      "type": "object",
      "properties": {
        "email": { "type": "string" }
      },
      "required": ["email"]
    }
  }
}
"""


@final
class _User(pydantic.BaseModel):
    email: str


@final
@dispatch_decorator(csrf_exempt)
class ExternalClass(View):
    def post(self, request: HttpRequest) -> JsonResponse:
        try:
            return JsonResponse(
                _User.model_validate_json(
                    request.body,
                ).model_dump(
                    mode='json',
                ),
            )
        except pydantic.ValidationError:
            return JsonResponse({}, status=HTTPStatus.BAD_REQUEST)

    @override
    def http_method_not_allowed(
        self,
        request: HttpRequest,
        *args: Any,
        **kwargs: Any,
    ) -> JsonResponse:
        # This is needed for `schemathesis` to pass on this type:
        return JsonResponse(
            {},
            status=HTTPStatus.METHOD_NOT_ALLOWED,
            headers={'Allow': 'GET'},
        )
