from dataclasses import dataclass
from typing import List, TypedDict, Dict, Optional, Tuple

from text_app.models.tbl_text import TblText

@dataclass
class WordParams:
    """Параметры слова из словаря"""
    param_01: int
    param_02: int
    param_03: int
    param_04: int
    param_05: int
    param_06: int
    param_07: int
    param_08: int
    param_09: int
    param_10: int
    param_11: int
    param_12: int
    param_13: int
    param_14: int
    param_15: int
    param_16: int
    param_17: int
    param_18: int
    param_19: int
    param_20: int
    
    @classmethod
    def from_dict_word(cls, dict_word) -> 'WordParams':
        """Создает WordParams из объекта DictWord"""
        return cls(**{f'param_{i:02d}': getattr(dict_word, f'param_{i:02d}') for i in range(1, 21)})

@dataclass
class TextWord:
    """Класс для представления слова в тексте"""
    def __init__(self, word: str, paragraph_index: Optional[int] = None, sentence_index: Optional[int] = None,
                 word_index: Optional[int] = None, chapter_index: Optional[int] = None, params: Optional[WordParams] = None):
        self.word = word
        self.paragraph_index = paragraph_index
        self.sentence_index = sentence_index
        self.word_index = word_index
        self.chapter_index = chapter_index
        self.params = params
        
    def __str__(self):
        return self.word

    def __repr__(self):
        return self.word

    word: str
    paragraph_index: int
    sentence_index: int
    word_index: int
    chapter_index: int
    params: WordParams

@dataclass
class TextContent:
    """Класс для представления текста"""
    id: int
    words: List[TextWord]
    length: int

    @classmethod
    def from_tbl_text(cls, text: TblText) -> 'TextContent':
        """Создает TextContent из объекта TblText"""
        words = []
        for word in text.get_content():
            params = WordParams.from_dict_word(word.dictword) if hasattr(word, 'dictword') and word.dictword else None
            words.append(TextWord(
                word=word.word,
                paragraph_index=word.paragraph_index,
                sentence_index=word.sentence_index,
                word_index=word.word_index,
                chapter_index=word.chapter_index,
                params=params
            ))
        
        return cls(
            id=text.id,
            words=words,
            length=len(words)
        )

@dataclass
class CodeInterval(TypedDict):
    """Тип для интервалов в коде"""
    S: int  # Start position
    E: int  # End position

@dataclass
class ParsedCode(TypedDict):
    """Тип для разобранного кода"""
    id1: int
    id2: int
    intervals: Dict[str, List[CodeInterval]]

@dataclass
class GeneratorParams:
    """Параметры генерации текста"""
    base_textlist_id: str  # ID списка базовых текстов
    other_textlist_id: str  # ID списка вставляемых текстов
    random_texts: bool = True  # Использовать случайные тексты
    base_text_id: Optional[str] = None  # ID базового текста
    other_text_id: Optional[str] = None  # ID вставляемого текста
    code_count: int = 1  # Количество генерируемых кодов
    percent_of_inserts: float = 0.2  # Доля вставок (0.01-0.95)
    fragment_size: int = 10  # Размер фрагмента (≥5)
    bind_borders: bool = False  # Привязка к границам предложений

    def validate(self) -> Tuple[bool, str]:
        """
        Проверяет корректность параметров.
        
        Returns:
            tuple[bool, str]: (успех проверки, сообщение об ошибке)
        """

        # Проверяем указан ли список базовых текстов
        if not self.base_textlist_id:
            return False, "Необходимо выбрать список основных текстов"

        # Проверяем указан ли список вставляемых текстов    
        if not self.other_textlist_id:
            return False, "Необходимо выбрать список вставляемых текстов"

        # Если не случайные тексты, проверяем указаны ли они
        if not self.random_texts:
            if not self.base_text_id:
                return False, "Необходимо выбрать основной текст"
            if not self.other_text_id:
                return False, "Необходимо выбрать вставляемый текст"

        # Проверяем число кодов
        if not 1 <= self.code_count <= 20:
            return False, "Количество кодов должно быть между 1 и 20"
            
        # Проверяем процент вставок
        if not (0.01 <= self.percent_of_inserts <= 0.95):
            return False, "Укажите долю вставок в диапазоне 0.01 - 0.95"

        # Проверяем размер фрагмента
        if self.fragment_size < 5:
            return False, "Минимальный размер заменяемого фрагмента 5"

        return True, ""

@dataclass
class WordShifts:
    """Сдвиги для слова влево и вправо"""
    L: int  # Сдвиг влево
    R: int  # Сдвиг вправо

@dataclass
class FragmentPosition:
    """Позиция фрагмента в тексте"""
    start: int
    end: int

@dataclass
class CodeGen(str):
    """Класс для генерации кода"""
    pass

@dataclass
class GeneratedWord:
    """Слово в сгенерированном тексте"""
    word: TextWord
    start_paragraph: bool
    highlight: bool
    start_sentence: bool = False

    def __str__(self):
        return self.word.word

    def __repr__(self):
        return self.word.word
