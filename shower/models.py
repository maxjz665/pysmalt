"""
Общие/абстрактные модели данных
"""

from django.db import models


class BaseModel(models.Model):
    """
    Модель данных с базовыми полями
    """

    class Meta:
        abstract = True

    created_at = models.DateTimeField(auto_now_add=True, blank=True, db_comment='Время создания объекта')
    updated_at = models.DateTimeField(auto_now=True, blank=True, db_comment='Время изменения объекта')
    created_by = models.IntegerField(default=0, db_comment='Автор создания')
    updated_by = models.IntegerField(default=0, db_comment='Автор обновления')
    is_deleted = models.BooleanField(default=False, db_comment='Флаг удаления дерева')
