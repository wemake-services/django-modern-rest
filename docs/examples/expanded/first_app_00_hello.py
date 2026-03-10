import sys

from django.conf import settings
from django.core.management import execute_from_command_line
from django.http import HttpResponse
from django.urls import path

# Configure Django settings
# For now, just leave it as is
# Real apps typically add INSTALLED_APPS and MIDDLEWARE. We will add it later
settings.configure(
    DEBUG=True,
    SECRET_KEY='your-secret-key-here',
    ROOT_URLCONF=__name__,
)

# Define URL patterns
# urlpatterns is mechanism that maps URL to function
# Now we pass a lambda function for the root URL (http://localhost:8000/)
urlpatterns = [
    path('', lambda request: HttpResponse('Hello from Django Modern Rest!')),
]

if __name__ == '__main__':
    # This code passes all arguments from command line to Django.
    # For example, simple way to run code is: python3 main.py runserver
    execute_from_command_line(sys.argv)
