"""
Модель текста
"""
from operator import and_
from unicodedata import category

from django.contrib.auth.models import AnonymousUser
from django.db import models

from text_app.models.tbl_author import TblAuthor
from text_app.models.tbl_magazine import TblMagazine
from user_app.models import TblUser


class TblText(models.Model):
    """
    Модель текста
    """

    class Meta:
        db_table = 'text'

    id = models.AutoField(primary_key=True)
    title = models.TextField()
    author = models.ForeignKey(TblAuthor, related_name='author_data', on_delete=models.SET_NULL, null=True, blank=True)
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
    author2 = models.ForeignKey(TblAuthor, related_name='author2_data', on_delete=models.SET_NULL, null=True,
                                blank=True)
    author2_type = models.IntegerField(default=0)
    author3 = models.ForeignKey(TblAuthor, related_name='author3_data', on_delete=models.SET_NULL, null=True,
                                blank=True)
    author3_type = models.IntegerField(default=0)
    short_title = models.TextField()
    magazine_volume = models.CharField(max_length=255)
    magazine_section = models.CharField(max_length=255)
    pages = models.CharField(max_length=255)
    censorship = models.TextField()
    attributions = models.TextField()
    status = models.IntegerField(default=0)
    idkey = models.CharField(max_length=255)
    origin_title = models.TextField()

    @staticmethod
    def get_texts(user = AnonymousUser, exclude_list: set = None, exclude_deleted: bool = False, exclude_not_verified: bool = False):
        """
        Получение перечня текстов в зависимости от пользователя
        :param user: пользователь
        :param exclude_list: перечень исключенных текстов
        :param exclude_deleted: исключить удаленные тексты
        :param exclude_not_verified: исключить непроверенные тексты
        :return: список текстов
        """
        texts = TblText.objects.filter(inuse1=1)
        if user.is_anonymous or not user.is_authenticated or not user.has_level(TblUser.LEVEL_USER) or exclude_not_verified:
            texts = texts.filter(status=2)

        if user.is_anonymous or not user.is_authenticated or not user.has_level(TblUser.LEVEL_EDITOR) or exclude_deleted:
            texts = texts.filter(category=0)

        if exclude_list:
            texts = texts.exclude(id__in=exclude_list)

        return texts

    def get_content(self):
        from text_app.models.tbl_word import TblWord
        return TblWord.objects.filter(text_id=self.id).order_by("chapter_index",
                                                                    "paragraph_index",
                                                                    "sentence_index",
                                                                    "word_index").all()
