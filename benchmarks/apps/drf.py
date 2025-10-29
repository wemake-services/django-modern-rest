import enum
import uuid

import django
from django.conf import settings
from django.core.handlers import wsgi
from django.urls import path
from django.utils.crypto import get_random_string

if not settings.configured:
    settings.configure(
        ROOT_URLCONF=__name__,
        REST_FRAMEWORK={},
        ALLOWED_HOSTS='*',
        DEBUG=False,
        SECRET_KEY=get_random_string(50),
        INSTALLED_APPS=[
            'django.contrib.auth',
            'django.contrib.contenttypes',
            'rest_framework',
        ],
    )
    django.setup()

from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

sync_app = wsgi.WSGIHandler()


class Level(enum.StrEnum):
    started = 'starter'
    mid = 'mid'
    pro = 'pro'


class SkillSerializer(serializers.Serializer):
    name = serializers.CharField()
    description = serializers.CharField()
    optional = serializers.BooleanField()
    level = serializers.ChoiceField(
        choices=[level.value for level in Level],
    )


class ItemSerializer(serializers.Serializer):
    name = serializers.CharField()
    quality = serializers.IntegerField()
    count = serializers.IntegerField()
    rarety = serializers.IntegerField()
    parts = serializers.ListField(child=serializers.DictField(), required=False)


class UserCreateSerializer(serializers.Serializer):
    email = serializers.CharField()
    age = serializers.IntegerField()
    height = serializers.FloatField()
    average_score = serializers.FloatField()
    balance = serializers.DecimalField(max_digits=1000, decimal_places=200)
    skills = SkillSerializer(many=True)
    aliases = serializers.DictField(child=serializers.CharField())
    birthday = serializers.DateTimeField()
    timezone_diff = serializers.DurationField()
    friends = serializers.ListField(
        child=serializers.DictField(),
        required=False,
    )
    best_friend = serializers.DictField(allow_null=True, required=False)
    promocodes = serializers.ListField(child=serializers.UUIDField())
    items = ItemSerializer(many=True)


class UserSerializer(UserCreateSerializer):
    uid = serializers.UUIDField()


class QuerySerializer(serializers.Serializer):
    per_page = serializers.IntegerField()
    count = serializers.IntegerField()
    page = serializers.IntegerField()
    filter = serializers.ListField(child=serializers.CharField())


class HeadersSerializer(serializers.Serializer):
    x_api_token = serializers.CharField()
    x_request_origin = serializers.CharField()


class SyncUserView(APIView):
    def post(self, request):
        query_serializer = QuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)
        filters = query_serializer.validated_data

        assert filters['filter'][0] == 'drf', filters['filter']

        header_data = {
            'x_api_token': request.headers.get('x-api-token', ''),
            'x_request_origin': request.headers.get('x-request-origin', ''),
        }
        header_serializer = HeadersSerializer(data=header_data)
        header_serializer.is_valid(raise_exception=True)

        user_data = UserCreateSerializer(data=request.data)
        user_data.is_valid(raise_exception=True)

        result = {
            'uid': str(uuid.uuid4()),
            **user_data.validated_data,
        }

        return Response(result, status=status.HTTP_200_OK)


urlpatterns = [
    path('sync/user/', SyncUserView.as_view()),
]
