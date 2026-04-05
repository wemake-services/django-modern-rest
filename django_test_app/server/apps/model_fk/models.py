from django.db import models


class Tag(models.Model):
    name = models.CharField(max_length=100, unique=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Role(models.Model):
    name = models.CharField(max_length=100, unique=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class User(models.Model):
    # This is sent to us from another service:
    email = models.EmailField(unique=True)

    # Linking:
    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name='users',
    )
    tags = models.ManyToManyField(Tag, related_name='users')

    # Our own fields:
    is_active = models.BooleanField(db_index=True, default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
