from dmr.plugins.pydantic import PydanticSerializer
from dmr.routing import Router, path
from examples.reusable_code.reusable_defaults import ReusableController

router = Router(
    'api/',
    [
        path(
            'example/',
            # No subclass of `ReusableController` anywhere:
            ReusableController.as_view(serializer=PydanticSerializer),
            name='example',
        ),
    ],
)

urlpatterns = [router.to_urlpatterns(namespace='api')]

# run: {"method": "post", "body": {"first_name": "Nikita", "last_name": "Sobolev"}, "url": "/api/example/", "use_urlpatterns": true}  # noqa: ERA001, E501
