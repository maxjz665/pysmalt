from dataclasses import dataclass
from typing import List, TypedDict, Dict


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