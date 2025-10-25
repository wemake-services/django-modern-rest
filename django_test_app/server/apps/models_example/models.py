from django.db import models


class Tag(models.Model):
    name = models.CharField(max_length=100)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Role(models.Model):
    name = models.CharField(max_length=100)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class User(models.Model):
    email = models.EmailField(unique=True)

    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name='users',
    )
    tags = models.ManyToManyField(Tag, related_name='users')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def tag_list(self) -> list[Tag]:
        """Needed for serialization only."""
        return list(self.tags.all())
