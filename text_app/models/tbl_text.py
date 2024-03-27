"""
Модель текста
"""
from django.db import models

from text_app.models.tbl_author import TblAuthor
from text_app.models.tbl_magazine import TblMagazine


class TblText(models.Model):
    """
    Модель текста
    """

    class Meta:
        db_table = 'text'

    id = models.AutoField(primary_key=True)
    title = models.CharField()
    author = models.ForeignKey(TblAuthor, on_delete=models.SET_NULL, null=True, blank=True)
    magazine = models.ForeignKey(TblMagazine, on_delete=models.SET_NULL, null=True, blank=True)
    magazine_no = models.CharField(max_length=255)
    publication_date = models.DateField()
    comment = models.TextField(max_length=1000)
    url = models.URLField(max_length=1000)
    background = models.ImageField(max_length=1000)
    inuse1 = models.IntegerField(default=1)
    inuse2 = models.IntegerField(default=0)  # Возможно в будущем удалить тексты новой разметки т.к. не используются
    syntax = models.IntegerField(default=0)
    category = models.IntegerField(default=0)
    text_type = models.IntegerField(default=0)
    author_verify = models.IntegerField(default=0)
    author_type = models.IntegerField(default=0)
    author2 = models.ForeignKey(TblAuthor, on_delete=models.SET_NULL, null=True, blank=True)
    author2_type = models.IntegerField(default=0)
    author3 = models.ForeignKey(TblAuthor, on_delete=models.SET_NULL, null=True, blank=True)
    author3_type = models.IntegerField(default=0)
    short_title = models.CharField()
    magazine_volume = models.CharField(max_length=255)
    magazine_section = models.CharField(max_length=255)
    pages = models.CharField(max_length=255)
    censorship = models.CharField()
    attributions = models.CharField()
    status = models.IntegerField(default=0)
    idkey = models.CharField(max_length=255)
    origin_title = models.CharField()
