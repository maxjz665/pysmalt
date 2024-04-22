from django.test import TestCase

from research.r_tree_app.models.tbl_tree_description import TblTreeDescription
from research.r_tree_app.views import _generate_table
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
        item = TblTextListDescription.objects.get(id=1)

        table1 = _generate_table(item, 200)
        self.assertTrue(len(table1) > 0)
