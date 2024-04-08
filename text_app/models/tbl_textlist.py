"""
Модель описания списка текстов
"""
from django.db import models

from text_app.models.tbl_text import TblText
from user_app.models import TblUser


class TblTextListDescription(models.Model):
    """
    Модель описания списка текстов
    """
    class Meta:
        db_table = 'textlist_description'

    id = models.AutoField(primary_key=True)
    name = models.TextField(max_length=200)
    owner = models.ForeignKey(TblUser, db_column="owner", on_delete=models.SET_NULL, null=True, blank=True)
    public = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)

    @property
    def items(self):
        """
        Маппинг с списка текстов с текстами
        :return:
        """
        return TblTextListItems.objects.filter(list_id=self.id).all()


class TblTextListItems(models.Model):
    """
    Модель связи списка текстов с текстом
    """
    class Meta:
        db_table = 'textlist_items'

    id = models.AutoField(primary_key=True)
    list = models.ForeignKey(TblTextListDescription, db_column="listid", on_delete=models.CASCADE)
    text = models.ForeignKey(TblText, db_column="textid", on_delete=models.CASCADE)
