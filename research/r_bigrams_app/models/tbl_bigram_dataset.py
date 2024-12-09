"""
Задача расчета частоты встречаемости биграм по группе текстов или по всем текстам
"""

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
