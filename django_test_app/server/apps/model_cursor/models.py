from typing import final

from django.db import models


@final
class Entry(models.Model):
    rank = models.IntegerField(db_index=True)
    name = models.CharField(max_length=100, default='')
    created_at = models.DateTimeField(auto_now_add=True)
