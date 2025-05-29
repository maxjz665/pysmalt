"""
Модель разбора слова
"""

from django.db import models
from django.db.models import Count, Min, F, Value, IntegerField, Func
from text_app.models.tbl_menu_items import TblMenuItems
from text_app.models.tbl_menu_params import TblMenuParams
from django.db.models import Q


class Sign(Func):
    function = 'SIGN'


class AbstractDictWord(models.Model):
    """
        Модель разбора слова
        """

    class Meta:
        abstract = True

    id = models.AutoField(primary_key=True)
    word = models.TextField()
    initial_form = models.TextField()
    param_01 = models.IntegerField(default=0)
    param_02 = models.IntegerField(default=0)
    param_03 = models.IntegerField(default=0)
    param_04 = models.IntegerField(default=0)
    param_05 = models.IntegerField(default=0)
    param_06 = models.IntegerField(default=0)
    param_07 = models.IntegerField(default=0)
    param_08 = models.IntegerField(default=0)
    param_09 = models.IntegerField(default=0)
    param_10 = models.IntegerField(default=0)
    param_11 = models.IntegerField(default=0)
    param_12 = models.IntegerField(default=0)
    param_13 = models.IntegerField(default=0)
    param_14 = models.IntegerField(default=0)
    param_15 = models.IntegerField(default=0)
    param_16 = models.IntegerField(default=0)
    param_17 = models.IntegerField(default=0)
    param_18 = models.IntegerField(default=0)
    param_19 = models.IntegerField(default=0)
    param_20 = models.IntegerField(default=0)
    current_status = models.IntegerField(default=0)
    params_count = models.IntegerField(default=0)
    modern = models.TextField()


class TblDictWord(AbstractDictWord):
    class Meta:
        db_table = 'entries'

    @classmethod
    def get_word(cls, id):
        return cls.objects.filter(id=id).first()

    """
    Поиск слов в entries (по полям WORD, MODERN и INITIAL_FORM
    """

    @classmethod
    def get_best_match_by_field(cls, field_name, word_variants, param_01=None):
        if field_name not in ['word', 'modern', 'initial_form']:
            raise ValueError("field_name must be one of: 'word', 'modern', 'initial_form'")

        filter_kwargs = {f"{field_name}__in": word_variants}
        if not param_01:
            return (
                cls.objects
                    .filter(**filter_kwargs)
                    .exclude(param_01__in=[16, 19, 22])
                    .values('param_01')
                    .annotate(
                    ID=Min('id'),
                    cnt=Count('id'),
                    sgnn=Sign(F('param_01') + Value(1), output_field=IntegerField())
                )
                    .order_by('-sgnn', '-cnt')
            )
        else:
            filter_kwargs['param_01'] = param_01
            return (
                cls.objects
                    .filter(**filter_kwargs)
                    .values('param_01')
                    .annotate(
                    ID=Min('id'),
                    cnt=Count('id'),
                    sgnn=Sign(F('param_01') + Value(1), output_field=IntegerField())
                )
                    .order_by('-sgnn', '-cnt')
            )

    @staticmethod       # Получает список частей речи и их id
    def get_attrs():
        menu_items = TblMenuItems.objects.all()
        menu_params = TblMenuParams.objects.all()
        attrs = []
        i = 0
        for item in menu_params[0]._meta.fields[3:26]:
            item_id = int(getattr(menu_params[0], item.name))
            attrs.append({
                "id": i,
                "name": menu_items[item_id].item_caption,
            })
            i += 1
        return attrs


    @staticmethod       # Получение морфологии для слова
    def get_dictword_attrs(dictword, attrs_data, res, index):
        params_data = dictword._meta.fields[3:22]
        params_count = dictword.params_count
        for attr in attrs_data:
            if index == 1:
                index += 1
                param_id = getattr(dictword, params_data[index].name)
            else:
                param_id = getattr(dictword, params_data[index].name)
            res.append({
                "id": param_id,
                "name": attr['name'],
                "value": attr['values'][param_id]["name"]
            })
            if len(attr['values'][param_id]["values"]) != 0:
                index = TblDictWord.get_dictword_attrs(dictword, attr['values'][param_id]["values"], res, index + 1) - 1
            if index >= params_count:
                break
            index += 1
        return index

    @staticmethod       # Получение всех атрибутов и признаков
    def get_all_attrs(index, data):
        menu_items = TblMenuItems.objects.all()
        menu_params = TblMenuParams.objects.all()
        param_caption = menu_params[index].param_caption
        # print(param_caption)
        data.append({
            "id": index,
            "name": param_caption,
            "values": [],
        })
        items_count = int(menu_params[index].items_count)
        items_fields = menu_params[index]._meta.fields[3:3 + items_count]
        for items_field in items_fields:
            item_id = int(getattr(menu_params[index], items_field.name))
            item_caption = menu_items[item_id].item_caption
            # print(item_caption)
            values = list(filter(lambda item: item['name'] == param_caption, data))[0]["values"]
            # print(values)
            values.append({
                "id": item_id,
                "name": item_caption,
                "values": [],
            })
            params_count = int(menu_items[item_id].params_count)
            params_fields = menu_items[item_id]._meta.fields[3:3 + params_count]
            for param_field in params_fields:
                param_id = int(getattr(menu_items[item_id], param_field.name))
                values_1 = list(filter(lambda item: item['name'] == item_caption, values))[0]["values"]
                values_1 = TblDictWord.get_all_attrs(param_id, values_1)
        return data


class TblDictWord2(AbstractDictWord):
    class Meta:
        db_table = 'entries2'
