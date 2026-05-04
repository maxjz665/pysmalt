"""
Модуль импорта и токенизации текстов.
Обеспечивает загрузку текстов из различных форматов (TXT, PDF, HTML),
их токенизацию с помощью библиотеки Natasha и сохранение
структурированных данных в базе SMALT.
"""
import logging
import re
from typing import List, Tuple, Optional

from django.utils import timezone
from natasha import Segmenter, MorphVocab, NewsEmbedding, NewsMorphTagger, NewsSyntaxParser, Doc

from text_app.models.tbl_text import TblText
from text_app.models.tbl_word import TblWord
from text_app.models.tbl_dict_word import TblDictWord
from research.authorship.models import TblSign

logger = logging.getLogger(__name__)

# Инициализация компонентов Natasha (синглтон)
_segmenter = None
_morph_vocab = None
_emb = None
_morph_tagger = None
_syntax_parser = None


def _init_natasha():
    """Ленивая инициализация компонентов Natasha."""
    global _segmenter, _morph_vocab, _emb, _morph_tagger, _syntax_parser
    if _segmenter is None:
        _segmenter = Segmenter()
        _morph_vocab = MorphVocab()
        _emb = NewsEmbedding()
        _morph_tagger = NewsMorphTagger(_emb)
        _syntax_parser = NewsSyntaxParser(_emb)


def get_natasha_doc(text: str) -> Doc:
    """
    Создаёт объект Natasha Doc с полным синтаксическим разбором.

    Args:
        text: исходный текст

    Returns:
        Doc: размеченный документ Natasha
    """
    _init_natasha()
    doc = Doc(text)
    doc.segment(_segmenter)
    doc.tag_morph(_morph_tagger)
    doc.parse_syntax(_syntax_parser)
    for token in doc.tokens:
        token.lemmatize(_morph_vocab)
    return doc


# ────────────────────────────────────────────────────────────
#  Извлечение текста из разных форматов
# ────────────────────────────────────────────────────────────

def extract_text_from_txt(file_path: str) -> str:
    """Чтение TXT-файла с определением кодировки."""
    encodings = ['utf-8', 'cp1251', 'latin-1']
    for enc in encodings:
        try:
            with open(file_path, 'r', encoding=enc) as f:
                return f.read()
        except (UnicodeDecodeError, UnicodeError):
            continue
    raise ValueError(f"Не удалось определить кодировку файла {file_path}")


def extract_text_from_pdf(file_path: str) -> str:
    """Извлечение текста из PDF через PyPDF2."""
    try:
        from PyPDF2 import PdfReader
    except ImportError:
        raise ImportError("Установите PyPDF2: pip install PyPDF2")
    reader = PdfReader(file_path)
    pages = [page.extract_text() or '' for page in reader.pages]
    return '\n'.join(pages)


def extract_text_from_html(file_path: str) -> str:
    """Извлечение текста из HTML через BeautifulSoup."""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        raise ImportError("Установите beautifulsoup4: pip install beautifulsoup4")
    with open(file_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f.read(), 'html.parser')
    for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
        tag.decompose()
    return soup.get_text(separator='\n')


def extract_text(file_path: str) -> str:
    """
    Универсальный экстрактор текста.
    Определяет формат по расширению файла.
    """
    ext = file_path.rsplit('.', 1)[-1].lower()
    extractors = {
        'txt': extract_text_from_txt,
        'pdf': extract_text_from_pdf,
        'html': extract_text_from_html,
        'htm': extract_text_from_html,
    }
    extractor = extractors.get(ext)
    if not extractor:
        raise ValueError(f"Неподдерживаемый формат файла: .{ext}")
    return extractor(file_path)


def normalize_text(text: str) -> str:
    """
    Нормализация текста: удаление лишних пробелов,
    унификация переносов строк.
    """
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


# ────────────────────────────────────────────────────────────
#  Разделение токенов на слова и знаки препинания
# ────────────────────────────────────────────────────────────

_PUNCT_RE = re.compile(r'^[^\w]+$', re.UNICODE)


def is_punctuation(token_text: str) -> bool:
    """Определяет, является ли токен знаком препинания."""
    return bool(_PUNCT_RE.match(token_text))


def split_into_paragraphs(text: str) -> List[str]:
    """Разбивает текст на параграфы по двойным переносам строк."""
    paragraphs = re.split(r'\n\s*\n', text)
    return [p.strip() for p in paragraphs if p.strip()]


