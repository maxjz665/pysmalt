"""
Модель слова в тексте
"""
import re
from datetime import date

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

    @classmethod
    def save_word(cls, text_obj, word_data):
        entry = None
        if not word_data["id"]:
            if word_data["pos"]:
                entry = TblDictWord(word=word_data["word"], param_01=word_data["pos"])
                entry.save()
        else:
            entry = TblDictWord.objects.filter(id=word_data["id"]).get()
        word = cls(
            text=text_obj,
            word_length=len(word_data["word"]),
            chapter_index=word_data["chapter"],
            paragraph_index=word_data["paragraph"],
            sentence_index=word_data["sentence"],
            word_index=word_data["wordindex"],
            chdate=date.today().strftime("%Y-%m-%d"),
            word=word_data["word"],
            dictword=entry,
            dictword2=None,
            wordorder=0,
            wordno=0,
        )
        word.save()


    @staticmethod
    def fix_word(word: str) -> str:
        return re.sub(r"[Іі]", "i",
                      re.sub(r"[áà]", "а",
                             re.sub(r"[óò]", "о",
                                    re.sub(r"[ёéѐè]", "е",
                                           re.sub(r"[́̀]", "", word)))))