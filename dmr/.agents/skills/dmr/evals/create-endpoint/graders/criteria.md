---
type: llm
focus: last_message
---

PASS if the module defines a `msgspec.Struct` DTO, a class that subclasses
`Controller[MsgspecSerializer]` with a `post` method whose body parameter
is annotated as `Body[...]`, the method returns the model instance
(not a Django response), and the 201 status is set with
`@modify(status_code=HTTPStatus.CREATED)` or an equivalent `modify` call.

FAIL if the endpoint returns `HttpResponse` or `JsonResponse`,
uses Django REST Framework or Django Ninja, uses `@validate` without
a reason, or builds the JSON by hand.
