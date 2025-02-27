"""
Модель описания списка текстов
"""
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ObjectDoesNotExist
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
    owner = models.ForeignKey(TblUser, db_column="owner", on_delete=models.SET_NULL,
                              null=True, blank=True)
    public = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)

    @property
    def items(self):
        """
        Маппинг списка текстов с текстами
        :return:
        """
        return TblTextListItems.objects.filter(list_id=self.id).order_by('text_id').all()

    @property
    def item_ids(self):
        """
        Получение списка прицепленных идентификаторов текстов
        :return:
        """
        return TblTextListItems.objects.filter(list_id=self.id).values_list('text', flat=True).all()

    def append_text(self, text_id: int):
        """
        Добавление нового текста к списку
        :param text_id: идентификатор нового текста
        """
        text = TblText.objects.get(id=text_id)
        item = TblTextListItems(list=self, text=text)
        item.save()

    def remove_text(self, text_id: int):
        """
        Удаление текста из списка
        :param text_id: идентификатор удаляемого текста
        """
        item = TblTextListItems.objects.filter(list__id=self.id, text__id=text_id).first()
        if not item:
            raise ValueError(f"Текст {text_id} в списке {self.id} не найден")
        item.delete()

    @classmethod
    def get_items(cls, user = AnonymousUser, exclude_deleted: bool = True):
        text_lists = TblTextListDescription.objects

        if exclude_deleted:
            text_lists = text_lists.filter(is_deleted=False)
        if not user.is_authenticated:
            text_lists = text_lists.filter(public=True)
        else:
            if not user.has_level(TblUser.LEVEL_ADMIN):
                text_lists = text_lists.filter(owner=user)
        return text_lists

    @classmethod
    def get_item(cls, user = AnonymousUser, group_id: int = None):
        """
        Получение одного элемента по Id с проверкой прав
        """
        ret = TblTextListDescription.objects.get(id=group_id)
        if user.is_anonymous or not user.is_authenticated:
            if not ret.public:
                raise TblTextListDescription.DoesNotExist
        else:
            if not user.has_level(TblUser.LEVEL_ADMIN):
                if ret.owner != user:
                    raise TblTextListDescription.DoesNotExist
        return ret

class TblTextListItems(models.Model):
    """
    Модель связи списка текстов с текстом
    """
    class Meta:
        db_table = 'textlist_items'

    id = models.AutoField(primary_key=True)
    list = models.ForeignKey(TblTextListDescription, db_column="listid", on_delete=models.CASCADE)
    text = models.ForeignKey(TblText, db_column="textid", on_delete=models.CASCADE)

    def get_content(self):
        return self.text.get_content()
