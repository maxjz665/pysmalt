from django.test import TestCase

from research.r_tree_app.tree_worker_hanlder import TreeWorkerHandler
from text_app.models.tbl_textlist import TblTextListDescription


class StatDataGeneratorTest(TestCase):
    """
    Проверка генерации таблицы текстов на базе списков
    """

    def setUp(self):
        TblTextListDescription.objects.create(id=1, name="test tree")

    def test_generate_table(self):
        """
        Проверка пробега по списку текстов и генерации таблицы
        """
        # TODO: загрузка данных в БД перед тестом
        # item = TblTextListDescription.objects.get(id=1)
        #
        # table1 = TreeWorkerHandler._generate_table(item, 200, 23)
        # self.assertTrue(len(table1) > 0)
