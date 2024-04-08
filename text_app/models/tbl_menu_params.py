"""
Модель значений элементов дерева атрибута
"""

from django.db import models


class AbstractMenuParams(models.Model):
    """
        Модель значений элементов старого дерева атрибутов
        """

    class Meta:
        abstract = True

    id = models.AutoField(primary_key=True)
    param_caption = models.TextField()
    items_count = models.IntegerField()
    item_1 = models.IntegerField()
    item_2 = models.IntegerField()
    item_3 = models.IntegerField()
    item_4 = models.IntegerField()
    item_5 = models.IntegerField()
    item_6 = models.IntegerField()
    item_7 = models.IntegerField()
    item_8 = models.IntegerField()
    item_9 = models.IntegerField()
    item_10 = models.IntegerField()
    item_11 = models.IntegerField()
    item_12 = models.IntegerField()
    item_13 = models.IntegerField()
    item_14 = models.IntegerField()
    item_15 = models.IntegerField()
    item_16 = models.IntegerField()
    item_17 = models.IntegerField()
    item_18 = models.IntegerField()
    item_19 = models.IntegerField()
    item_20 = models.IntegerField()
    item_21 = models.IntegerField()
    item_22 = models.IntegerField()
    item_23 = models.IntegerField()
    item_24 = models.IntegerField()
    item_25 = models.IntegerField()
    item_26 = models.IntegerField()
    item_27 = models.IntegerField()
    item_28 = models.IntegerField()
    item_29 = models.IntegerField()
    item_30 = models.IntegerField()


class TblMenuParams(AbstractMenuParams):
    class Meta:
        db_table = "menu_params"


class TblMenuParams2(AbstractMenuParams):
    class Meta:
        db_table = "menu_params2"
