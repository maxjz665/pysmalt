"""
Обработчик команд из брокера сообщений
"""
import asyncio
import json
import logging
import time
from json import JSONDecodeError

import graphviz
from aiomqtt import MqttError, Client
from asgiref.sync import sync_to_async
from sklearn import tree

from research.r_tree_app.models.tbl_tree_description import TblTreeDescription
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
                        logging.error("Got message from topic: " + topic)
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
    def _generate_table(text_list: TblTextListDescription, block_size: int, dict_size: int) -> []:
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
                if prev_pos < 0:  # если это первое слово в биграмме, то запоминаем его
                    prev_pos = part_of_speech
                    continue
                ret_item[prev_pos * dict_size + part_of_speech] += 1
                word_index += 1
                if word_index >= block_size:
                    ret.append(ret_item)
                    ret_item = [0] * dict_size * dict_size

                    word_index = 0
        return ret

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

        # перестраиваем дерево решений
        table1 = self._generate_table(tree_data.first_list, tree_data.block_size, 23)
        table2 = self._generate_table(tree_data.second_list, tree_data.block_size, 23)
        logging.error(f"project: {params['project_id']}: table1: {len(table1)}, table2: {len(table2)}")
        min_size = min(len(table1), len(table2))
        table1 = table1[:min_size]
        table2 = table2[:min_size]
        result = [0] * min_size + [1] * min_size
        clf = tree.DecisionTreeClassifier()
        clf = clf.fit(table1 + table2, result)
        dot_data = tree.export_graphviz(clf, out_file=None)
        tree_data.build_time = time.ctime()
        tree_data.graph = dot_data
        tree_data.save()
        # graph = graphviz.Source(dot_data)
        # graph.render("iris")
        logging.error(f"project: {params['project_id']}: done")