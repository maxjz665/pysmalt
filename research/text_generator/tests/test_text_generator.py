import pytest
from django.test import TestCase
from pathlib import Path
import json
from research.text_generator.utils import rint_ext, get_random_texts, parse_code, get_length_text, get_array_of_shifts, \
    generate_text_code, check_params, generate_text_by_code, get_new_fragment_positions
from research.text_generator.dataclasses import *
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
        """Тест Б15: Проверка парсинга кода без E"""
        self.assertIsNone(parse_code("A329S1E25B330S510"))

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

    def test_array_of_shifts_in_count_zero(self):
        """Тест Б21: Проверка генерации массива сдвигов с нулевым количеством элементов"""
        shifts = get_array_of_shifts(0, 7)
        self.assertFalse(shifts)  # Пустой массив

    def test_get_texts_code_correct_1more2_2nonrep(self):
        """Тест Б22: Проверка генерации кода со вставками без повторов (1й текст > 2го)"""
        base_text = TextContent.from_tbl_text(self.texts[331])
        other_text = TextContent.from_tbl_text(self.texts[330])

        code = generate_text_code(
            base_text,
            other_text,
            fragment_size=8,
            percent_of_inserts=0.15
        )

    def test_get_texts_code_correct_1more2_2rep(self):
        """Тест Б23: Проверка генерации кода со вставками с повторами (1й текст > 2го)"""
        base_text = TextContent.from_tbl_text(self.texts[331])  # длина 236 слов
        other_text = TextContent.from_tbl_text(self.texts[330])  # длина 47 слов

        code = generate_text_code(
            base_text,
            other_text,
            fragment_size=15,
            percent_of_inserts=0.35
        )

        result = parse_code(code)
        self.assertEqual(len(result["intervals"]["A"]), 6)
        self.assertEqual(len(result["intervals"]["B"]), 6)

        for interval in result["intervals"]["A"]:
            self.assertEqual(interval["E"] - interval["S"] + 1, 15)

    def test_get_texts_code_correct_1more2_maxfrsize(self):
        """Тест Б24: Проверка генерации кода с максимальным размером фрагмента (1й текст > 2го)"""
        base_text = TextContent.from_tbl_text(self.texts[331])  # длина 236 слов
        other_text = TextContent.from_tbl_text(self.texts[330])  # длина 47 слов

        code = generate_text_code(
            base_text,
            other_text,
            fragment_size=47,
            percent_of_inserts=0.6
        )

        result = parse_code(code)
        self.assertEqual(len(result["intervals"]["A"]), 3)
        self.assertEqual(len(result["intervals"]["B"]), 3)

    def test_get_texts_code_correct_1more2_maxfrsize_maxpoins(self):
        """Тест Б25: Проверка генерации кода с макс. размером фрагмента и макс. процентом вставок"""
        base_text = TextContent.from_tbl_text(self.texts[331])  # длина 236 слов
        other_text = TextContent.from_tbl_text(self.texts[330])  # длина 47 слов

        code = generate_text_code(
            base_text,
            other_text,
            fragment_size=47,
            percent_of_inserts=0.95
        )

        result = parse_code(code)
        self.assertEqual(len(result["intervals"]["A"]), 5)
        self.assertEqual(len(result["intervals"]["B"]), 5)

    def test_get_texts_code_correct_1more2_minfrsize(self):
        """Тест Б26: Проверка генерации кода с минимальным размером фрагмента"""
        base_text = TextContent.from_tbl_text(self.texts[331])  # длина 236 слов
        other_text = TextContent.from_tbl_text(self.texts[330])  # длина 47 слов

        code = generate_text_code(
            base_text,
            other_text,
            fragment_size=5,
            percent_of_inserts=0.6
        )

        result = parse_code(code)
        self.assertEqual(len(result["intervals"]["A"]), 28)
        self.assertEqual(len(result["intervals"]["B"]), 28)

    def test_get_texts_code_correct_1more2_minfrsize_maxpoins(self):
        """Тест Б27: Проверка генерации кода с мин. размером фрагмента и макс. процентом вставок"""
        base_text = TextContent.from_tbl_text(self.texts[331])  # длина 236 слов
        other_text = TextContent.from_tbl_text(self.texts[330])  # длина 47 слов

        code = generate_text_code(
            base_text,
            other_text,
            fragment_size=5,
            percent_of_inserts=0.95
        )

        result = parse_code(code)
        self.assertEqual(len(result["intervals"]["A"]), 45)
        self.assertEqual(len(result["intervals"]["B"]), 45)

    def test_get_texts_code_correct_2more1(self):
        """Тест Б28: Проверка генерации кода когда 2й текст > 1го"""
        base_text = TextContent.from_tbl_text(self.texts[330])  # длина 47 слов
        other_text = TextContent.from_tbl_text(self.texts[331])  # длина 236 слов

        code = generate_text_code(
            base_text,
            other_text,
            fragment_size=10,
            percent_of_inserts=0.4
        )

        result = parse_code(code)
        self.assertEqual(len(result["intervals"]["A"]), 2)
        self.assertEqual(len(result["intervals"]["B"]), 2)

    def test_get_texts_code_correct_2more1_maxfrsize_maxpoins(self):
        """Тест Б29: Проверка кода с макс. фрагментом и макс. процентом (2й текст > 1го)"""
        base_text = TextContent.from_tbl_text(self.texts[330])  # длина 47 слов
        other_text = TextContent.from_tbl_text(self.texts[331])  # длина 236 слов

        code = generate_text_code(
            base_text,
            other_text,
            fragment_size=45,
            percent_of_inserts=0.95
        )

        result = parse_code(code)
        self.assertEqual(len(result["intervals"]["A"]), 1)
        self.assertEqual(len(result["intervals"]["B"]), 1)

    def test_get_texts_code_correct_2more1_minfrsize(self):
        """Тест Б30: Проверка генерации кода с мин. размером фрагмента (2й текст > 1го)"""
        base_text = TextContent.from_tbl_text(self.texts[330])  # длина 47 слов
        other_text = TextContent.from_tbl_text(self.texts[331])  # длина 236 слов

        code = generate_text_code(
            base_text,
            other_text,
            fragment_size=5,
            percent_of_inserts=0.34
        )

        result = parse_code(code)
        self.assertEqual(len(result["intervals"]["A"]), 3)
        self.assertEqual(len(result["intervals"]["B"]), 3)

    def test_get_texts_code_correct_2more1_minfrsize_maxpoins(self):
        """Тест Б31: Проверка кода с мин. фрагментом и макс. процентом вставок (2й текст > 1го)"""
        base_text = TextContent.from_tbl_text(self.texts[330])  # длина 47 слов
        other_text = TextContent.from_tbl_text(self.texts[331])  # длина 236 слов

        code = generate_text_code(
            base_text,
            other_text,
            fragment_size=5,
            percent_of_inserts=0.95
        )

        result = parse_code(code)
        self.assertEqual(len(result["intervals"]["A"]), 9)
        self.assertEqual(len(result["intervals"]["B"]), 9)

    def test_get_texts_code_correct_1more2_2nonrep_borders(self):
        """Тест Б32: Проверка генерации кода со вставками без повторов с привязкой к границам"""
        base_text = TextContent.from_tbl_text(self.texts[331])
        other_text = TextContent.from_tbl_text(self.texts[330])

        code = generate_text_code(
            base_text,
            other_text,
            fragment_size=8,
            percent_of_inserts=0.1,
            bind_borders=True
        )

        result = parse_code(code)
        self.assertEqual(len(result["intervals"]["A"]), 3)
        self.assertEqual(len(result["intervals"]["B"]), 3)

    def test_get_texts_code_correct_1more2_2rep_borders(self):
        """Тест Б33: Проверка генерации кода со вставками с повторами с привязкой к границам"""
        base_text = TextContent.from_tbl_text(self.texts[331])
        other_text = TextContent.from_tbl_text(self.texts[330])

        code = generate_text_code(
            base_text,
            other_text,
            fragment_size=15,
            percent_of_inserts=0.35,
            bind_borders=True
        )

        result = parse_code(code)
        self.assertEqual(len(result["intervals"]["A"]), 6)
        self.assertEqual(len(result["intervals"]["B"]), 6)

    def test_get_texts_code_correct_1more2_maxfrsize_borders(self):
        """Тест Б34: Проверка генерации кода с макс. размером фрагмента с привязкой к границам"""
        base_text = TextContent.from_tbl_text(self.texts[331])
        other_text = TextContent.from_tbl_text(self.texts[330])

        code = generate_text_code(
            base_text,
            other_text,
            fragment_size=47,
            percent_of_inserts=0.6,
            bind_borders=True
        )

        result = parse_code(code)
        self.assertEqual(len(result["intervals"]["A"]), 3)
        self.assertEqual(len(result["intervals"]["B"]), 3)

    def test_get_texts_code_correct_1more2_maxfrsize_maxpoins_borders(self):
        """Тест Б35: Проверка кода с макс. фрагментом и макс. процентом с границами"""
        base_text = TextContent.from_tbl_text(self.texts[331])
        other_text = TextContent.from_tbl_text(self.texts[330])

        code = generate_text_code(
            base_text,
            other_text,
            fragment_size=47,
            percent_of_inserts=0.95,
            bind_borders=True
        )

        result = parse_code(code)
        self.assertEqual(len(result["intervals"]["A"]), 5)
        self.assertEqual(len(result["intervals"]["B"]), 5)

    def test_get_texts_code_correct_1more2_minfrsize_borders(self):
        """Тест Б36: Проверка кода с мин. размером фрагмента с привязкой к границам"""
        base_text = TextContent.from_tbl_text(self.texts[331])
        other_text = TextContent.from_tbl_text(self.texts[330])

        code = generate_text_code(
            base_text,
            other_text,
            fragment_size=5,
            percent_of_inserts=0.6,
            bind_borders=True
        )

        result = parse_code(code)
        self.assertEqual(len(result["intervals"]["A"]), 22)
        self.assertEqual(len(result["intervals"]["B"]), 22)

    def test_get_texts_code_correct_1more2_minfrsize_maxpoins_borders(self):
        """Тест Б37: Проверка кода с мин. фрагментом и макс. процентом с границами"""
        base_text = TextContent.from_tbl_text(self.texts[331])
        other_text = TextContent.from_tbl_text(self.texts[330])

        code = generate_text_code(
            base_text,
            other_text,
            fragment_size=5,
            percent_of_inserts=0.95,
            bind_borders=True
        )

        result = parse_code(code)
        self.assertEqual(len(result["intervals"]["A"]), 27)
        self.assertEqual(len(result["intervals"]["B"]), 27)

    def test_get_texts_code_correct_2more1_borders(self):
        """Тест Б38: Проверка генерации кода со вторым текстом больше первого с границами"""
        base_text = TextContent.from_tbl_text(self.texts[330])
        other_text = TextContent.from_tbl_text(self.texts[331])

        code = generate_text_code(
            base_text,
            other_text,
            fragment_size=10,
            percent_of_inserts=0.4,
            bind_borders=True
        )

        result = parse_code(code)
        self.assertEqual(len(result["intervals"]["A"]), 2)
        self.assertEqual(len(result["intervals"]["B"]), 2)

    def test_get_texts_code_correct_2more1_maxfrsize_maxpoins_borders(self):
        """Тест Б39: Проверка кода с макс. фрагментом (второй > первого) с границами"""
        base_text = TextContent.from_tbl_text(self.texts[330])
        other_text = TextContent.from_tbl_text(self.texts[331])

        code = generate_text_code(
            base_text,
            other_text,
            fragment_size=45,
            percent_of_inserts=0.95,
            bind_borders=True
        )

        result = parse_code(code)
        self.assertEqual(len(result["intervals"]["A"]), 1)
        self.assertEqual(len(result["intervals"]["B"]), 1)

    def test_get_texts_code_correct_2more1_minfrsize_borders(self):
        """Тест Б40: Проверка кода с мин. фрагментом (второй > первого) с границами"""
        base_text = TextContent.from_tbl_text(self.texts[330])
        other_text = TextContent.from_tbl_text(self.texts[331])

        code = generate_text_code(
            base_text,
            other_text,
            fragment_size=5,
            percent_of_inserts=0.34,
            bind_borders=True
        )

        result = parse_code(code)
        self.assertEqual(len(result["intervals"]["A"]), 3)
        self.assertEqual(len(result["intervals"]["B"]), 3)

    def test_get_texts_code_correct_2more1_minfrsize_maxpoins_borders(self):
        """Тест Б41: Проверка кода с мин. фрагментом и макс. процентом вставок (2й текст > 1го) с границами"""
        base_text = TextContent.from_tbl_text(self.texts[330])  # длина 47 слов
        other_text = TextContent.from_tbl_text(self.texts[331])  # длина 236 слов

        code = generate_text_code(
            base_text,
            other_text,
            fragment_size=5, 
            percent_of_inserts=0.95,
            bind_borders=True
        )

        result = parse_code(code)
        self.assertEqual(len(result["intervals"]["A"]), 6)
        self.assertEqual(len(result["intervals"]["B"]), 6)

    def test_check_params_correct(self):
        """Тест Б42: Проверка корректных параметров"""
        success, _ = check_params(100, 200, 0.2, 5)
        self.assertTrue(success)

    def test_check_params_percent_less(self):
        """Тест Б43: Проверка слишком низкого процента вставок"""
        success, _ = check_params(100, 200, 0.2, 40)
        self.assertFalse(success)

    def test_check_params_fragment_size_max(self):
        """Тест Б44: Проверка максимального размера фрагмента"""
        success, _ = check_params(100, 200, 0.2, 100)
        self.assertFalse(success)
    
    def test_check_params_fragment_size_more_than_text(self):
        """Тест Б45: Проверка размера фрагмента больше размера текста"""
        success, _ = check_params(100, 200, 0.2, 300)
        self.assertFalse(success)

    def test_validate_form_correct(self):
        """Тест Б46: Проверка корректных входных данных"""
        params = GeneratorParams(
            base_textlist_id='1',
            other_textlist_id='2',
            random_texts=False,
            base_text_id='1',
            other_text_id='2',
            code_count=1,
            percent_of_inserts=0.3,
            fragment_size=20
        )
        success, _ = params.validate()
        self.assertTrue(success)

    def test_validate_form_empty_text_id(self):
        """Тест Б47: Проверка пустого ID списка текстов"""
        params = GeneratorParams(
            base_textlist_id='',  # Пустой ID базового списка
            other_textlist_id='2',
            random_texts=False,
            base_text_id='1',
            other_text_id='2',
            code_count=1,
            percent_of_inserts=0.3,
            fragment_size=20
        )
        success, _ = params.validate()
        self.assertFalse(success)

    def test_validate_form_empty_fragment_id(self):
        """Тест Б48: Проверка пустого ID выбранного текста"""
        params = GeneratorParams(
            base_textlist_id='1',
            other_textlist_id='2',
            random_texts=False,
            base_text_id='',  # Пустой ID текста
            other_text_id='2',
            code_count=1,
            percent_of_inserts=0.3,
            fragment_size=20
        )
        success, _ = params.validate()
        self.assertFalse(success)

    def test_validate_form_incorrect_code_count(self):
        """Тест Б49: Проверка некорректного количества кодов"""
        params = GeneratorParams(
            base_textlist_id='1',
            other_textlist_id='2',
            random_texts=False,
            base_text_id='1',
            other_text_id='2',
            code_count=-1,  # некорректное кол-во
            percent_of_inserts=0.3,
            fragment_size=20
        )
        success, _ = params.validate()
        self.assertFalse(success)

    def test_validate_form_incorrect_percent(self):
        """Тест Б50: Проверка некорректного процента вставок"""
        # Проверка пустого значения
        params1 = GeneratorParams(
            base_textlist_id='1',
            other_textlist_id='2',
            random_texts=False,
            base_text_id='1',
            other_text_id='2',
            code_count=1,
            percent_of_inserts=-1,  # некорректный процент
            fragment_size=20
        )
        success1, _ = params1.validate()
        self.assertFalse(success1)

        # Проверка отрицательного значения
        params1.percent_of_inserts=-0.2
        success2, _ = params1.validate()
        self.assertFalse(success2)

        # Проверка значения больше 1
        params1.percent_of_inserts=1.2
        success3, _ = params1.validate()
        self.assertFalse(success3)

    def test_validate_form_incorrect_fs(self):
        """Тест Б51: Проверка некорректного размера фрагмента"""
        params = GeneratorParams(
            base_textlist_id='1',
            other_textlist_id='2',
            random_texts=False,
            base_text_id='1',
            other_text_id='2',
            code_count=1,
            percent_of_inserts=0.2,
            fragment_size=0  # некорректный размер
        )
        success, _ = params.validate()
        self.assertFalse(success)

    def test_process_text_correct_1ins(self):
        """Тест Б52: Проверка обработки текста с одной вставкой"""
        base_text = TextContent.from_tbl_text(self.texts[329])
        intervals = {
            "A": [CodeInterval(S=5, E=10)],
            "B": [CodeInterval(S=15, E=20)]
        }

        # Генерируем текст
        result = generate_text_by_code(
            f"A{base_text.id}S5E10B{base_text.id}S15E20",
            base_text.words,
            base_text.words
        )

        # Проверяем что слова совпадают 
        words = [item.word.word for item in result if item.word.word != '|']
        for i in range(5, 11):
            self.assertEqual(words[i], words[i + 10])

    def test_process_text_correct_3ins(self):
        """Тест Б53: Проверка обработки текста с тремя вставками"""
        base_text = TextContent.from_tbl_text(self.texts[329])
        intervals = {
            "A": [
                CodeInterval(S=1, E=3),
                CodeInterval(S=7, E=9),
                CodeInterval(S=13, E=15)
            ],
            "B": [
                CodeInterval(S=4, E=6),
                CodeInterval(S=10, E=12),
                CodeInterval(S=16, E=18)
            ]
        }

        # Формируем код
        code = "".join([
            f"A{base_text.id}S{a['S']}E{a['E']}B{base_text.id}S{b['S']}E{b['E']}"
            for a, b in zip(intervals["A"], intervals["B"])
        ])


        # Генерируем текст
        result = generate_text_by_code(code, base_text.words, base_text.words)

        # Проверяем что слова совпадают
        words = [item.word.word for item in result if not item.word.word == '|']
        for interval in intervals["A"]:
            for i in range(interval["S"], interval["E"] + 1):
                self.assertEqual(words[i], words[i + 3])

    def test_process_text_correct_3ins_borders(self):
        """Тест Б54: Проверка обработки текста с тремя вставками с границами"""
        base_text = TextContent.from_tbl_text(self.texts[329])
        intervals = {
            "A": [
                CodeInterval(S=1, E=5),
                CodeInterval(S=7, E=8),
                CodeInterval(S=9, E=15)
            ],
            "B": [
                CodeInterval(S=4, E=6),
                CodeInterval(S=10, E=13),
                CodeInterval(S=16, E=20)
            ]
        }

        # Формируем код с учетом границ
        code = "".join([
            f"A{base_text.id}S{a['S']}E{a['E']}B{base_text.id}S{b['S']}E{b['E']}"
            for a, b in zip(intervals["A"], intervals["B"])
        ])

        # Генерируем текст
        result = generate_text_by_code(code, base_text.words, base_text.words)

        # Проверяем количество слов
        words = [item.word.word for item in result if not item.word.word == '|']
        self.assertEqual(len(words), 20)

    def test_get_new_position_all_less_max_sr_el(self):
        """Тест Б55: Проверка коррекции позиций с SR и EL меньше максимума"""
        base_text = TextContent.from_tbl_text(self.texts[329])
        s_lr = WordShifts(L=-2, R=3)
        e_lr = WordShifts(L=-3, R=2)

        base_text.length = 100

        # Корректируем границы
        result = get_new_fragment_positions(
            base_text,
            start_pos=10,
            end_pos=25,
            s_lr=s_lr,
            e_lr=e_lr,
            last_end_pos=5
        )
        
        self.assertEqual(14, result.start)
        self.assertEqual(22, result.end)

    def test_get_new_position_all_less_max_same_sr_el(self):
        """Тест Б56: Проверка коррекции с одинаковыми SR и EL меньше максимума"""
        base_text = TextContent.from_tbl_text(self.texts[329])
        s_lr = WordShifts(L=-2, R=2)  # Одинаковые по модулю
        e_lr = WordShifts(L=-2, R=2)

        base_text.length = 100

        # Корректируем границы
        result = get_new_fragment_positions(
            base_text,
            start_pos=10,
            end_pos=25,
            s_lr=s_lr,
            e_lr=e_lr,
            last_end_pos=5
        )
        
        self.assertEqual(13, result.start)
        self.assertEqual(23, result.end)

    def test_get_new_position_sr_el(self):
        """Тест Б57: Проверка коррекции с обычными SR и EL"""
        base_text = TextContent.from_tbl_text(self.texts[329])
        s_lr = WordShifts(L=-11, R=3)
        e_lr = WordShifts(L=-3, R=11)

        base_text.length = 100

        # Корректируем границы
        result = get_new_fragment_positions(
            base_text,
            start_pos=20,
            end_pos=35,
            s_lr=s_lr,
            e_lr=e_lr,
            last_end_pos=5
        )
        
        self.assertEqual(24, result.start)
        self.assertEqual(32, result.end)

    def test_get_new_position_all_less_max_sl_er(self):
        """Тест Б58: Проверка коррекции с SL и ER меньше максимума"""
        base_text = TextContent.from_tbl_text(self.texts[329])
        s_lr = WordShifts(L=-1, R=2)
        e_lr = WordShifts(L=-2, R=1)
        
        # Корректируем границы
        result = get_new_fragment_positions(
            base_text, 
            start_pos=10,
            end_pos=15,
            s_lr=s_lr,
            e_lr=e_lr,
            last_end_pos=5
        )
        
        self.assertEqual(9, result.start)
        self.assertEqual(17, result.end)

    def test_get_new_position_sl_er(self):
        """Тест Б59: Проверка коррекции с обычными SL и ER"""
        base_text = TextContent.from_tbl_text(self.texts[329])
        s_lr = WordShifts(L=-2, R=11)
        e_lr = WordShifts(L=-11, R=2)

        base_text.length = 100

        # Корректируем границы
        result = get_new_fragment_positions(
            base_text,
            start_pos=5,
            end_pos=30, 
            s_lr=s_lr,
            e_lr=e_lr,
            last_end_pos=1
        )
        
        self.assertEqual(3, result.start)
        self.assertEqual(33, result.end)

    def test_get_new_position_sl_er_1sentence(self):
        """Тест Б60: Проверка коррекции SL и ER для одного предложения"""
        base_text = TextContent.from_tbl_text(self.texts[329])
        s_lr = WordShifts(L=-2, R=7)
        e_lr = WordShifts(L=-7, R=2)

        # Корректируем границы
        result = get_new_fragment_positions(
            base_text,
            start_pos=10,
            end_pos=15,
            s_lr=s_lr,
            e_lr=e_lr,
            last_end_pos=5
        )
        
        self.assertEqual(8, result.start)
        self.assertEqual(18, result.end)

    def test_get_new_position_sl_el1(self):
        """Тест Б61: Проверка коррекции SL и EL случай 1"""
        base_text = TextContent.from_tbl_text(self.texts[329])
        s_lr = WordShifts(L=-2, R=11)
        e_lr = WordShifts(L=-5, R=2)

        base_text.length = 100

        # Корректируем границы
        result = get_new_fragment_positions(
            base_text,
            start_pos=10,
            end_pos=30,
            s_lr=s_lr,
            e_lr=e_lr,
            last_end_pos=5
        )

        self.assertEqual(8, result.start)
        self.assertEqual(25, result.end)

    def test_get_new_position_sl_el2(self):
        """Тест Б62: Проверка коррекции SL и EL случай 2"""
        base_text = TextContent.from_tbl_text(self.texts[329])
        s_lr = WordShifts(L=-2, R=11)
        e_lr = WordShifts(L=-5, R=11)

        base_text.length = 100

        # Корректируем границы
        result = get_new_fragment_positions(
            base_text,
            start_pos=10,
            end_pos=30,
            s_lr=s_lr,
            e_lr=e_lr,
            last_end_pos=5
        )

        self.assertEqual(8, result.start)
        self.assertEqual(25, result.end)

    def test_get_new_position_sl_el3(self):
        """Тест Б63: Проверка коррекции SL и EL случай 3"""
        base_text = TextContent.from_tbl_text(self.texts[329])
        s_lr = WordShifts(L=-2, R=5)
        e_lr = WordShifts(L=-11, R=11)

        base_text.length = 100

        # Корректируем границы
        result = get_new_fragment_positions(
            base_text,
            start_pos=10,
            end_pos=30,
            s_lr=s_lr,
            e_lr=e_lr,
            last_end_pos=5
        )

        self.assertEqual(8, result.start)
        self.assertEqual(29, result.end)

    def test_get_new_position_sl_el4(self):
        """Тест Б64: Проверка коррекции SL и EL случай 4"""
        base_text = TextContent.from_tbl_text(self.texts[329])
        s_lr = WordShifts(L=-2, R=11)
        e_lr = WordShifts(L=-11, R=11)

        base_text.length = 100

        # Корректируем границы
        result = get_new_fragment_positions(
            base_text,
            start_pos=5,
            end_pos=30,
            s_lr=s_lr,
            e_lr=e_lr,
            last_end_pos=-1
        )

        self.assertEqual(3, result.start)
        self.assertEqual(29, result.end)

    def test_get_new_position_sl_el5(self):
        """Тест Б65: Проверка коррекции SL и EL случай 5"""
        base_text = TextContent.from_tbl_text(self.texts[329])
        s_lr = WordShifts(L=-11, R=11)
        e_lr = WordShifts(L=-2, R=5)

        base_text.length = 100

        # Корректируем границы
        result = get_new_fragment_positions(
            base_text,
            start_pos=15,
            end_pos=30,
            s_lr=s_lr,
            e_lr=e_lr,
            last_end_pos=2
        )

        self.assertEqual(12, result.start)
        self.assertEqual(28, result.end)

    def test_get_new_position_sl_el6(self):
        """Тест Б66: Проверка коррекции SL и EL случай 6"""
        base_text = TextContent.from_tbl_text(self.texts[329])
        s_lr = WordShifts(L=-11, R=11)
        e_lr = WordShifts(L=-2, R=11)

        base_text.length = 100

        # Корректируем границы
        result = get_new_fragment_positions(
            base_text,
            start_pos=15,
            end_pos=30,
            s_lr=s_lr,
            e_lr=e_lr,
            last_end_pos=2
        )

        self.assertEqual(12, result.start)
        self.assertEqual(28, result.end)

    def test_get_new_position_sr_er1(self):
        """Тест Б67: Проверка коррекции SR и ER случай 1"""
        base_text = TextContent.from_tbl_text(self.texts[329])
        s_lr = WordShifts(L=-3, R=4)
        e_lr = WordShifts(L=-11, R=2)

        base_text.length = 100

        # Корректируем границы
        result = get_new_fragment_positions(
            base_text,
            start_pos=10,
            end_pos=30,
            s_lr=s_lr,
            e_lr=e_lr,
            last_end_pos=5
        )

        self.assertEqual(15, result.start)
        self.assertEqual(33, result.end)

    def test_get_new_position_sr_er2(self):
        """Тест Б68: Проверка коррекции SR и ER случай 2"""
        base_text = TextContent.from_tbl_text(self.texts[329])
        s_lr = WordShifts(L=-11, R=4)
        e_lr = WordShifts(L=-11, R=2)

        base_text.length = 100

        # Корректируем границы
        result = get_new_fragment_positions(
            base_text,
            start_pos=13,
            end_pos=30,
            s_lr=s_lr,
            e_lr=e_lr,
            last_end_pos=-1
        )

        self.assertEqual(18, result.start)
        self.assertEqual(33, result.end)

    def test_get_new_position_sr_er3(self):
        """Тест Б69: Проверка коррекции SR и ER случай 3"""
        base_text = TextContent.from_tbl_text(self.texts[329])
        s_lr = WordShifts(L=-5, R=2)
        e_lr = WordShifts(L=-11, R=11)

        base_text.length = 100

        # Корректируем границы
        result = get_new_fragment_positions(
            base_text,
            start_pos=10,
            end_pos=30,
            s_lr=s_lr,
            e_lr=e_lr,
            last_end_pos=2
        )

        self.assertEqual(13, result.start)
        self.assertEqual(34, result.end)

    def test_get_new_position_sr_er4(self):
        """Тест Б70: Проверка коррекции SR и ER случай 4"""
        base_text = TextContent.from_tbl_text(self.texts[329])
        s_lr = WordShifts(L=-12, R=2)
        e_lr = WordShifts(L=-11, R=12)

        base_text.length = 100

        # Корректируем границы
        result = get_new_fragment_positions(
            base_text,
            start_pos=13,
            end_pos=30,
            s_lr=s_lr,
            e_lr=e_lr,
            last_end_pos=1
        )

        self.assertEqual(16, result.start)
        self.assertEqual(34, result.end)

    def test_get_new_position_sr_er5(self):
        """Тест Б71: Проверка коррекции SR и ER случай 5"""
        base_text = TextContent.from_tbl_text(self.texts[329])
        s_lr = WordShifts(L=-11, R=11)
        e_lr = WordShifts(L=-2, R=1)

        base_text.length = 100

        # Корректируем границы
        result = get_new_fragment_positions(
            base_text,
            start_pos=15,
            end_pos=30,
            s_lr=s_lr,
            e_lr=e_lr,
            last_end_pos=2
        )

        self.assertEqual(16, result.start)
        self.assertEqual(32, result.end)

    def test_get_new_position_sr_er6(self):
        """Тест Б72: Проверка коррекции SR и ER случай 6"""
        base_text = TextContent.from_tbl_text(self.texts[329])
        s_lr = WordShifts(L=-12, R=11)
        e_lr = WordShifts(L=-12, R=2)

        base_text.length = 100

        # Корректируем границы
        result = get_new_fragment_positions(
            base_text,
            start_pos=15,
            end_pos=40,
            s_lr=s_lr,
            e_lr=e_lr,
            last_end_pos=5
        )

        self.assertEqual(17, result.start)
        self.assertEqual(43, result.end)

    def test_get_new_position_sr_er7_last_end(self):
        """Тест Б73: Проверка коррекции SR и ER с учетом последней позиции"""
        base_text = TextContent.from_tbl_text(self.texts[329])
        s_lr = WordShifts(L=-3, R=2)
        e_lr = WordShifts(L=-2, R=3)

        base_text.length = 100

        # Корректируем границы
        result = get_new_fragment_positions(
            base_text,
            start_pos=10,
            end_pos=15,
            s_lr=s_lr,
            e_lr=e_lr,
            last_end_pos=8
        )

        self.assertEqual(13, result.start)
        self.assertEqual(19, result.end)

    def test_get_new_position_s0_1(self):
        """Тест Б74: Проверка коррекции S0 случай 1"""
        base_text = TextContent.from_tbl_text(self.texts[329])
        s_lr = WordShifts(L=-5, R=0)
        e_lr = WordShifts(L=-5, R=5)

        base_text.length = 100

        # Корректируем границы
        result = get_new_fragment_positions(
            base_text,
            start_pos=10,
            end_pos=22,
            s_lr=s_lr,
            e_lr=e_lr,
            last_end_pos=2
        )

        self.assertEqual(11, result.start)
        self.assertEqual(17, result.end)

    def test_get_new_position_s0_2(self):
        """Тест Б75: Проверка коррекции S0 случай 2"""
        base_text = TextContent.from_tbl_text(self.texts[329])
        s_lr = WordShifts(L=-5, R=0)
        e_lr = WordShifts(L=-5, R=11)

        base_text.length = 100

        # Корректируем границы
        result = get_new_fragment_positions(
            base_text,
            start_pos=10,
            end_pos=22,
            s_lr=s_lr,
            e_lr=e_lr,
            last_end_pos=2
        )

        self.assertEqual(11, result.start)
        self.assertEqual(17, result.end)

    def test_get_new_position_s0_3(self):
        """Тест Б76: Проверка коррекции S0 случай 3"""
        base_text = TextContent.from_tbl_text(self.texts[329])
        s_lr = WordShifts(L=-12, R=0)
        e_lr = WordShifts(L=-5, R=5)

        base_text.length = 100

        # Корректируем границы
        result = get_new_fragment_positions(
            base_text,
            start_pos=18,
            end_pos=30,
            s_lr=s_lr,
            e_lr=e_lr,
            last_end_pos=2
        )

        self.assertEqual(19, result.start)
        self.assertEqual(25, result.end)

    def test_get_new_position_s0_4(self):
        """Тест Б77: Проверка коррекции S0 случай 4"""
        base_text = TextContent.from_tbl_text(self.texts[329])
        s_lr = WordShifts(L=-12, R=0)
        e_lr = WordShifts(L=-5, R=12)

        base_text.length = 100

        # Корректируем границы
        result = get_new_fragment_positions(
            base_text,
            start_pos=18,
            end_pos=30,
            s_lr=s_lr,
            e_lr=e_lr,
            last_end_pos=2
        )

        self.assertEqual(19, result.start)
        self.assertEqual(25, result.end)

    def test_get_new_position_s0_5(self):
        """Тест Б78: Проверка коррекции S0 случай 5"""
        base_text = TextContent.from_tbl_text(self.texts[329])
        s_lr = WordShifts(L=-5, R=0)
        e_lr = WordShifts(L=-5, R=5)

        base_text.length = 100

        # Корректируем границы
        result = get_new_fragment_positions(
            base_text,
            start_pos=20,
            end_pos=25,
            s_lr=s_lr,
            e_lr=e_lr,
            last_end_pos=2
        )

        self.assertEqual(21, result.start)
        self.assertEqual(31, result.end)

    def test_get_new_position_s0_6(self):
        """Тест Б79: Проверка коррекции S0 случай 6"""
        base_text = TextContent.from_tbl_text(self.texts[329])
        s_lr = WordShifts(L=-11, R=0)
        e_lr = WordShifts(L=-5, R=5)

        base_text.length = 100

        # Корректируем границы
        result = get_new_fragment_positions(
            base_text,
            start_pos=20,
            end_pos=25,
            s_lr=s_lr,
            e_lr=e_lr,
            last_end_pos=2
        )

        self.assertEqual(21, result.start)
        self.assertEqual(31, result.end)

    def test_get_new_position_s0_7(self):
        """Тест Б80: Проверка коррекции S0 случай 7"""
        base_text = TextContent.from_tbl_text(self.texts[329])
        s_lr = WordShifts(L=-5, R=0)
        e_lr = WordShifts(L=-5, R=12)

        base_text.length = 100

        # Корректируем границы
        result = get_new_fragment_positions(
            base_text,
            start_pos=20,
            end_pos=25,
            s_lr=s_lr,
            e_lr=e_lr,
            last_end_pos=2
        )

        self.assertEqual(21, result.start)
        self.assertEqual(27, result.end)

    def test_get_new_position_s0_8(self):
        """Тест Б81: Проверка коррекции S0 случай 8"""
        base_text = TextContent.from_tbl_text(self.texts[329])
        s_lr = WordShifts(L=-11, R=0)
        e_lr = WordShifts(L=-5, R=12)

        base_text.length = 100

        # Корректируем границы
        result = get_new_fragment_positions(
            base_text,
            start_pos=20,
            end_pos=25,
            s_lr=s_lr,
            e_lr=e_lr,
            last_end_pos=2
        )

        self.assertEqual(21, result.start)
        self.assertEqual(27, result.end)

    def test_get_new_position_0s_1(self):
        """Тест Б82: Проверка коррекции 0S случай 1"""
        base_text = TextContent.from_tbl_text(self.texts[329]) 
        s_lr = WordShifts(L=0, R=5)
        e_lr = WordShifts(L=-5, R=5)

        base_text.length = 100

        # Корректируем границы
        result = get_new_fragment_positions(
            base_text,
            start_pos=10,
            end_pos=25,
            s_lr=s_lr,
            e_lr=e_lr,
            last_end_pos=2
        )

        self.assertEqual(10, result.start)
        self.assertEqual(20, result.end)

    def test_get_new_position_0s_2(self):
        """Тест Б83: Проверка коррекции 0S случай 2"""
        base_text = TextContent.from_tbl_text(self.texts[329])
        s_lr = WordShifts(L=0, R=5)
        e_lr = WordShifts(L=-12, R=5)

        base_text.length = 100

        # Корректируем границы
        result = get_new_fragment_positions(
            base_text,
            start_pos=10,
            end_pos=30,
            s_lr=s_lr,
            e_lr=e_lr,
            last_end_pos=2
        )

        self.assertEqual(16, result.start)
        self.assertEqual(36, result.end)

    def test_get_new_position_0s_3(self):
        """Тест Б84: Проверка коррекции 0S случай 3"""
        base_text = TextContent.from_tbl_text(self.texts[329])
        s_lr = WordShifts(L=0, R=5)
        e_lr = WordShifts(L=-4, R=5)

        base_text.length = 100

        # Корректируем границы
        result = get_new_fragment_positions(
            base_text,
            start_pos=10,
            end_pos=20,
            s_lr=s_lr,
            e_lr=e_lr,
            last_end_pos=2
        )

        self.assertEqual(10, result.start)
        self.assertEqual(16, result.end)

    def test_get_new_position_0s_4(self):
        """Тест Б85: Проверка коррекции 0S случай 4"""
        base_text = TextContent.from_tbl_text(self.texts[329])
        s_lr = WordShifts(L=0, R=4)
        e_lr = WordShifts(L=-15, R=5)

        base_text.length = 100

        # Корректируем границы
        result = get_new_fragment_positions(
            base_text,
            start_pos=10,
            end_pos=30,
            s_lr=s_lr,
            e_lr=e_lr,
            last_end_pos=2
        )

        self.assertEqual(15, result.start)
        self.assertEqual(36, result.end)

    def test_get_new_position_0s_5(self):
        """Тест Б86: Проверка коррекции 0S случай 5"""
        base_text = TextContent.from_tbl_text(self.texts[329])
        s_lr = WordShifts(L=0, R=9)
        e_lr = WordShifts(L=-5, R=4)

        base_text.length = 100

        # Корректируем границы 
        result = get_new_fragment_positions(
            base_text,
            start_pos=10,
            end_pos=15,
            s_lr=s_lr,
            e_lr=e_lr,
            last_end_pos=2
        )

        self.assertEqual(10, result.start)
        self.assertEqual(20, result.end)

    def test_get_new_position_0s_6(self):
        """Тест Б87: Проверка коррекции 0S случай 6"""
        base_text = TextContent.from_tbl_text(self.texts[329])
        s_lr = WordShifts(L=0, R=16)
        e_lr = WordShifts(L=-5, R=11)

        base_text.length = 100

        # Корректируем границы
        result = get_new_fragment_positions(
            base_text,
            start_pos=10,
            end_pos=15,
            s_lr=s_lr,
            e_lr=e_lr,
            last_end_pos=2
        )

        self.assertEqual(10, result.start)
        self.assertEqual(16, result.end)

    def test_get_new_position_e0_1(self):
        """Тест Б88: Проверка коррекции E0 случай 1"""
        base_text = TextContent.from_tbl_text(self.texts[329])
        s_lr = WordShifts(L=-3, R=4)
        e_lr = WordShifts(L=-5, R=0)

        base_text.length = 100

        # Корректируем границы
        result = get_new_fragment_positions(
            base_text,
            start_pos=15,
            end_pos=30,
            s_lr=s_lr,
            e_lr=e_lr,
            last_end_pos=2
        )

        self.assertEqual(20, result.start)
        self.assertEqual(31, result.end)

    def test_get_new_position_e0_2(self):
        """Тест Б89: Проверка коррекции E0 случай 2"""
        base_text = TextContent.from_tbl_text(self.texts[329])
        s_lr = WordShifts(L=-11, R=4)
        e_lr = WordShifts(L=-5, R=0)

        base_text.length = 100

        # Корректируем границы
        result = get_new_fragment_positions(
            base_text,
            start_pos=15,
            end_pos=30,
            s_lr=s_lr,
            e_lr=e_lr,
            last_end_pos=2
        )

        self.assertEqual(20, result.start)
        self.assertEqual(31, result.end)

    def test_get_new_position_e0_3(self):
        """Тест Б90: Проверка коррекции E0 случай 3"""
        base_text = TextContent.from_tbl_text(self.texts[329])
        s_lr = WordShifts(L=-11, R=4)
        e_lr = WordShifts(L=-5, R=0)

        base_text.length = 100

        # Корректируем границы
        result = get_new_fragment_positions(
            base_text,
            start_pos=20,
            end_pos=30,
            s_lr=s_lr,
            e_lr=e_lr,
            last_end_pos=2
        )

        self.assertEqual(25, result.start)
        self.assertEqual(31, result.end)

    def test_get_new_position_e0_4(self):
        """Тест Б91: Проверка коррекции E0 случай 4"""
        base_text = TextContent.from_tbl_text(self.texts[329])
        s_lr = WordShifts(L=-3, R=4)
        e_lr = WordShifts(L=-5, R=0)

        base_text.length = 100

        # Корректируем границы
        result = get_new_fragment_positions(
            base_text,
            start_pos=20,
            end_pos=30,
            s_lr=s_lr,
            e_lr=e_lr,
            last_end_pos=2
        )

        self.assertEqual(25, result.start)
        self.assertEqual(31, result.end)

    def test_get_new_position_e0_5(self):
        """Тест Б92: Проверка коррекции E0 случай 5"""
        base_text = TextContent.from_tbl_text(self.texts[329])
        s_lr = WordShifts(L=-3, R=5)
        e_lr = WordShifts(L=-8, R=0)

        base_text.length = 100

        # Корректируем границы
        result = get_new_fragment_positions(
            base_text,
            start_pos=25,
            end_pos=30,
            s_lr=s_lr,
            e_lr=e_lr,
            last_end_pos=2
        )

        self.assertEqual(22, result.start)
        self.assertEqual(31, result.end)

    def test_get_new_position_e0_6(self):
        """Тест Б93: Проверка коррекции E0 случай 6"""
        base_text = TextContent.from_tbl_text(self.texts[329])
        s_lr = WordShifts(L=-11, R=4)
        e_lr = WordShifts(L=-15, R=0)

        base_text.length = 100

        # Корректируем границы
        result = get_new_fragment_positions(
            base_text,
            start_pos=26,
            end_pos=30,
            s_lr=s_lr,
            e_lr=e_lr,
            last_end_pos=2
        )

        self.assertEqual(26, result.start)
        self.assertEqual(31, result.end)

    def test_get_new_position_0e_1(self):
        """Тест Б94: Проверка коррекции 0E случай 1"""
        base_text = TextContent.from_tbl_text(self.texts[329])
        s_lr = WordShifts(L=-5, R=4)
        e_lr = WordShifts(L=0, R=5)

        base_text.length = 100

        # Корректируем границы
        result = get_new_fragment_positions(
            base_text,
            start_pos=10,
            end_pos=30,
            s_lr=s_lr,
            e_lr=e_lr,
            last_end_pos=2
        )

        self.assertEqual(15, result.start)
        self.assertEqual(30, result.end)

    def test_get_new_position_0e_2(self):
        """Тест Б95: Проверка коррекции 0E случай 2""" 
        base_text = TextContent.from_tbl_text(self.texts[329])
        s_lr = WordShifts(L=-12, R=3)
        e_lr = WordShifts(L=0, R=8)

        base_text.length = 100

        # Корректируем границы
        result = get_new_fragment_positions(
            base_text,
            start_pos=20,
            end_pos=30,
            s_lr=s_lr,
            e_lr=e_lr,
            last_end_pos=2
        )

        self.assertEqual(24, result.start)
        self.assertEqual(30, result.end)

    def test_get_new_position_0e_3(self):
        """Тест Б96: Проверка коррекции 0E случай 3"""
        base_text = TextContent.from_tbl_text(self.texts[329])
        s_lr = WordShifts(L=-5, R=3)
        e_lr = WordShifts(L=0, R=12)

        base_text.length = 100

        # Корректируем границы
        result = get_new_fragment_positions(
            base_text,
            start_pos=20,
            end_pos=30,
            s_lr=s_lr,
            e_lr=e_lr,
            last_end_pos=2
        )

        self.assertEqual(24, result.start)
        self.assertEqual(30, result.end)

    def test_get_new_position_0e_4(self):
        """Тест Б97: Проверка коррекции 0E случай 4"""
        base_text = TextContent.from_tbl_text(self.texts[329])
        s_lr = WordShifts(L=-12, R=3)
        e_lr = WordShifts(L=0, R=12)

        base_text.length = 100

        # Корректируем границы
        result = get_new_fragment_positions(
            base_text,
            start_pos=20,
            end_pos=30,
            s_lr=s_lr,
            e_lr=e_lr,
            last_end_pos=2
        )

        self.assertEqual(24, result.start)
        self.assertEqual(30, result.end)

    def test_get_new_position_0e_5(self):
        """Тест Б98: Проверка коррекции 0E случай 5"""
        base_text = TextContent.from_tbl_text(self.texts[329])
        s_lr = WordShifts(L=-2, R=4)
        e_lr = WordShifts(L=0, R=7)

        base_text.length = 100

        # Корректируем границы
        result = get_new_fragment_positions(
            base_text,
            start_pos=15,
            end_pos=20,
            s_lr=s_lr,
            e_lr=e_lr,
            last_end_pos=2
        )

        self.assertEqual(13, result.start)
        self.assertEqual(20, result.end)

    def test_get_new_position_0e_6(self):
        """Тест Б99: Проверка коррекции 0E случай 6"""
        base_text = TextContent.from_tbl_text(self.texts[329])
        s_lr = WordShifts(L=-11, R=4)
        e_lr = WordShifts(L=0, R=6)

        base_text.length = 100

        # Корректируем границы
        result = get_new_fragment_positions(
            base_text,
            start_pos=15,
            end_pos=20,
            s_lr=s_lr,
            e_lr=e_lr,
            last_end_pos=2
        )

        self.assertEqual(20, result.start)
        self.assertEqual(27, result.end)

    def test_get_new_position_0s_e0(self):
        """Тест Б100: Проверка коррекции 0S и E0"""
        base_text = TextContent.from_tbl_text(self.texts[329])
        s_lr = WordShifts(L=0, R=4)
        e_lr = WordShifts(L=-4, R=0)

        base_text.length = 100

        # Корректируем границы
        result = get_new_fragment_positions(
            base_text,
            start_pos=11,
            end_pos=20,
            s_lr=s_lr,
            e_lr=e_lr,
            last_end_pos=2
        )

        self.assertEqual(11, result.start)
        self.assertEqual(21, result.end)

    def test_get_new_position_s0_e0(self):
        """Тест Б101: Проверка коррекции S0 и E0"""
        base_text = TextContent.from_tbl_text(self.texts[329])
        s_lr = WordShifts(L=-5, R=0)
        e_lr = WordShifts(L=-5, R=0)

        base_text.length = 100

        # Корректируем границы
        result = get_new_fragment_positions(
            base_text,
            start_pos=10,
            end_pos=20,
            s_lr=s_lr,
            e_lr=e_lr,
            last_end_pos=2
        )

        self.assertEqual(11, result.start)
        self.assertEqual(21, result.end)

    def test_get_new_position_0s_0e(self):
        """Тест Б102: Проверка коррекции 0S и 0E"""
        base_text = TextContent.from_tbl_text(self.texts[329])
        s_lr = WordShifts(L=0, R=5)
        e_lr = WordShifts(L=0, R=5)

        base_text.length = 100

        # Корректируем границы
        result = get_new_fragment_positions(
            base_text,
            start_pos=10,
            end_pos=20,
            s_lr=s_lr,
            e_lr=e_lr,
            last_end_pos=2
        )

        self.assertEqual(10, result.start)
        self.assertEqual(20, result.end)

    def test_get_new_position_s0_0e(self):
        """Тест Б103: Проверка коррекции S0 и 0E"""
        base_text = TextContent.from_tbl_text(self.texts[329])
        s_lr = WordShifts(L=-3, R=0)
        e_lr = WordShifts(L=0, R=5)

        base_text.length = 100

        # Корректируем границы
        result = get_new_fragment_positions(
            base_text,
            start_pos=10,
            end_pos=20,
            s_lr=s_lr,
            e_lr=e_lr,
            last_end_pos=2
        )

        self.assertEqual(11, result.start)
        self.assertEqual(20, result.end)