# ────────────────────────────────────────────────────────────
#  Импорт текста в SMALT
# ────────────────────────────────────────────────────────────

def import_text_to_db(text_obj: TblText, raw_text: str) -> dict:
    """
    Токенизирует текст и сохраняет слова и знаки препинания
    в базу данных SMALT.

    Args:
        text_obj: объект TblText, к которому привязываются слова
        raw_text: исходный текст

    Returns:
        dict: статистика импорта (words_count, signs_count, sentences_count)
    """
    from django.db import transaction

    normalized = normalize_text(raw_text)
    paragraphs = split_into_paragraphs(normalized)

    words_count = 0
    signs_count = 0
    sentences_count = 0
    chapter_index = 1

    with transaction.atomic():
        # Удаляем старые данные, если есть
        TblWord.objects.filter(text=text_obj).delete()
        TblSign.objects.filter(text=text_obj).delete()

        for para_idx, paragraph in enumerate(paragraphs, start=1):
            doc = get_natasha_doc(paragraph)

            for sent in doc.sents:
                sentences_count += 1
                word_index = 0
                last_word_obj = None
                sign_position = 0

                for token in sent.tokens:
                    token_text = token.text

                    if is_punctuation(token_text):
                        # Сохраняем знак препинания
                        placement = 'before' if last_word_obj is None else 'after'
                        sign = TblSign(
                            text=text_obj,
                            word=last_word_obj,
                            chapter_index=chapter_index,
                            paragraph_index=para_idx,
                            sentence_index=sentences_count,
                            position_index=sign_position,
                            sign_value=token_text,
                            placement=placement,
                        )
                        sign.save()
                        signs_count += 1
                        sign_position += 1
                    else:
                        # Сохраняем слово
                        word_index += 1

                        # Ищем или создаём запись в словаре
                        lemma = (getattr(token, 'lemma', None) or token_text).lower()
                        entry, _ = TblDictWord.objects.get_or_create(
                            word=token_text,
                            initial_form=lemma,
                            modern=lemma,
                            defaults={'param_01': 0},
                        )

                        word_obj = TblWord(
                            text=text_obj,
                            word_length=len(token_text),
                            chapter_index=chapter_index,
                            paragraph_index=para_idx,
                            sentence_index=sentences_count,
                            word_index=word_index,
                            chdate=timezone.now(),
                            word=token_text,
                            dictword=entry,
                            wordorder=0,
                            wordno=0,
                        )
                        word_obj.save()
                        last_word_obj = word_obj
                        words_count += 1
                        sign_position = 0  # сброс счётчика знаков

    return {
        'words_count': words_count,
        'signs_count': signs_count,
        'sentences_count': sentences_count,
        'paragraphs_count': len(paragraphs),
    }


# ────────────────────────────────────────────────────────────
#  Восстановление текста из БД
# ────────────────────────────────────────────────────────────

def reconstruct_text(text_obj: TblText) -> str:
    """
    Восстанавливает исходный текст из таблиц word и signs.

    Args:
        text_obj: объект TblText

    Returns:
        str: восстановленный текст
    """
    words = list(
        TblWord.objects.filter(text=text_obj)
        .order_by('chapter_index', 'paragraph_index',
                  'sentence_index', 'word_index')
    )
    signs = list(
        TblSign.objects.filter(text=text_obj)
        .order_by('chapter_index', 'paragraph_index',
                  'sentence_index', 'position_index')
    )

    # Индексируем знаки по word_id
    signs_before_first = []  # знаки перед первым словом предложения
    signs_after_word = {}    # word_id -> [signs]
    for s in signs:
        if s.word_id is None:
            signs_before_first.append(s)
        else:
            signs_after_word.setdefault(s.word_id, []).append(s)

    result_parts = []
    prev_para = None
    prev_sent = None

    # Знаки перед первым словом
    for s in signs_before_first:
        result_parts.append(s.sign_value)

    for w in words:
        # Новый параграф
        if prev_para is not None and w.paragraph_index != prev_para:
            result_parts.append('\n\n')
        elif prev_sent is not None and w.sentence_index != prev_sent:
            result_parts.append(' ')

        if result_parts and not result_parts[-1].endswith('\n'):
            if prev_para is not None:
                result_parts.append(' ')

        result_parts.append(w.word)

        # Знаки после слова
        for s in signs_after_word.get(w.id_word, []):
            result_parts.append(s.sign_value)

        prev_para = w.paragraph_index
        prev_sent = w.sentence_index

    return ''.join(result_parts).strip()
