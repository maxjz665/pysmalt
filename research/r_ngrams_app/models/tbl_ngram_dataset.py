"""
Задача расчета частоты встречаемости N-грамм по группе текстов или по всем текстам
"""
from collections import namedtuple, deque

from django.contrib.auth.models import AnonymousUser
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

    @classmethod
    def get_item(cls, user = AnonymousUser, list_id: int = None):
        """
        Получение данных N-граммы с проверкой прав пользователя
        """
        ret = TblBigramDataset.objects.get(id=list_id)
        if user.is_anonymous or not user.is_authenticated:
            if not ret.is_public:
                raise TblTextListDescription.DoesNotExist
        else:
            if not user.has_level(TblUser.LEVEL_ADMIN):
                if ret.owner != user:
                    raise TblTextListDescription.DoesNotExist
        return ret


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
        for item in self.content:  # подготавливаем словарь для работы с текстом
            dataset[item[0]] = StatData(item[1], len(dataset))
            total_ngrams += item[1]["count"]
        total_ngrams = 1000 / total_ngrams # делаем множитель для нормализации значений по словарю

        ngrams = self.extract_ngrams(text_id, text_data)  # получаем распределение N-грамм по всему тексту
        block_ngrams = self.extract_block_ngrams(text_id, text_data, block_size)  # расчет N-грамм по блокам текста

        ret_total = self._filter_ngrams(dataset, total_ngrams, ngrams)

        ret_blocks = []
        for item in block_ngrams:
            ret_blocks.append({'start': item['start'], 'end': item['end'], 'ngrams': self._filter_ngrams(dataset, total_ngrams, item['ngrams'])})

        return ret_total, ret_blocks, len(ngrams)

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

        # последний блок в тексте
        start_pos = max(0, len(text_data) - block_size)
        result.append({'start': start_pos, 'end': len(text_data), 'ngrams': self.extract_ngrams(text_id, text_data[start_pos:])})
        return result

    def check_group(self, text_id: int, text_content, block_size, group):
        """
        Сравнение спектра текста и группы

        :param text_id идентификатор рассматриваемого текста
        :param text_content содержимое текста
        :param block_size размер блока
        :param group список текстов для сравнения
        """
        # получаем спектры исходного текста
        target_ngrams, target_block_ngrams, target_len = self.check_text(text_id, text_content, block_size)

        # получаем спектры для текстов из группы
        group_ngrams = []
        for item in group:
            if item['text_id'] == text_id:
                continue
            text_ngrams, block_ngrams, text_len = self.check_text(item['text_id'], item['content'], block_size)
            group_ngrams.append({"text_id": item['text_id'], "text_ngrams": text_ngrams, "block_ngrams": block_ngrams, "text_len": text_len})


        # выполняем расчет дистанции для каждого текста из группы с исходным текстом
        min_distance = None
        min_iid = None  # идентификатор текста с мин расстоянием
        sum_distance = 0
        max_distance = 0
        max_iid = None  # идентификатор текста с максимумом расстояния
        for item in group_ngrams:
            distance = self._calc_distance(target_ngrams, target_len, item['text_ngrams'], item["text_len"])
            if min_distance is None or distance < min_distance:
                min_iid = item['text_id']
                min_distance = distance
            sum_distance += distance
            if distance > max_distance:
                max_distance = distance
                max_iid = item['text_id']


        # расчет дистанции для блока текста
        ret_block_ngrams = []
        for target_block in target_block_ngrams:
            min_block = None
            min_id = None
            min_part = None
            sum_block = 0
            max_block = 0
            max_id = None
            max_part = None
            block_count = 0

            for item in group_ngrams:
                block_count += len(item['block_ngrams'])
                for item_block in item['block_ngrams']:
                    distance = self._calc_distance(target_block["ngrams"], block_size, item_block["ngrams"], block_size)
                    if min_block is None or distance < min_block:
                        min_block = distance
                        min_id = item["text_id"]
                        min_part = f"{item_block['start']}-{item_block['end']}"
                    sum_block += distance
                    if distance > max_block:
                        max_block = distance
                        max_id = item["text_id"]
                        max_part = f"{item_block['start']}-{item_block['end']}"
            ret_block_ngrams.append({"start": target_block["start"], "end": target_block["end"], "min": min_block,
                                     "min_id": min_id, "min_part": min_part, "avg": sum_block / block_count, "max": max_block, "max_id": max_id,
                                     "max_part": max_part})

        return {"min": min_distance, "min_id": min_iid, "avg": sum_distance / len(group_ngrams), "max": max_distance,
                "max_id": max_iid, "ngrams": target_ngrams}, {"ngrams": target_block_ngrams, "result": ret_block_ngrams}

    @staticmethod
    def _calc_distance(target_ngrams: list, total_target: int, other_ngrams: list, total_other: int):
        """
        Расчет манхеттенского расстояния между спектрами

        :param target_ngrams исходный список n-грамм
        :param total_target размер исходного блока
        :param other_ngrams конечный список n-грамм
        :param total_other размер конечного блока
        """
        dist_vector = {}
        for item in target_ngrams:
            dist_vector[item.dict_pos] = item.value

        for item in other_ngrams:
            if item.dict_pos in dist_vector:
                dist_vector[item.dict_pos] = dist_vector[item.dict_pos] - item.value
            else:
                dist_vector[item.dict_pos] = item.value

        return sum(abs(x) for x in dist_vector.values())
