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

    @property
    def bib_item(self):
        """
        Формирование библиографического описания
        :return: строка с библиографическим описанием
        """
        ret = f"[{self.idkey}] "
        if self.author is not None:
            ret += self.author.name
            if self.author.name[-1] == '.':
                ret += " "
            else:
                ret += ". "

        # печать названия. TODO: добавить ссылку!
        ret += self.title

        # печать перечня авторов. TODO: перевернуть ФИО на ИОФ
        has_author = False
        if self.author is not None:
            ret += " / " + self.author.name
            has_author = True
        if self.author2 is not None:
            if not has_author:
                ret += " / "
                has_author = True
            else:
                ret += ", "
            ret += self.author2.name
        if self.author3 is not None:
            if not has_author:
                ret += " / "
            else:
                ret += ", "
                ret += self.author3.name

        # печать журнала если он есть
        ret += " // "
        if self.magazine is not None:
            ret += self.magazine.title + "."

        # дата публикации
        if self.publication_date is not None:
            ret += f" - {self.publication_date.year}."

        # раздел журнала если есть
        if self.magazine_section is not None:
            ret += f" - Разд. {self.magazine_section}."

        # том журнала если есть
        if self.magazine_volume is not None:
            ret += f" - Т. {self.magazine_volume}."

        # номер журнала если есть
        if self.magazine_no is not None:
            ret += f" - № {self.magazine_no}."

        # номера страниц если есть
        if self.pages is not None:
            ret += f" - с. {self.pages}."

        return ret
