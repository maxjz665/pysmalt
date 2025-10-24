"""
Тесты генератора деревьев решений
"""
from django.test import TestCase

from research.r_tree_app.models.tbl_tree_description import TblTreeDescription
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
        items = TreeWorkerHandler._generate_features(pos, sector_size=0, many_sectors=True)
        self.assertEqual(len(items), len(pos) ** 2)
        self.assertIn("часть1-часть2", items)

        # проверка генерации пар с одним поворотом
        items = TreeWorkerHandler._generate_features(pos, sector_size=25, many_sectors=False)
        self.assertEqual(len(items), len(pos) ** 4 * 2 + len(pos) ** 2) # исходные N^2 пары + пары пар с плюсом и с минусом
        self.assertIn("часть1-часть2(0.25) - часть1-часть3(0.75)", items)
        self.assertIn("часть1-часть2(0.25) + часть1-часть3(0.75)", items)

        # проверка генерации пар с несколькими поворотами
        items = TreeWorkerHandler._generate_features(pos, sector_size=25, many_sectors=True)
        self.assertEqual(len(items), len(pos) ** 4 * 2 * 3 + len(pos) ** 2) # исходные N^2 пары + пары пар с плюсом и с минусом
        self.assertIn("часть1-часть2(0.5) - часть1-часть3(0.5)", items)
        self.assertIn("часть1-часть2(0.5) + часть1-часть3(0.5)", items)
