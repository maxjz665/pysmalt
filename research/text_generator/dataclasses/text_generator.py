from dataclasses import dataclass
from typing import List, TypedDict, Dict

from text_app.models.tbl_text import TblText


@dataclass
class TextWord:
    """Класс для представления слова в тексте"""
    word: str
    paragraph_index: int
    sentence_index: int
    word_index: int

@dataclass
class TextContent:
    """Класс для представления текста"""
    id: int
    words: List[TextWord]
    length: int

    @classmethod
    def from_tbl_text(cls, text: TblText) -> 'TextContent':
        """Создает TextContent из объекта TblText"""
        words = [
            TextWord(
                word=w.word,
                paragraph_index=w.paragraph_index,
                sentence_index=w.sentence_index,
                word_index=w.word_index
            ) for w in text.get_content()
        ]
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