"""
Модель слова в тексте
"""
from django.db import models

from text_app.models.tbl_dict_word import TblDictWord, TblDictWord2
from text_app.models.tbl_text import TblText


class TblWord(models.Model):
    """
    Модель слова в тексте
    """
    class Meta:
        db_table = 'word'

    id_word = models.AutoField(primary_key=True)
    text = models.ForeignKey(TblText, on_delete=models.CASCADE)
    word_length = models.IntegerField(default=0)
    chapter_index = models.IntegerField(default=0)
    paragraph_index = models.IntegerField(default=0)
    sentence_index = models.IntegerField(default=0)
    word_index = models.IntegerField(default=0)
    chdate = models.DateTimeField()
    word = models.CharField()
    dictword = models.ForeignKey(TblDictWord, on_delete=models.SET_NULL, null=True, blank=True)
    dictword2 = models.ForeignKey(TblDictWord2, on_delete=models.SET_NULL, null=True, blank=True)
    wordorder = models.IntegerField(default=0)
    wordno = models.IntegerField(default=0)
