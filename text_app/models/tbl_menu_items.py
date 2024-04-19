"""
Модель названий элементов дерева атрибута
"""

from django.db import models


class AbstractMenuItems(models.Model):
    """
        Модель названий элементов старого дерева атрибутов
        """

    class Meta:
        abstract = True

    id = models.AutoField(primary_key=True)
    item_caption = models.CharField(max_length=255)
    params_count = models.IntegerField()
    param_1 = models.IntegerField()
    param_2 = models.IntegerField()
    param_3 = models.IntegerField()
    param_4 = models.IntegerField()
    param_5 = models.IntegerField()
    param_6 = models.IntegerField()
    param_7 = models.IntegerField()
    param_8 = models.IntegerField()
    param_9 = models.IntegerField()
    param_10 = models.IntegerField()
    param_11 = models.IntegerField()
    param_12 = models.IntegerField()
    param_13 = models.IntegerField()
    param_14 = models.IntegerField()
    param_15 = models.IntegerField()
    param_16 = models.IntegerField()
    param_17 = models.IntegerField()
    param_18 = models.IntegerField()
    param_19 = models.IntegerField()
    param_20 = models.IntegerField()
    param_21 = models.IntegerField()
    param_22 = models.IntegerField()
    param_23 = models.IntegerField()
    param_24 = models.IntegerField()
    param_25 = models.IntegerField()
    param_26 = models.IntegerField()
    param_27 = models.IntegerField()
    param_28 = models.IntegerField()
    param_29 = models.IntegerField()
    param_30 = models.IntegerField()


class TblMenuItems(AbstractMenuItems):
    class Meta:
        db_table = "menu_items"


class TblMenuItems2(AbstractMenuItems):
    class Meta:
        db_table = "menu_items2"
