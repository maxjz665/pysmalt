import re

from nltk.stem.snowball import SnowballStemmer

from text_app.models.tbl_dict_word import TblDictWord
from text_app.models.tbl_text import TblText
from text_app.models.tbl_word import TblWord
from prereform2modern import Processor


class ParseException(Exception):
    pass


class Parser:
    def __init__(self):
        self.foundWords = []
        self.foundInitialForms = []
        self.miss = 0
        self.hit = 0
        self.notFound = 0
        self.stemmer = SnowballStemmer("russian")



    def parse_section(self, text):
        # режем текст на предложения + знак окончания
        text = re.sub(r"^([.!?…]+)(?:\s+|$)", "", text)
        if len(text) == 0:  # если строка стала пустой, то пропускаем
            return []

        lines = re.split(r"([.!?…]+)(?:\s+|$)", text)
        lines = list(filter(None, lines))

        if not lines:
            raise ParseException(f"Can't parse section: \"{text}\"")

        words_and_marks = []

        # бежим по предложениям и пилим на слова и знаки препинания
        for i in range(0, len(lines), 2):
            cur_line = re.sub(r"[—–]+", "-", lines[i])
            cur_line = TblWord.fix_word(cur_line)  # удаляем ударения
            cur_line = re.sub(r'["»«\':;{}()*!?”“°„…_—]', ' ', cur_line)
            cur_line = re.sub(r"\.\s+", " ", cur_line)
            cur_line = re.sub(r"\.$", " ", cur_line)
            cur_line = re.sub(r"\s*[.]?[,]\s+", " ", cur_line)
            cur_line = re.sub(r"\s*,$", " ", cur_line)
            cur_line = re.sub(r"\s+-+\s+", " ", cur_line)
            cur_line = re.sub(r"\s+-$", " ", cur_line)
            cur_line = re.sub(r"^-\\s+", " ", cur_line)

            words = re.split(r"(\s+)", cur_line)
            words_and_marks.append(words)

        ret = []
        for i, words in enumerate(words_and_marks):
            if i > 0:
                ret.append('')

            for word in words:
                if re.match(r"\s+", word):
                    continue

                # if ENCODER.is_mark(word): #нужна реализация енкодера
                #   continue

                word_base = self.stemmer.stem(word.lower())
                ret.append([word, word_base])

        return ret

    def parseTextFile(self, sections):
        is_start = True
        ret = []
        for section in sections:
            if is_start:
                is_start = False
            else:
                ret.append('')
                ret.append('')
            cur = self.parse_section(section)
            if len(cur) > 0:
                ret.extend(cur)
            else:
                is_start = True  # пропускаем раздел, если он пустой

        # Вернем результат
        return ret


    def encode_in_old_type(self, value):
        ret = {}
        if not isinstance(value, list) or len(value) < 2:
            return ret

        ret["WORD"] = value[0]
        ret["INITIAL_FORM"] = value[1]

        # Убираем мягкие знаки (U+00AD)
        ret["WORD"] = re.sub(r"\u00AD", "", ret["WORD"])
        ret["INITIAL_FORM"] = re.sub(r"\u00AD", "", ret["INITIAL_FORM"])

        # Заменяем длинные тире на обычные
        ret["WORD"] = re.sub(r"–", "-", ret["WORD"])
        ret["INITIAL_FORM"] = re.sub(r"–", "-", ret["INITIAL_FORM"])

        # Убираем лишние пробелы
        ret["WORD"] = ret["WORD"].strip()
        ret["INITIAL_FORM"] = ret["INITIAL_FORM"].strip()

        # Проверка на неизвестные символы в словах
        '''if not Encoder.check_word(ret["WORD"]):          #нужна реализаци енкодера
            print(f"Неизвестные символы в {ret['WORD']}")
            exit(1)'''

        # Для кодирования, если потребуется, раскомментировать
        ret["ENCODED_WORD"] = ret["WORD"]  # Encoder.encode_word(ret["WORD"])
        ret["ENCODED_INITIAL_FORM"] = ret["INITIAL_FORM"]  # Encoder.encode_word(ret["INITIAL_FORM"])

        self.serch_in_db(ret)

        return ret

    def serch_in_db(self, ret):
        # закодировать слова
        encodedWord = ret["ENCODED_WORD"];
        encodedInitialForm = ret["ENCODED_INITIAL_FORM"];
        param1 = None
        if "PARAM_01" in ret:
            param1 = ret["PARAM_01"]

        if encodedWord in self.foundWords:
            ret["ID"] = self.foundWords[encodedWord][0]
            ret["PARAM_01"] = self.foundWords[encodedWord][1]
            self.hit += 1
            return

        self.miss += 1

        word_value = encodedWord.strip()

        # Приводим строку к нижнему и верхнему регистру
        en_lo_word = word_value.lower()
        en_hi_word = word_value.upper()

        # Костыль для разных написаний "i"
        en_i_word = self.get_other_small_i(word_value)
        en_ii_word = self.get_other_big_i(word_value)

        en_lo_i_word = self.get_other_small_i(en_lo_word)
        en_lo_ii_word = self.get_other_big_i(en_lo_word)

        en_hi_i_word = self.get_other_small_i(en_hi_word)
        en_hi_ii_word = self.get_other_big_i(en_hi_word)

        word_variants = [word_value, en_lo_word, en_hi_word, en_i_word, en_ii_word, en_lo_i_word, en_lo_ii_word,
                         en_hi_i_word, en_hi_ii_word, Parser.get_modern(word_value)]

        word_variants = list(filter(lambda x: x is not None, word_variants))


        # Поиск по полю "word"
        if param1:
            word_matches = TblDictWord.get_best_match_by_field("word", word_variants, param1)
        else:
            word_matches = TblDictWord.get_best_match_by_field("word", word_variants)

        if word_matches:
            ret["ID"] = word_matches[0]['ID']
            ret["PARAM_01"] = word_matches[0]['param_01']
            self.foundWords.append({encodedWord: [word_matches[0]['ID'], word_matches[0]['param_01']]})
            return

        # Поиск по полю "modern"
        if param1:
            modern_matches = TblDictWord.get_best_match_by_field("modern", word_variants, param1)
        else:
            modern_matches = TblDictWord.get_best_match_by_field("modern", word_variants)

        if modern_matches:
            ret["ID"] = modern_matches[0]['ID']
            ret["PARAM_01"] = modern_matches[0]['param_01']
            self.foundWords.append({encodedWord: [modern_matches[0]['ID'], modern_matches[0]['param_01']]})
            return

        # Поиск по полю "initial_form"
        if param1:
            initial_form_matches = TblDictWord.get_best_match_by_field("initial_form", word_variants, param1)
        else:
            initial_form_matches = TblDictWord.get_best_match_by_field("initial_form", word_variants)

        if initial_form_matches:
            ret["ID"] = initial_form_matches[0]['ID']
            ret["PARAM_01"] = initial_form_matches[0]['param_01']
            self.foundInitialForms.append({encodedInitialForm: [initial_form_matches[0]['ID'],
                                                                  initial_form_matches[0]['param_01']]})
            return

        self.notFound += 1

    def get_other_small_i(self, word: str) -> str | None:
        """
        Заменяет кириллическую 'і' (U+0456) на латинскую 'i' (U+0069), если она есть.
        """
        cyrillic_i = chr(0x0456)  # 'і'
        latin_i = chr(0x0069)  # 'i'

        if cyrillic_i in word:
            return word.replace(cyrillic_i, latin_i)
        return None

    def get_other_big_i(self, word: str) -> str | None:
        """
        Заменяет кириллическую 'І' (U+0406) на латинскую 'I' (U+0049), если она есть.
        """
        cyrillic_I = chr(0x0406)  # 'І'
        latin_I = chr(0x0049)  # 'I'

        if cyrillic_I in word:
            return word.replace(cyrillic_I, latin_I)
        return None

    @staticmethod       #преобразование в современное написание
    def get_modern(text):
        text_res, changes, s_json = Processor.process_text(
            text=text,
            show=False,
            delimiters=False,
            check_brackets=False
        )
        return text_res
