"""
Модель хранения типов автора
"""

from django.db import models


class TblAuthorTypes(models.Model):
    """
    Модель хранения типов автора
    """
    class Meta:
        db_table = 'author_types'

    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)

    @property
    def items(self):
        """
        Маппинг списка текстов с текстами
        :return:
        """
        return TblAuthorTypes.objects