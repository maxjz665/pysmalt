"""
Тесты генератора деревьев решений
"""
import pytest
from django.test import TestCase

from research.r_tree_app.tree_worker_hanlder import TreeWorkerHandler


class TestTreeWorkerHandler(TestCase):
    """
    Тесты генератора деревьев решений
    """

    async def test_generate_features(self):
        """
        Проверка построения пар
        """

        pos = ["часть1", "часть2", "часть3"]

        # проверка простой генерации пар без поворотов
        items = TreeWorkerHandler._generate_features(pos, sector_size=0, many_sectors=True, is_need_uno=True, is_need_duo=True, is_need_separate=False, removed_pos=[])
        self.assertEqual(len(items), len(pos) ** 2 + len(pos))
        self.assertIn("часть1-часть2", items)

        # проверка генерации пар с одним поворотом
        items = TreeWorkerHandler._generate_features(pos, sector_size=25, many_sectors=False, is_need_uno=True, is_need_duo=True, is_need_separate=True, removed_pos=[])
        self.assertEqual(len(items), len(pos) ** 2 * 3 - len(pos)) # исходные N^2 пары + пары пар с плюсом и с минусом N(N-1)*2
        self.assertIn("часть1(0.25)-часть3(0.75)", items)
        self.assertIn("часть1(0.25)+часть3(0.75)", items)

        # проверка генерации пар с несколькими поворотами
        items = TreeWorkerHandler._generate_features(pos, sector_size=25, many_sectors=True, is_need_uno=True, is_need_duo=True, is_need_separate=True, removed_pos=[])
        self.assertEqual(len(items), len(pos) + len(pos) ** 2 + len(pos) ** 2 * (2 * 3) - len(pos) * (2 * 3)) # исходные N^2 пары + пары пар с плюсом и с минусом
        self.assertIn("часть1(0.5)-часть3(0.5)", items)
        self.assertIn("часть1(0.5)+часть3(0.5)", items)

        # проверка генерации пар с несколькими поворотами без уно и биграмм
        items = TreeWorkerHandler._generate_features(pos, sector_size=25, many_sectors=True, is_need_uno=False, is_need_duo=False, is_need_separate=True, removed_pos=[])
        self.assertEqual(len(items), len(pos) ** 2 * (2 * 3) - len(pos) * (2 * 3)) # исходные N^2 пары + пары пар с плюсом и с минусом N(N-1)*2*3
        self.assertIn("часть1(0.5)-часть3(0.5)", items)
        self.assertIn("часть1(0.5)+часть3(0.5)", items)

    async def test_generate_slice(self):
        """
        Проверка генерации данных для поворотов
        """

        table = [[1,2,3,4,5,6,7,8,9], [9,8,7,6,5,4,3,2,1]]

        # если нет поворота, то слайс не должен вызываться
        with pytest.raises(AssertionError):
            TreeWorkerHandler._generate_slice(table=table, len_pos=9, sector_size=0, many_sectors=True)

        # проверка генерации вектора с одним поворотом
        items = TreeWorkerHandler._generate_slice(table=table, len_pos=9, sector_size=25, many_sectors=False)
        self.assertEqual(len(items), len(table))
        self.assertEqual(len(items[0]), len(table[0]) ** 2 * 2 - len(table[0])) # Здесь мы должны были добавить число унограмм и вычесть 2 числа унограмм, т.к. в поворотах n(n-1)*2
        self.assertListEqual(items[0][:18], [1,2,3,4,5,6,7,8,9, 1*0.25+2*0.75, 1*0.25+3*0.75, 1*0.25+4*0.75, 1*0.25+5*0.75, 1*0.25+6*0.75, 1*0.25+7*0.75, 1*0.25+8*0.75, 1*0.25+9*0.75, 2*0.25+1*0.75])

        # проверка генерации с множеством поворотов
        items = TreeWorkerHandler._generate_slice(table=table, len_pos=9, sector_size=25, many_sectors=True)
        self.assertEqual(len(items), len(table))
        self.assertEqual(len(items[0]), len(table[0]) + len(table[0]) ** 2 * 2 * 3 - 2 * len(table[0]) * 3)
