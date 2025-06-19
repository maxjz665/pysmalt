"""
Модель текста
"""
import re
from operator import and_

from unicodedata import category

from django.contrib.auth.models import AnonymousUser
from django.db import models
from django.core.exceptions import ValidationError
from django.utils.dateparse import parse_date

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
    title = models.TextField(blank=True, null=True)
    author = models.ForeignKey(TblAuthor, related_name='author_data', on_delete=models.SET_NULL, null=True, blank=True)
    magazine = models.ForeignKey(TblMagazine, on_delete=models.SET_NULL, null=True, blank=True)
    magazine_no = models.CharField(max_length=255, null=True, blank=True)
    publication_date = models.DateField(null=True, blank=True)
    comment = models.TextField(max_length=1000, null=True, blank=True)
    url = models.URLField(max_length=1000, null=True, blank=True)
    background = models.ImageField(max_length=1000, null=True, blank=True)
    inuse1 = models.IntegerField(default=1)
    inuse2 = models.IntegerField(default=0)  # Возможно в будущем удалить тексты новой разметки т.к. не используются
    syntax = models.IntegerField(default=0)
    category = models.IntegerField(default=0)
    text_type = models.IntegerField(default=0)
    author_verify = models.IntegerField(default=0)
    author_type = models.IntegerField(default=0, blank=True, null=True)
    author2 = models.ForeignKey(TblAuthor, related_name='author2_data', on_delete=models.SET_NULL, null=True,
                                blank=True)
    author2_type = models.IntegerField(default=0, blank=True, null=True)
    author3 = models.ForeignKey(TblAuthor, related_name='author3_data', on_delete=models.SET_NULL, null=True,
                                blank=True)
    author3_type = models.IntegerField(default=0, blank=True, null=True)
    short_title = models.TextField(null=True, blank=True)
    magazine_volume = models.CharField(max_length=255, null=True, blank=True)
    magazine_section = models.CharField(max_length=255, null=True, blank=True)
    pages = models.CharField(max_length=255, null=True, blank=True)
    censorship = models.TextField(null=True, blank=True)
    attributions = models.TextField(null=True, blank=True)
    status = models.IntegerField(default=0)
    idkey = models.CharField(max_length=255, null=True, blank=True)
    origin_title = models.TextField(null=True, blank=True)

    @staticmethod
    def get_texts(user=AnonymousUser, exclude_list: set = None, include_list: set = None, exclude_deleted: bool = False,
                  exclude_not_verified: bool = False):
        """
        Получение перечня текстов в зависимости от пользователя
        :param user: пользователь
        :param exclude_list: перечень исключенных текстов
        :param include_list: перечень текстов для поиска
        :param exclude_deleted: исключить удаленные тексты
        :param exclude_not_verified: исключить непроверенные тексты
        :return: список текстов
        """
        texts = TblText.objects.filter(inuse1=1)
        if user.is_anonymous or not user.is_authenticated or not user.has_level(
                TblUser.LEVEL_USER) or exclude_not_verified:
            texts = texts.filter(status=2)

        if user.is_anonymous or not user.is_authenticated or not user.has_level(
                TblUser.LEVEL_EDITOR) or exclude_deleted:
            texts = texts.filter(category=0)

        if exclude_list:
            texts = texts.exclude(id__in=exclude_list)

        if include_list:
            texts = texts.filter(id__in=include_list)

        # подключение авторов и журналов для ускорения запроса
        return texts.select_related('magazine').select_related('author')

    @staticmethod
    def get_text(user=AnonymousUser, text_id: int = None):
        """
        Получение текста с проверкой всех прав
        """
        texts = TblText.objects.filter(inuse1=1, id=text_id)
        if user.is_anonymous or not user.is_authenticated or not user.has_level(TblUser.LEVEL_USER):
            texts = texts.filter(status=2)

        if user.is_anonymous or not user.is_authenticated or not user.has_level(TblUser.LEVEL_EDITOR):
            texts = texts.filter(category=0)

        return texts.first()

    def get_content(self):
        from text_app.models.tbl_word import TblWord
        return TblWord.objects.filter(text_id=self.id).order_by("chapter_index",
                                                                "paragraph_index",
                                                                "sentence_index",
                                                                "word_index").select_related('dictword').all()

    @classmethod
    def save_text_in_db(
            cls,
            title, author, magazine, magazine_no, publication_date, comment, url, background,
            category, text_type, author_verify, author_type, author2, author2_type, author3,
            author3_type, short_title, magazine_volume, magazine_section, pages, censorship, attributions,
            status, origin_title,
    ) -> int:
        try:
            def get_author_or_none(author_id):
                if author_id:
                    try:
                        return TblAuthor.objects.get(id=author_id)
                    except TblAuthor.DoesNotExist:
                        raise ValidationError(f"Автор с id={author_id} не найден.")
                return None
            magazine_obj = None
            public_date = None
            if author:
                author_obj = TblAuthor.objects.get(id=author)
            if magazine:
                magazine_obj = TblMagazine.objects.get(id=magazine)
            if publication_date:
                public_date = parse_date(publication_date)
                if publication_date and not public_date:
                    raise ValidationError("Неверный формат даты публикации.")

            text = cls(
                title=title.strip()[:1000] if title else None,
                author=get_author_or_none(author),
                magazine=magazine_obj,
                magazine_no=magazine_no[:255] if magazine_no else None,
                publication_date=public_date,
                comment=comment[:1000] if comment else None,
                url=url[:1000] if url else None,
                background=None,  # по умолчанию
                inuse1=1,
                inuse2=0,
                syntax=0,
                category=int(category) if category is not None else 0,
                text_type=int(text_type) if text_type is not None else 0,
                author_verify=int(author_verify) if author_verify is not None else 0,
                author_type=int(author_type) if author_type else None,
                author2=get_author_or_none(author2),
                author2_type=int(author2_type) if author2_type else None,
                author3_type=int(author3_type) if author3_type else None,
                author3=get_author_or_none(author3),
                origin_title=origin_title[:1000] if origin_title else None,
                short_title=short_title[:1000] if short_title else None,
                magazine_volume=magazine_volume[:255] if magazine_volume else None,
                magazine_section=magazine_section[:255] if magazine_section else None,
                pages=pages[:255] if pages else None,
                censorship=censorship[:1000] if censorship else None,
                attributions=attributions[:1000] if attributions else None,
                status=int(status) if status is not None else 0,
                idkey=None,  # Можно сгенерировать hash от названия, например
            )
            text.full_clean()  # Django built-in validation
            text.save()
            return text.id

        except ValidationError as ve:
            raise ve
        except Exception as e:
            raise RuntimeError(f"Ошибка при сохранении текста: {e}")
