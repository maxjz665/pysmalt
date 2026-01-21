"""
Обработчик команд из брокера сообщений
"""
import asyncio
import json
import logging
from datetime import datetime, timezone

from asgiref.sync import sync_to_async
from sklearn import ensemble, tree
from sklearn.metrics import accuracy_score

from research.r_tree_app.models.tbl_tree_description import TblTreeDescription
from research.r_tree_app.utils import get_pos, generate_subslice, fix_pos
from text_app.models.tbl_textlist import TblTextListDescription
from text_app.models.tbl_word import TblWord


class TreeWorkerHandler(object):


    async def run(self):
        """
        Запуск бесконечного цикла обработки сообщений
        """
        reconnect_interval = 15  # In seconds
        while True:
            item = await self.get_task()
            if item is not None:
                logging.error("Found not calculated item with id=%s", item.id)
                await TreeWorkerHandler.build_tree(item)
            else:
                await asyncio.sleep(reconnect_interval)

    @sync_to_async
    def get_task(self):
        try:
            return TblTreeDescription.objects.filter(build_at=None, is_deleted=False).first()
        except TblTreeDescription.DoesNotExist:
            return None

    @staticmethod
    def _generate_table(text_list: TblTextListDescription, block_size: int, dict_size: int, removed_pos:list, is_need_uno: bool, is_need_duo: bool) -> list:
        """
        Генерация таблицы признаков по блокам текстов
        :param text_list: список текстов
        :param block_size: размер блока
        :param dict_size: размер словарика
        :param is_need_uno: требуется ли генерация статистик по унограммам
        :param is_need_duo: требуется ли генерация статистик по биграммам
        :return: таблица частот встречаемости частей речи в блоках текста [унограммы, биграммы]
        """
        word_index = 0
        ret = []  # матрица переходов по блокам текста
        ret_single_item = [0] * dict_size  # статистика по унограммам
        ret_double_item = [0] * dict_size * dict_size  # найденные переходы в текущем блоке текста
        for text in text_list.items:  # бежим по текстам и вытаскиваем слова из текста
            text_data = TblWord.objects.filter(text_id=text.text.id).order_by("chapter_index",
                                                                              "paragraph_index",
                                                                              "sentence_index",
                                                                              "word_index").all()
            prev_pos = -1  # предыдущая часть речи
            for word in text_data:  # бежим по словам, вытаскиваем часть речи и строим таблицу переходов
                part_of_speech = word.dictword.param_01
                if part_of_speech < 0 or part_of_speech in removed_pos:  # если битая часть речи, то пропускаем
                    prev_pos = -1
                    continue
                if prev_pos < 0:  # если это первое слово в N-грамме, то запоминаем его
                    ret_single_item[fix_pos(part_of_speech, removed_pos)] += 1
                    prev_pos = part_of_speech
                    continue
                ret_single_item[fix_pos(part_of_speech, removed_pos)] += 1
                ret_double_item[fix_pos(prev_pos, removed_pos) * dict_size + fix_pos(part_of_speech, removed_pos)] += 1
                word_index += 1
                prev_pos = part_of_speech
                if word_index >= block_size:
                    if is_need_uno:
                        if is_need_duo:
                            ret.append([*ret_single_item, *ret_double_item])
                        else:
                            ret.append(ret_single_item)
                    else:
                        if is_need_duo:
                            ret.append(ret_double_item)
                        else:
                            logging.error("Не заданы параметры генерации")
                    ret_single_item = [0] * dict_size
                    ret_double_item = [0] * dict_size * dict_size

                    word_index = 0
                    prev_pos = -1
        return ret

    @staticmethod
    def _generate_features(pos, removed_pos: list, sector_size: float, many_sectors: bool, is_need_uno: bool, is_need_duo: bool, is_need_separate: bool) -> list:
        """
        Построение пар "часть_речи-часть_речи" и "часть-часть(доля)=часть-часть(доля)"
        """
        ret = []
        if is_need_uno:
            for idx in range(len(pos)):
                if idx in removed_pos: continue  # если часть речи в списке исключенных, то пропускаем
                ret.append(str(pos[idx]))
        if is_need_duo:
            for idx1 in range(len(pos)):
                if idx1 in removed_pos: continue # если часть речи в списке исключенных, то пропускаем
                for idx2 in range(len(pos)):
                    if idx2 in removed_pos: continue # если часть речи в списке исключенных, то пропускаем
                    ret.append(pos[idx1] + "-" + pos[idx2])
        if is_need_separate and 0 < sector_size < 100:
            # у нас разделитель - дополняем таблицу пар комбинациями часть-часть(доля)=часть-часть(доля)
            origin_size = len(pos)
            if many_sectors:
                n = 1.0
                while n * sector_size < 100:
                    ret.extend(TreeWorkerHandler._generate_subfeatures(pos, removed_pos, n * sector_size))
                    n += 1.0
            else:
                ret.extend(TreeWorkerHandler._generate_subfeatures(pos, removed_pos, sector_size))
        return ret

    @staticmethod
    def _generate_subfeatures(pos: list, removed_pos: list, sector_size: float) -> list:
        pos_ret = []
        neg_ret = []
        for i in range(len(pos)):
            if i in removed_pos: continue # если часть речи в списке исключенных, то пропускаем
            for j in range(len(pos)):
                if j in removed_pos: continue # если часть речи в списке исключенных, то пропускаем
                if i == j:
                    continue
                pos_ret.append(pos[i] + f"({sector_size / 100})+" + pos[j] + f"({(100 - sector_size) / 100})")
                neg_ret.append(pos[i] + f"({sector_size / 100})-" + pos[j] + f"({(100 - sector_size) / 100})")
        return [*pos_ret, *neg_ret]

    @staticmethod
    def _generate_slice(table: list, len_pos: int, sector_size: float, many_sectors: bool) -> list:
        assert 0 < sector_size < 100
        ret = []
        for item in table:
            ret_row = [*item]
            if many_sectors:
                n = 1.0
                while n * sector_size < 100:
                    ret_row.extend(generate_subslice(item, len_pos, n * sector_size))
                    n += 1.0
            else:
                ret_row.extend(generate_subslice(item, len_pos, sector_size))
            ret.append(ret_row)
        return ret

    @staticmethod
    @sync_to_async
    def build_tree(tree_data: TblTreeDescription):
        """
        Построение дерева решений для заданного проекта
        """

        tree_data.accuracy = 0
        tree_data.build_status = "Построение матрицы списка 1"
        tree_data.save()

        # перестраиваем дерево решений
        pos = get_pos()
        removed_pos = json.loads(tree_data.removed_pos)
        len_pos = len(pos) - len(removed_pos)
        # т.к. для разделителей требуются унограммы, то мы их тоже строим
        table1 = TreeWorkerHandler._generate_table(tree_data.first_list, tree_data.block_size, len_pos, removed_pos, tree_data.is_need_uno or tree_data.is_need_separate, tree_data.is_need_duo)
        tree_data.build_status = "Построение матрицы списка 2"
        tree_data.save()
        table2 = TreeWorkerHandler._generate_table(tree_data.second_list, tree_data.block_size, len_pos, removed_pos, tree_data.is_need_uno or tree_data.is_need_separate, tree_data.is_need_duo)
        features = TreeWorkerHandler._generate_features(pos, removed_pos, tree_data.sector_size, tree_data.many_sectors, tree_data.is_need_uno, tree_data.is_need_duo, tree_data.is_need_separate)
        logging.error(f"project: %s: table1: %s, table2: %s", tree_data.id, len(table1), len(table2))
        min_size = min(len(table1), len(table2))
        tree_data.table1_size = len(table1)
        tree_data.table2_size = len(table2)
        table1 = table1[:min_size]
        table2 = table2[:min_size]
        if tree_data.is_need_separate and 0 < tree_data.sector_size < 100:
            tree_data.build_status = "Построение разделителей"
            tree_data.save()
            table1 = TreeWorkerHandler._generate_slice(table1, len_pos, tree_data.sector_size, tree_data.many_sectors)
            table2 = TreeWorkerHandler._generate_slice(table2, len_pos, tree_data.sector_size, tree_data.many_sectors)
            # удаляем унограммы если они не нужны
            if not tree_data.is_need_uno:
                table1 = TreeWorkerHandler._remove_uno(table1, len_pos)
                table2 = TreeWorkerHandler._remove_uno(table2, len_pos)
        tree_data.build_status = "Построение дерева"
        tree_data.save()
        result = [0] * min_size + [1] * min_size
        max_score = 0
        for i in range(10):
            clf = ensemble.RandomForestClassifier(n_estimators=(100 if min_size < 100 else min_size), max_depth=tree_data.max_depth, bootstrap=False)
            clf = clf.fit(table1 + table2, result)
            y_pred = clf.predict(table1 + table2)
            if accuracy_score(result, y_pred) > max_score:
                max_score = accuracy_score(result, y_pred)
                tree_data.accuracy = max_score
                classes = ["list1", "list2"]
                dot_data = tree.export_graphviz(clf.estimators_[0], out_file=None, feature_names=features, class_names=classes)
                tree_data.graph_dot = dot_data
                tree_data.graph_pickle = clf
                tree_data.save()
        tree_data.vector_size = len(table1[0])
        tree_data.build_status = "Выполнено"
        tree_data.build_at = datetime.now(timezone.utc)
        tree_data.save()
        # graph = graphviz.Source(dot_data)
        # graph.render("iris")
        logging.error(f"project: %s: done", tree_data.id)

    @staticmethod
    def _remove_uno(table1: list, len_pos: int) -> list:
        """
        Удаление статистик по унограммам если они не используются
        :param table1: Список статистик.
        :param len_pos: Длина унограмм.
        """
        ret = []
        for item in table1:
            ret.append(item[len_pos:])
        return ret

