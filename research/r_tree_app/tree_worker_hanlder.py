"""
Обработчик команд из брокера сообщений
"""
import asyncio
import json
import logging
from datetime import datetime, timezone
from json import JSONDecodeError

from aiomqtt import MqttError, Client
from asgiref.sync import sync_to_async
from sklearn import ensemble, tree

from research.r_tree_app.models.tbl_tree_description import TblTreeDescription
from research.r_tree_app.utils import get_pos
from shower.settings import BROKER_HOST, BROKER_PORT
from text_app.models.tbl_textlist import TblTextListDescription
from text_app.models.tbl_word import TblWord


class TreeWorkerHandler(object):

    async def run(self):
        """
        Запуск бесконечного цикла обработки сообщений
        """
        reconnect_interval = 5  # In seconds
        while True:
            try:
                async with Client(BROKER_HOST, BROKER_PORT, identifier="tg_bot_" + str(id(self))) as client:
                    logging.debug("TG bot broker connected successfully")
                    await client.subscribe("service/tree_worker/#")
                    async for message in client.messages:
                        topic = str(message.topic)
                        logging.error("Got message from topic: %s", topic)
                        if topic == "service/tree_worker/build":
                            try:
                                await self.build_tree(json.loads(message.payload))
                            except JSONDecodeError:
                                logging.error("JSON decode error")

            except MqttError as error:
                print(f'Error "{error}". Reconnecting in {reconnect_interval} seconds.')
                await asyncio.sleep(reconnect_interval)
            except KeyboardInterrupt:
                return

    @staticmethod
    def _generate_table(text_list: TblTextListDescription, block_size: int, dict_size: int) -> list:
        """
        Генерация таблицы признаков по блокам текстов
        :param text_list: список текстов
        :param block_size: размер блока
        :return: таблица частот встречаемости частей речи в блоках текста
        """
        word_index = 0
        ret = []  # матрица переходов по блокам текста
        ret_item = [0] * dict_size * dict_size  # найденные переходы в текущем блоке текста
        for text in text_list.items:  # бежим по текстам и вытаскиваем слова из текста
            text_data = TblWord.objects.filter(text_id=text.text.id).order_by("chapter_index",
                                                                              "paragraph_index",
                                                                              "sentence_index",
                                                                              "word_index").all()
            prev_pos = -1  # предыдущая часть речи
            for word in text_data:  # бежим по словам, вытаскиваем часть речи и строим таблицу переходов
                part_of_speech = word.dictword.param_01
                if part_of_speech < 0:  # если битая часть речи, то пропускаем
                    prev_pos = -1
                    continue
                if prev_pos < 0:  # если это первое слово в N-грамме, то запоминаем его
                    prev_pos = part_of_speech
                    continue
                ret_item[prev_pos * dict_size + part_of_speech] += 1
                word_index += 1
                if word_index >= block_size:
                    ret.append(ret_item)
                    ret_item = [0] * dict_size * dict_size

                    word_index = 0
        return ret

    @staticmethod
    def _generate_features(pos, sector_size: float, many_sectors: bool) -> list:
        """
        Построение пар "часть_речи-часть_речи" и "часть-часть(доля)=часть-часть(доля)"
        """
        ret = []
        for item1 in pos:
            for item2 in pos:
                ret.append(item1 + "-" + item2)
        if 0 < sector_size < 100:
            # у нас разделитель - дополняем таблицу пар комбинациями часть-часть(доля)=часть-часть(доля)
            origin_size = len(ret)
            if many_sectors:
                n = 1.0
                while n * sector_size < 100:
                    ret.extend(TreeWorkerHandler._generate_subfeatures(ret, origin_size, n * sector_size))
                    n += 1.0
            else:
                ret.extend(TreeWorkerHandler._generate_subfeatures(ret, origin_size, sector_size))
        return ret

    @staticmethod
    def _generate_subfeatures(items: list, origin_size: int, sector_size: float) -> list:
        pos_ret = []
        neg_ret = []
        for i in range(origin_size):
            for j in range(origin_size):
                pos_ret.append(items[i] + f"({sector_size / 100}) + " + items[j] + f"({(100 - sector_size) / 100})")
                neg_ret.append(items[i] + f"({sector_size / 100}) - " + items[j] + f"({(100 - sector_size) / 100})")
        return [*pos_ret, *neg_ret]

    def _generate_slice(self, table: list, sector_size: float, many_sectors: bool) -> list:
        ret = []
        for item in table:
            ret_row = [*item]
            if many_sectors:
                n = 1.0
                while n * sector_size < 100:
                    ret_row.append(*self._generate_subslice(item, n * sector_size))
                    n += 1.0
            else:
                ret_row.append(*self._generate_subslice(item, sector_size))
            ret.append(ret_row)
        return ret

    @staticmethod
    def _generate_subslice(record: list, sector_size: float) -> list:
        """
        Генерация записей с поворотами, т.е. (sector_size*x + (100-sector_size)*y)/100 и (sector_size*x - (100-sector_size)*y)/100
        """
        pos_ret = []
        neg_ret = []
        for i in record:
            for j in record:
                pos_ret.append((sector_size * i + (100 - sector_size) * j) / 100)
                neg_ret.append((sector_size * i - (100 - sector_size) * j) / 100)
        return [*pos_ret, *neg_ret]

    @sync_to_async
    def build_tree(self, params):
        """
        Построение дерева решений для заданного проекта
        """
        if "project_id" not in params:
            logging.error("Missing project_id")
            return

        try:
            tree_data = TblTreeDescription.objects.get(id=params["project_id"])
        except TblTreeDescription.DoesNotExist:
            logging.error("Invalid project_id")
            return

        tree_data.build_status = "Построение матриц"
        tree_data.save()

        # перестраиваем дерево решений
        pos = get_pos()
        len_pos = len(pos)
        table1 = self._generate_table(tree_data.first_list, tree_data.block_size, len_pos)
        table2 = self._generate_table(tree_data.second_list, tree_data.block_size, len_pos)
        features = self._generate_features(pos, tree_data.sector_size, tree_data.many_sectors)
        logging.error(f"project: %s: table1: %s, table2: %s", params['project_id'], len(table1), len(table2))
        min_size = min(len(table1), len(table2))
        table1 = table1[:min_size]
        table2 = table2[:min_size]
        if 0 < tree_data.sector_size < 100:
            tree_data.build_status = "Построение разделителей"
            tree_data.save()
            table1 = self._generate_slice(table1, tree_data.sector_size, tree_data.many_sectors)
            table2 = self._generate_slice(table1, tree_data.sector_size, tree_data.many_sectors)
        tree_data.build_status = "Построение дерева"
        tree_data.save()
        result = [0] * min_size + [1] * min_size
        clf = ensemble.RandomForestClassifier()
        clf = clf.fit(table1 + table2, result)
        tree_data.build_status = "Выполнено"
        tree_data.build_at = datetime.now(timezone.utc)
        classes = ["list1", "list2"]
        dot_data = tree.export_graphviz(clf.estimators_[0], out_file=None, feature_names=features, class_names=classes)
        tree_data.graph_dot = dot_data
        tree_data.graph_pickle = clf
        tree_data.save()
        # graph = graphviz.Source(dot_data)
        # graph.render("iris")
        logging.error(f"project: %s: done", params['project_id'])
