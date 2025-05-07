"""
Модель разбора слова
"""

from django.db import models
from django.db.models import Count, Min, F, Value, IntegerField, Func
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

    '''@classmethod
    def get_best_match(cls, word_variants):
        result = (
            cls.objects
                .filter(word__in=word_variants)
                .exclude(param_01__in=[16, 19, 22])
                .values('param_01')
                .annotate(
                ID=Min('id'),
                cnt=Count('id'),
                sgnn=Sign(F('param_01') + Value(1), output_field=IntegerField())
            )
                .order_by('-sgnn', '-cnt')
        )
        return result'''


class TblDictWord2(AbstractDictWord):
    class Meta:
        db_table = 'entries2'
