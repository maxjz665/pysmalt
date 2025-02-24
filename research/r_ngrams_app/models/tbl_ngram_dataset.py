"""
Задача расчета частоты встречаемости N-грамм по группе текстов или по всем текстам
"""
from collections import namedtuple, deque

from django.db import models

from shower.models import BaseModel
from text_app.models.tbl_textlist import TblTextListDescription
from user_app.models import TblUser


class TblBigramDataset(BaseModel):
    """
    Задача расчета частоты встречаемости N-грамм по группе текстов или по всем текстам
    """
    class Meta:
        db_table = 'r_ngram_dataset'
        db_table_comment = 'Датасеты N-грамм для групп текстов'

    id = models.AutoField(primary_key=True)
    name = models.TextField(max_length=200, db_comment='Название датасета')
    owner = models.ForeignKey(TblUser, db_column="owner", on_delete=models.SET_NULL,
                              null=True, blank=True, db_comment='Владелец датасета')
    is_public = models.BooleanField(default=False, db_comment='Публичный доступ к датасету')
    ngram_size = models.IntegerField(db_default=2, db_comment='Размер N-граммы')
    max_ngrams = models.IntegerField(default=100, db_comment='Максимальное число N-грамм в датасете')
    min_occurrence = models.IntegerField(default=1, db_comment='Минимальное количество встречаемости N-граммы')
    text_group = models.ForeignKey(TblTextListDescription, db_column='text_group', on_delete=models.SET_NULL,
                                   null=True, blank=True, db_comment="Группа текстов или все доступные тексты")
    is_use_initial = models.BooleanField(default=False, db_comment='расчет N-грамм по словоформам (False) или по начальным значениям (True)')
    is_sentence_split = models.BooleanField(default=True, db_comment='расчет N-грамм по предложениям или по абзацам')
    content = models.JSONField(default=list, db_comment='Перечень N-грамм')
    build_at = models.DateTimeField(null=True, default=None, db_comment="Время последней сборки")
    build_status = models.TextField(max_length=200, db_comment="Статус сборки", null=True)

    def check_text(self, text_data):
        """
        Построение лексического спектра для данного текста
        """
        dataset = {}
        StatData = namedtuple('StatData', ['value', 'pos'])
        total_ngrams = 0
        for item in self.content:
            dataset[item[0]] = StatData(item[1], len(dataset))
            total_ngrams += item[1]
        ret = []
        total_ngrams = 1000 / total_ngrams # делаем множитель для нормализации значений по словарю

        ngrams = self.extract_ngrams(text_data)

        ResultItem = namedtuple("ResultItem", ['ngram', 'value', 'dict_value', 'dict_pos'])
        for item in ngrams:
            if item in dataset.keys():
                ret.append(ResultItem(item, ngrams[item], dataset[item].value * total_ngrams, dataset[item].pos))
        ret.sort(key=lambda x: x.dict_pos)
        return ret

    def extract_ngrams(self, content, result=None):
        """
        Извлечение лексического спектра из текста
        """
        if result is None:
            result = {}

        ngram_item: deque = deque()  # содержимое N-граммы
        last_item = None  # последний рассмотренный элемент
        for item in content:
            if last_item is None or (
            item.is_new_sentence(last_item) if self.is_sentence_split else item.is_new_paragraph(last_item)):
                # если новое предложение или первый токен, то сохраняем его
                ngram_item.clear()
                ngram_item.appendleft(item)
                last_item = item
                continue

            if len(ngram_item) == self.ngram_size:
                # если очередь заданной длины, то удаляем последний и добавляем первый
                ngram_item.popleft()
                ngram_item.append(item)
                last_item = item
            elif len(ngram_item) < self.ngram_size:
                # если не добрало до заданной длины, то добавляем в очередь элемент
                ngram_item.append(item)
                last_item = item
                continue
            else:
                raise ValueError("Превышение размера стека N-грамм: " + str(self.ngram_size))

            # если дошли до сюда, то у нас есть N-грамма, запоминаем ее
            key = " - ".join(map(lambda x: x.word, ngram_item))
            if key in result:
                result[key] += 1
            else:
                result[key] = 1
        return result

    def ngram_pos(self, ngram_item: str, content: list):
        """
        Получение позиций N-грамм в тексте с учетом параметров датасета
        """
        ngram_data = ngram_item.split(" - ")
        ngram_len = len(ngram_data)
        ret = []

        for idx, item in enumerate(content):
            if item.word.lower() == ngram_data[0]:
                print(idx)
                is_found = True
                for pos in range(ngram_len):
                    if content[pos + idx].word.lower() != ngram_data[pos]:
                        print(pos+idx, content[pos + idx].word.lower(), pos, ngram_data[pos])
                        is_found = False
                        break
                if is_found:
                    ret.append({"start": idx, "end": ngram_len + idx, "pros": 100, "cons": 0})

        return ret