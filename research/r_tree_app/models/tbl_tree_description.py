from django.db import models
from picklefield.fields import PickledObjectField

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
    block_size = models.IntegerField(default=0)
    sector_size = models.FloatField(default=0)
    many_sectors = models.BooleanField(default=False)
    first_list = models.ForeignKey(TblTextListDescription, related_name="first_list_data", db_column="first_list", on_delete=models.CASCADE)
    second_list = models.ForeignKey(TblTextListDescription, related_name="second_list_data", db_column="second_list", on_delete=models.CASCADE)
    build_at = models.DateTimeField(null=True, default=None)
    build_status = models.TextField(max_length=200, db_comment="Статус сборки", null=True)
    graph_dot = models.TextField(blank=True, null=True, db_comment="Граф дерева решений")
    graph_pickle = PickledObjectField(null=True, db_comment="Бинарное дерево решений")
