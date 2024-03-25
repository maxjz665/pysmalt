"""
Модель текста
"""
from django.db import models


class TblText(models.Model):
    class Meta:
        db_table = 'text'

    id = models.AutoField(primary_key=True)
    title = models.CharField()
