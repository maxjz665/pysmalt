"""
Модель описания списка текстов
"""
from django.db import models

from user_app.models import TblUser


class TblTextListDescription(models.Model):
    """
    Модель описания списка текстов
    """
    class Meta:
        db_table = 'textlist_description'

    id = models.AutoField(primary_key=True)
    name = models.TextField(max_length=200)
    owner = models.ForeignKey(TblUser, db_column="owner", on_delete=models.SET_NULL, null=True, blank=True)
    public = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
