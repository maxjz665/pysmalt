from django.db import models

from text_app.models.tbl_textlist import TblTextListDescription
from user_app.models import TblUser


# Create your models here.
class TblTreeDescription(models.Model):
    """
    Модель дерева решений
    """

    class Meta:
        db_table = 'r_tree_description'

    id = models.AutoField(primary_key=True)
    name = models.TextField(max_length=200)
    owner = models.ForeignKey(TblUser, db_column="owner", on_delete=models.SET_NULL,
                              null=True, blank=True)
    public = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    block_size = models.IntegerField(default=0)
    first_list = models.ForeignKey(TblTextListDescription, db_column="first_list", on_delete=models.CASCADE)
    second_list = models.ForeignKey(TblTextListDescription, db_column="second_list", on_delete=models.CASCADE)
