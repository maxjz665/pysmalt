"""
Модель текста
"""
from django.db import models

from text_app.models.tbl_author import TblAuthor


class TblText(models.Model):
    """
    Модель текста
    """

    class Meta:
        db_table = 'text'

    id = models.AutoField(primary_key=True)
    title = models.CharField()
    inuse1 = models.IntegerField(default=1)
    inuse2 = models.IntegerField(default=0)  # Возможно в будущем удалить тексты новой разметки т.к. не используются
    status = models.IntegerField(default=0)
    author = models.ForeignKey(TblAuthor, on_delete=models.SET_NULL)
