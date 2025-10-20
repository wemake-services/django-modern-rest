from collections.abc import Callable
from typing import Any, TypeVar

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt, csrf_protect

_TypeT = TypeVar('_TypeT', bound=type[Any])


def _dmr_csrf_class_decorator(cls: _TypeT) -> _TypeT:
    """Mark controller for internal CSRF and exempt dispatch from Django."""
    cls._dmr_require_csrf = True
    return method_decorator(csrf_exempt, name='dispatch')(cls)


def dispatch_decorator(
    func: Callable[..., Any],
) -> Callable[[_TypeT], _TypeT]:
    """
    Special helper to decorate class-based view's ``dispatch`` method.

    Use it directly on controllers, like so:

    .. code:: python

        >>> from django_modern_rest import dispatch_decorator, Controller
        >>> from django_modern_rest.plugins.pydantic import PydanticSerializer
        >>> from django.contrib.auth.decorators import login_required

        >>> @dispatch_decorator(login_required())
        ... class MyController(Controller[PydanticSerializer]):
        ...     def get(self) -> str:
        ...         return 'Logged in!'

    In this example we would require all calls
    to all methods of ``MyController`` to require an existing authentication.

    It also works for things like:
    - :func:`django.contrib.auth.decorators.login_not_required`
    - :func:`django.contrib.auth.decorators.user_passes_test`
    - :func:`django.contrib.auth.decorators.permission_required`
    - and any other default or custom django decorator

    Additionally, when used with
    :func:`django.views.decorators.csrf.csrf_protect`, we reroute
    CSRF enforcement to framework-level handling to allow
    consistent JSON error responses without changing global settings.
    """
    if func is csrf_protect:
        return _dmr_csrf_class_decorator

    return method_decorator(func, name='dispatch')
