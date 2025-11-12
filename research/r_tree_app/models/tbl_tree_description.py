import json

from django.db import models
from picklefield.fields import PickledObjectField

from research.r_tree_app.utils import get_pos
from shower.models import BaseModel
from text_app.models.tbl_textlist import TblTextListDescription
from user_app.models import TblUser


# Create your models here.
class TblTreeDescription(BaseModel):
    """
    Модель дерева решений
    """

    class Meta:
        db_table = 'r_tree_description'
        db_table_comment = 'Проекты деревьев решений'

    id = models.AutoField(primary_key=True)
    name = models.TextField(max_length=200, db_comment='Название проекта/дерева')
    owner = models.ForeignKey(TblUser, db_column="owner", on_delete=models.SET_NULL,
                              null=True, blank=True, db_comment='Владелец проекта/дерева')
    public = models.BooleanField(default=False, db_comment='Публичный доступ к проекту/дереву')
    block_size = models.IntegerField(default=0, db_comment='Размер блока для расчета')
    sector_size = models.FloatField(default=0, db_comment='Размер сектора в разделители в процентах (0-100)')
    many_sectors = models.BooleanField(default=False, db_comment='Флаг использования циклических разделов')
    is_need_uno = models.BooleanField(default=False, db_comment='Флаг использования униграмм частей речи в дереве решения')
    is_need_duo = models.BooleanField(default=True, db_comment='Флаг использования биграмм частей речи в дереве решений')
    is_need_separate = models.BooleanField(default=False, db_comment='Флаг использования разделителей униграмм в дереве решений')
    first_list = models.ForeignKey(TblTextListDescription, related_name="first_list_data", db_column="first_list", on_delete=models.CASCADE)
    second_list = models.ForeignKey(TblTextListDescription, related_name="second_list_data", db_column="second_list", on_delete=models.CASCADE)
    removed_pos = models.TextField(default="[]", db_comment='Перечень частей речи для исключения из дерева решений')
    max_depth = models.IntegerField(default=4, db_comment='Максимальная глубина дерева решений')
    accuracy = models.FloatField(default=0, db_comment='Точность дерева решений')
    vector_size = models.IntegerField(default=0, db_comment='Размер вектора принятия решений')
    build_at = models.DateTimeField(null=True, default=None, db_comment='Дата сборки')
    build_status = models.TextField(max_length=200, db_comment="Статус сборки", null=True)
    graph_dot = models.TextField(blank=True, null=True, db_comment="Граф дерева решений")
    graph_pickle = PickledObjectField(null=True, db_comment="Бинарное дерево решений")
    table1_size = models.IntegerField(default=0, db_comment="Число блоков текста первого набора")
    table2_size = models.IntegerField(default=0, db_comment="Число блоков текста второго набора")

    @property
    def text_removed_pos(self):
        """
        Получение текстовых представлений частей речи для отображения на фронте
        """
        pos = get_pos()
        items = json.loads(str(self.removed_pos))
        ret = []
        for idx in items:
            ret.append(pos[idx])
        return ret

    @property
    def count_removed_pos(self):
        """
        Подсчет числа удаленных частей речи для фронта
        """
        try:
            return len(json.loads(str(self.removed_pos)))
        except Exception:
            return 0
