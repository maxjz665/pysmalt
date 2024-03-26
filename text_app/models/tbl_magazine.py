"""
Модель хранения журнала
"""

from django.db import models


class TblMagazine(models.Model):
    """
    Модель хранения журнала
    """
    class Meta:
        db_table = 'magazine'

    id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=255)
    origin_title= models.CharField(max_length=255)
