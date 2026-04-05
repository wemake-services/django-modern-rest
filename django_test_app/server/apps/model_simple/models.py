from django.db import models


class User(models.Model):
    # This is sent to us from another service:
    email = models.EmailField(unique=True)
    customer_service_uid = models.UUIDField(unique=True)

    # Our own fields:
    is_active = models.BooleanField(db_index=True, default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
