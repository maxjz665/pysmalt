"""
Модель разбора слова
"""

from django.db import models


class AbstractDictWord(models.Model):
    """
        Модель разбора слова
        """

    class Meta:
        abstract = True

    id = models.AutoField(primary_key=True)
    word = models.TextField()
    initial_form = models.TextField()
    param_01 = models.IntegerField(default=0)
    param_02 = models.IntegerField(default=0)
    param_03 = models.IntegerField(default=0)
    param_04 = models.IntegerField(default=0)
    param_05 = models.IntegerField(default=0)
    param_06 = models.IntegerField(default=0)
    param_07 = models.IntegerField(default=0)
    param_08 = models.IntegerField(default=0)
    param_09 = models.IntegerField(default=0)
    param_10 = models.IntegerField(default=0)
    param_11 = models.IntegerField(default=0)
    param_12 = models.IntegerField(default=0)
    param_13 = models.IntegerField(default=0)
    param_14 = models.IntegerField(default=0)
    param_15 = models.IntegerField(default=0)
    param_16 = models.IntegerField(default=0)
    param_17 = models.IntegerField(default=0)
    param_18 = models.IntegerField(default=0)
    param_19 = models.IntegerField(default=0)
    param_20 = models.IntegerField(default=0)
    current_status = models.IntegerField(default=0)
    params_count = models.IntegerField(default=0)
    modern = models.TextField()


class TblDictWord(AbstractDictWord):
    class Meta:
        db_table = 'entries'


class TblDictWord2(AbstractDictWord):
    class Meta:
        db_table = 'entries2'
