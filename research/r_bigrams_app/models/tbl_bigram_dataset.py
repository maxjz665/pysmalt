"""
Задача расчета частоты встречаемости биграм по группе текстов или по всем текстам
"""
from collections import namedtuple

from django.db import models

from shower.models import BaseModel
from text_app.models.tbl_textlist import TblTextListDescription
from user_app.models import TblUser


class TblBigramDataset(BaseModel):
    """
    Задача расчета частоты встречаемости биграмм по группе текстов или по всем текстам
    """
    class Meta:
        db_table = 'r_bigram_dataset'
        db_table_comment = 'Датасеты биграмм для групп текстов'

    id = models.AutoField(primary_key=True)
    name = models.TextField(max_length=200, db_comment='Название датасета')
    owner = models.ForeignKey(TblUser, db_column="owner", on_delete=models.SET_NULL,
                              null=True, blank=True, db_comment='Владелец датасета')
    is_public = models.BooleanField(default=False, db_comment='Публичный доступ к датасету')
    max_bigrams = models.IntegerField(default=100, db_comment='Максимальное число биграмм в датасете')
    min_occurrence = models.IntegerField(default=1, db_comment='Минимальное количество встречаемости биграммы')
    text_group = models.ForeignKey(TblTextListDescription, db_column='text_group', on_delete=models.SET_NULL,
                                   null=True, blank=True, db_comment="Группа текстов или все доступные тексты")
    is_use_initial = models.BooleanField(default=False, db_comment='расчет биграмм по словоформам (False) или по начальным значениям (True)')
    is_sentence_split = models.BooleanField(default=True, db_comment='расчет биграмм по предложениям или по абзацам')
    content = models.JSONField(default=list, db_comment='Перечень биграмм')
    build_at = models.DateTimeField(null=True, default=None, db_comment="Время последней сборки")
    build_status = models.TextField(max_length=200, db_comment="Статус сборки", null=True)

    def check_text(self, text_data):
        """
        Построение лексического спектра для данного текста
        """
        dataset = {}
        StatData = namedtuple('StatData', ['value', 'pos'])
        total_ngrams = 0
        for item in self.content:
            dataset[item[0]] = StatData(item[1], len(dataset))
            total_ngrams += item[1]
        ret = []
        total_ngrams = 1000 / total_ngrams # делаем множитель для нормализации значений по словарю
        ngrams = self.extract_ngrams(text_data)
        ResultItem = namedtuple("ResultItem", ['ngram', 'value', 'dict_value', 'dict_pos'])
        for item in ngrams:
            if item in dataset.keys():
                ret.append(ResultItem(item, ngrams[item], dataset[item].value * total_ngrams, dataset[item].pos))
        ret.sort(key=lambda x: x.dict_pos)
        return ret

    def extract_ngrams(self, content, result=None):
        """
        Извлечение лексического спектра из текста
        """
        if result is None:
            result = {}

        first_item = None
        for item in content:
            if first_item is None or (
            item.is_new_sentence(first_item) if self.is_sentence_split else item.is_new_paragraph(first_item)):
                first_item = item
                continue
            key = first_item.word + " - " + item.word
            if key in result:
                result[key] += 1
            else:
                result[key] = 1
            first_item = item
        return result