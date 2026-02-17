from dmr import Blueprint
from dmr.plugins.pydantic import PydanticSerializer
from dmr.routing import compose_blueprints

# 0 args:
compose_blueprints()  # type: ignore[call-arg]


class _FirstBlueprint(Blueprint[PydanticSerializer]): ...


# 1 arg:
compose_blueprints(_FirstBlueprint)


class _SecondBlueprint(Blueprint[PydanticSerializer]): ...


# 2 args:
compose_blueprints(_FirstBlueprint, _SecondBlueprint)


class _ThirdBlueprint(Blueprint[PydanticSerializer]): ...


# More args:
compose_blueprints(_FirstBlueprint, _SecondBlueprint, _ThirdBlueprint)
