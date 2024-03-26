"""
Модель хранения автора
"""

from django.db import models


class TblAuthor(models.Model):
    """
    Модель хранения автора
    """
    class Meta:
        db_table = 'author'

    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    origin_name = models.CharField(max_length=255)
    real_name = models.CharField(max_length=255)
