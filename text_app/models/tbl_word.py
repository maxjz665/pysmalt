"""
Модель слова в тексте
"""
import re

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
    word = models.TextField()
    dictword = models.ForeignKey(TblDictWord, on_delete=models.SET_NULL, null=True, blank=True)
    dictword2 = models.ForeignKey(TblDictWord2, on_delete=models.SET_NULL, null=True, blank=True)
    wordorder = models.IntegerField(default=0)
    wordno = models.IntegerField(default=0)

    def is_new_sentence(self, next_word):
        """
        Определяем следующее предложение или нет
        """
        if self.is_new_paragraph(next_word) or \
            self.sentence_index != next_word.sentence_index:
            return True
        return False

    def is_new_paragraph(self, next_word):
        if self.chapter_index != next_word.chapter_index or self.paragraph_index != next_word.paragraph_index:
            return True
        return False

    @staticmethod
    def fix_word(word: str) -> str:
        return re.sub(r"[Іі]", "i",
                      re.sub(r"[áà]", "а",
                             re.sub(r"[óò]", "о",
                                    re.sub(r"[ёéѐè]", "е",
                                           re.sub(r"[́̀]", "", word)))))