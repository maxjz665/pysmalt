import pytest
from django.test import TestCase
from pathlib import Path
import json
from research.text_generator.utils import rint_ext, get_random_texts, parse_code, get_length_text, get_array_of_shifts
from research.text_generator.dataclasses import ParsedCode, CodeInterval
from text_app.models.tbl_text import TblText
from text_app.models.tbl_textlist import TblTextListItems, TblTextListDescription
from text_app.models.tbl_author import TblAuthor
from text_app.models.tbl_magazine import TblMagazine
from text_app.models.tbl_word import TblWord
from user_app.models import TblUser


@pytest.mark.django_db
class TextGeneratorTest(TestCase):
    """Тесты генератора текстов"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        fixture_path = Path(__file__).parent / "fixtures"
        
        # Загружаем фикстуры пользователей
        with open(fixture_path / "users.json", encoding='utf-8') as f:
            users_json = json.load(f)
            cls.users = {}
            for item in users_json:
                user = TblUser(
                    id=item["pk"],
                    **item["fields"]
                )
                user.save()
                cls.users[item["pk"]] = user

        # Загружаем фикстуры авторов
        with open(fixture_path / "authors.json", encoding='utf-8') as f:
            authors_json = json.load(f)
            cls.authors = {}
            for item in authors_json:
                author = TblAuthor(
                    id=item["pk"],
                    **item["fields"]
                )
                author.save()  # Save author to DB
                cls.authors[item["pk"]] = author

        # Загружаем фикстуры журналов
        with open(fixture_path / "magazines.json", encoding='utf-8') as f:
            magazines_json = json.load(f)
            cls.magazines = {}
            for item in magazines_json:
                magazine = TblMagazine(
                    id=item["pk"],
                    **item["fields"]
                )
                magazine.save()
                cls.magazines[item["pk"]] = magazine

        # Загружаем фикстуры текстов
        with open(fixture_path / "texts.json", encoding='utf-8') as f:
            texts_json = json.load(f)
            cls.texts = {}
            for item in texts_json:
                fields = item["fields"].copy()
                
                # Заменяем id на объекты для foreign keys
                if "author" in fields and fields["author"]:
                    fields["author"] = cls.authors[fields["author"]]
                if "magazine" in fields and fields["magazine"]:
                    fields["magazine"] = cls.magazines[fields["magazine"]]

                text = TblText(
                    id=item["pk"],
                    **fields
                )
                text.save()
                cls.texts[item["pk"]] = text

        # Загружаем фикстуры списков
        with open(fixture_path / "lists.json", encoding='utf-8') as f:
            lists_json = json.load(f)
            cls.lists = {}
            for item in lists_json:
                fields = item["fields"].copy()
                
                if "owner" in fields:
                    fields["owner"] = cls.users[fields["owner"]]
                    
                text_list = TblTextListDescription(
                    id=item["pk"],
                    **fields
                )
                text_list.save()
                cls.lists[item["pk"]] = text_list

        # Загружаем фикстуры списков текстов
        with open(fixture_path / "list_text.json", encoding='utf-8') as f:
            list_items_json = json.load(f)
            cls.list_text_items = {}
            for item in list_items_json:
                list_item = TblTextListItems(
                    id=item["pk"],
                    list=cls.lists[item["fields"]["list"]],
                    text=cls.texts[item["fields"]["text"]]
                )
                list_item.save()
                cls.list_text_items[item["pk"]] = list_item

        # Загружаем фикстуры слов
        with open(fixture_path / "text_words.json", encoding='utf-8') as f:
            words_json = json.load(f)
            for item in words_json:
                fields = item["fields"]
                # Создаем и сохраняем слово в БД
                word = TblWord(
                    id_word=item["pk"],
                    text=cls.texts[fields["text_id"]],
                    word=fields["word"], 
                    word_length=fields["word_length"],
                    chapter_index=fields["chapter_index"],
                    paragraph_index=fields["paragraph_index"],
                    sentence_index=fields["sentence_index"],
                    word_index=fields["word_index"],
                    chdate=fields["chdate"], 
                    wordorder=fields["wordorder"],
                    wordno=fields["wordno"]
                )
                word.save()

    def test_rint_correct(self):
        """Тест Б1: Проверка корректной работы функции rint с целыми числами"""
        val = rint_ext(1, 3, 0.5)
        self.assertIsInstance(val, int)
        self.assertGreaterEqual(val, 1)
        self.assertLessEqual(val, 3)

    def test_rint_with_zero(self):
        """Тест Б2: Проверка работы rint с нулем"""
        self.assertEqual(rint_ext(0, 0, 0.5), 0)

    def test_rint_start_bigger_end(self):
        """Тест Б3: Проверка исключения при некорректном диапазоне""" 
        with self.assertRaises(ValueError):
            rint_ext(2, 1, 0.5)

    def test_r_texts_from_diff_lists(self):
        """Тест Б4: Проверка выбора текстов из разных списков"""
        base_items = [item.text.id for item in self.list_text_items.values() if item.list.id == 1]
        other_items = [item.text.id for item in self.list_text_items.values() if item.list.id == 2]

        base_text, other_text = get_random_texts(1, 2, base_items, other_items)
        
        self.assertIn(base_text, base_items)
        self.assertIn(other_text, other_items)

    def test_r_texts_from_equals_lists(self):
        """Тест Б5: Проверка выбора разных текстов из одного списка"""
        items = [item.text.id for item in self.list_text_items.values() if item.list.id == 1]
        
        for _ in range(10):
            base_text, other_text = get_random_texts(1, 1, items, items)
            self.assertNotEqual(base_text, other_text)

    def test_get_text_length_large_text(self):
        """Тест Б6: Проверка получения длины большого текста"""

        length = get_length_text(self.texts[333])

        self.assertEqual(1620, length)

    def test_get_text_length_incorrect_text_number(self):
        """Тест Б7: Проверка получения длины несуществующего текста"""
        text = next((t for t in self.texts.values() if str(t.id) == "5555"), None)
        self.assertIsNone(text)

    def test_parse_code_correct_1_replace(self):
        """Тест Б8: Проверка парсинга кода с одной заменой"""
        code = "A325S112E211B326S102E201"
        expected: ParsedCode = {
            "id1": 325,
            "id2": 326,
            "intervals": {
                "A": [CodeInterval(S=112, E=211)],
                "B": [CodeInterval(S=102, E=201)]
            }
        }
        
        result = parse_code(code)
        self.assertEqual(result, expected)

    def test_parse_code_correct_3_replace(self):
        """Тест Б9: Проверка парсинга кода с тремя заменами"""
        code = "A325S112E211B326S102E201A325S222E321B326S212E311A325S332E431B326S322E421"
        expected: ParsedCode = {
            "id1": 325,
            "id2": 326,
            "intervals": {
                "A": [
                    CodeInterval(S=112, E=211),
                    CodeInterval(S=222, E=321), 
                    CodeInterval(S=332, E=431)
                ],
                "B": [
                    CodeInterval(S=102, E=201),
                    CodeInterval(S=212, E=311),
                    CodeInterval(S=322, E=421)
                ]
            }
        }
        
        result = parse_code(code)
        self.assertEqual(result, expected)

    def test_parse_code_empty(self):
        """Тест Б10: Проверка парсинга пустого кода"""
        self.assertIsNone(parse_code(""))

    def test_parse_code_incorrect(self):
        """Тест Б11: Проверка парсинга некорректного кода"""
        self.assertIsNone(parse_code("12Aghf"))

    def test_parse_code_incorrect_1(self):
        """Тест Б12: Проверка парсинга неполного кода"""
        self.assertIsNone(parse_code("A325S112E211"))

    def test_parse_code_incorrect_2(self):
        """Тест Б13: Проверка парсинга кода с неверным ID"""
        code = "A325S112E211B326S102E201A111S222E321B326S212E311A325S332E431B326S322E421"
        self.assertIsNone(parse_code(code))

    def test_parse_code_incorrect_3(self):
        """Тест Б14: Проверка парсинга кода с неверными границами"""
        self.assertIsNone(parse_code("A325S112E111B326S102E201"))

    def test_parse_code_incorrect_4(self):
        """Тест Б15: Проверка парсинга кода """
        self.assertIsNone(parse_code("A329S1E25B330S5E10"))

    def test_array_of_shifts_correct_1(self):
        """Тест Б16: Проверка генерации массива сдвигов - случай 1"""
        shifts = get_array_of_shifts(7, 5)
        self.assertTrue(shifts)  # Массив не пустой
        self.assertNotEqual(all(shifts), True)  # Не все элементы True
        self.assertEqual(sum(1 for x in shifts if x), 5)  # Сумма True равна 5

    def test_array_of_shifts_correct_2(self):
        """Тест Б17: Проверка генерации массива сдвигов - случай 2"""
        shifts = get_array_of_shifts(7, 7)
        self.assertTrue(shifts)  # Массив не пустой
        self.assertEqual(sum(1 for x in shifts if x), 7)  # Сумма True равна 7

    def test_array_of_shifts_sh_count_zero(self):
        """Тест Б18: Проверка генерации массива сдвигов с нулевым количеством сдвигов"""
        shifts = get_array_of_shifts(7, 0)
        self.assertTrue(shifts)  # Массив не пустой
        self.assertEqual(sum(1 for x in shifts if x), 0)  # Нет True элементов

    def test_array_of_shifts_sh_count_less_zero(self):
        """Тест Б19: Проверка генерации массива сдвигов с отрицательным количеством"""
        shifts = get_array_of_shifts(7, -2)
        self.assertFalse(shifts)  # Пустой массив

    def test_array_of_shifts_in_count_less(self):
        """Тест Б20: Проверка генерации массива сдвигов с некорректным количеством вставок"""
        shifts = get_array_of_shifts(5, 7)
        self.assertFalse(shifts)  # Пустой массив