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

    @staticmethod
    def _filter_ngrams(dataset: dict, total_ngrams: float, ngrams: dict):
        """
        Выборка N-грамм из словаря
        """
        ResultItem = namedtuple("ResultItem", ['ngram', 'value', 'dict_value', 'dict_pos'])

        ret = []
        for item in ngrams:
            if item in dataset.keys():
                ret.append(ResultItem(item, ngrams[item]["count"], dataset[item].value["count"] * total_ngrams, dataset[item].pos))
        ret.sort(key=lambda x: x.dict_pos)
        return ret


    def check_text(self, text_id: int, text_data: set, block_size: int):
        """
        Построение лексического спектра для данного текста
        """
        dataset = {}
        StatData = namedtuple('StatData', ['value', 'pos'])
        total_ngrams = 0
        for item in self.content:  # подгатавливаем словарь для работы с текстом
            dataset[item[0]] = StatData(item[1], len(dataset))
            total_ngrams += item[1]["count"]
        total_ngrams = 1000 / total_ngrams # делаем множитель для нормализации значений по словарю

        ngrams = self.extract_ngrams(text_id, text_data)  # получаем распределение N-грамм по всему тексту
        block_ngrams = self.extract_block_ngrams(text_id, text_data, block_size)  # расчет N-грамм по блокам текста

        ret_total = self._filter_ngrams(dataset, total_ngrams, ngrams)

        ret_blocks = []
        for item in block_ngrams:
            ret_blocks.append({'start': item['start'], 'end': item['end'], 'ngrams': self._filter_ngrams(dataset, total_ngrams, item['ngrams'])})

        return ret_total, ret_blocks

    def extract_ngrams(self, text_id: int, content, result=None):
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
                if len(ngram_item) < self.ngram_size:  # если все еще мало, то идем на след.слово
                    continue
            else:
                raise ValueError("Превышение размера стека N-грамм: " + str(self.ngram_size))

            # если дошли до сюда, то у нас есть N-грамма, запоминаем ее
            key = " - ".join(map(lambda x: x.word.lower(), ngram_item))
            if key in result:
                result[key] = {"count": result[key]["count"] + 1, "text": result[key]["text"] if text_id in result[key]["text"] else result[key]["text"] + list([text_id])}
            else:
                result[key] = {"count":1, "text":[text_id]}
        return result

    @staticmethod
    def ngram_pos(ngram_item: str, content: list):
        """
        Получение позиций N-грамм в тексте с учетом параметров датасета
        """
        ngram_data = ngram_item.split(" - ")
        ngram_len = len(ngram_data)
        ret = []

        for idx, item in enumerate(content):
            if item.word.lower() == ngram_data[0]:
                is_found = True
                for pos in range(ngram_len):
                    if content[pos + idx].word.lower() != ngram_data[pos]:
                        is_found = False
                        break
                if is_found:
                    ret.append({"start": idx, "end": ngram_len + idx, "pros": 100, "cons": 0})

        return ret

    def extract_block_ngrams(self, text_id, text_data, block_size):
        """
        Расчет N-грамм по блокам текста
        """
        result = []

        total_full_blocks = len(text_data) * 2 // block_size - 1
        for i in range(total_full_blocks):
            start_pos = i * block_size // 2
            result.append({'start': start_pos, "end": start_pos + block_size, "ngrams": self.extract_ngrams(text_id, text_data[start_pos:start_pos + block_size])})

        result.append({'start': len(text_data) - block_size, 'end': len(text_data), 'ngrams': self.extract_ngrams(text_id, text_data[len(text_data) - block_size:])})
        return result