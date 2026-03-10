import json
import sys

from django.conf import settings
from django.core.management import execute_from_command_line
from django.http import HttpResponse, JsonResponse
from django.urls import path

DATABASE = {
    '1': 'Alex',
    '2': 'Sasha',
}

# Configure Django settings
# For now, just leave it as is
# Real apps typically add INSTALLED_APPS and MIDDLEWARE. We will add it later
settings.configure(
    DEBUG=True,
    SECRET_KEY='your-secret-key-here',
    ROOT_URLCONF=__name__,
)


def get_users(request):
    return JsonResponse(DATABASE)


def set_user(request):
    if request.method != 'POST':
        return HttpResponse('Method not allowed', status=405)

    try:
        data = json.loads(request.body)
        user_id = data.get('id')
        name = data.get('name')

        if not user_id or not name:
            return HttpResponse('Missing id or name', status=400)

        DATABASE[user_id] = name

        return JsonResponse({'status': 'success', 'data': DATABASE})
    except json.JSONDecodeError:
        return HttpResponse('Invalid JSON', status=400)


# Define URL patterns
# urlpatterns is mechanism that maps URL to function
# Now we pass a lambda function for the root URL (http://localhost:8000/)
urlpatterns = [
    path('', lambda request: HttpResponse('Hello from Django Modern Rest!')),
    path('get_users', get_users),
    path('set_user', set_user),
]

if __name__ == '__main__':
    # This code passes all arguments from command line to Django.
    # For example, simple way to run code is: python3 main.py runserver
    execute_from_command_line(sys.argv)
