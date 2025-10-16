from django_modern_rest import Controller, compose_controllers
from django_modern_rest.plugins.pydantic import PydanticSerializer

# 0 args:
compose_controllers()  # type: ignore[call-arg]


class _FirstController(Controller[PydanticSerializer]): ...


# 1 arg:
compose_controllers(_FirstController)  # type: ignore[call-arg]


class _SecondController(Controller[PydanticSerializer]): ...


# 1 args:
compose_controllers(_FirstController, _SecondController)


class _ThirdController(Controller[PydanticSerializer]): ...


# More args:
compose_controllers(_FirstController, _SecondController, _ThirdController)
