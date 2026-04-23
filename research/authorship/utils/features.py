"""
Модуль извлечения синтаксических признаков текста.

Общий для обоих алгоритмов. Из деревьев зависимостей Natasha
извлекаются признаки, характеризующие синтаксический стиль автора:
распределения POS-тегов, типов зависимостей, глубин деревьев,
типов предложений и пунктуационных паттернов.
"""
import logging
import math
from collections import Counter, defaultdict
from typing import List, Dict, Optional, Tuple

import numpy as np
from natasha import Doc

from research.authorship.utils.importer import get_natasha_doc, normalize_text, split_into_paragraphs

logger = logging.getLogger(__name__)

# ────────────────────────────────────────────────────────────
#  Константы: фиксированный порядок признаков
# ────────────────────────────────────────────────────────────

# Универсальные POS-теги (Universal Dependencies)
POS_TAGS = [
    'ADJ', 'ADP', 'ADV', 'AUX', 'CCONJ', 'DET', 'INTJ',
    'NOUN', 'NUM', 'PART', 'PRON', 'PROPN', 'PUNCT',
    'SCONJ', 'SYM', 'VERB', 'X'
]

# Типы синтаксических зависимостей (основные для русского языка)
DEP_TYPES = [
    'acl', 'acl:relcl', 'advcl', 'advmod', 'amod', 'appos',
    'aux', 'aux:pass', 'case', 'cc', 'ccomp', 'compound',
    'conj', 'cop', 'csubj', 'dep', 'det', 'discourse',
    'expl', 'fixed', 'flat', 'flat:foreign', 'flat:name',
    'iobj', 'mark', 'nmod', 'nsubj', 'nsubj:pass', 'nummod',
    'nummod:gov', 'obj', 'obl', 'orphan', 'parataxis',
    'punct', 'root', 'vocative', 'xcomp'
]

# Типы предложений по структуре
CLAUSE_TYPES = [
    'simple',          # простое
    'compound',        # сложносочинённое
    'complex',         # сложноподчинённое
    'compound_complex', # сложное с сочинением и подчинением
]

POS_TAG_INDEX = {tag: i for i, tag in enumerate(POS_TAGS)}
DEP_TYPE_INDEX = {dep: i for i, dep in enumerate(DEP_TYPES)}


# ────────────────────────────────────────────────────────────
#  Расширенные синтаксические признаки
# ────────────────────────────────────────────────────────────

# POS-биграммы: наиболее частотные переходы между частями речи
# в русском тексте. Отражают предпочитаемые автором синтаксические
# последовательности.
POS_BIGRAMS_VOCAB = [
    'NOUN_NOUN', 'ADJ_NOUN', 'NOUN_ADJ', 'ADP_NOUN', 'ADP_ADJ',
    'ADP_PRON', 'NOUN_ADP', 'VERB_NOUN', 'NOUN_VERB', 'PRON_VERB',
    'VERB_PRON', 'VERB_ADP', 'VERB_ADV', 'ADV_VERB', 'VERB_VERB',
    'CCONJ_NOUN', 'CCONJ_VERB', 'CCONJ_PRON', 'CCONJ_ADJ', 'PUNCT_CCONJ',
    'PUNCT_SCONJ', 'PUNCT_PRON', 'SCONJ_PRON', 'SCONJ_VERB', 'SCONJ_NOUN',
    'PART_VERB', 'PART_ADJ', 'DET_NOUN', 'ADJ_ADJ', 'NUM_NOUN',
]

# Синтаксические продукции (head_POS -- dep_rel --> child_POS):
# чисто синтаксические тройки из дерева зависимостей, не сводящиеся
# ни к лексике, ни к морфологии по отдельности.
SYNTACTIC_PRODUCTIONS_VOCAB = [
    'VERB-nsubj-NOUN', 'VERB-nsubj-PRON', 'VERB-obj-NOUN', 'VERB-obj-PRON',
    'VERB-obl-NOUN', 'VERB-advmod-ADV', 'VERB-xcomp-VERB', 'VERB-ccomp-VERB',
    'VERB-advcl-VERB', 'VERB-conj-VERB', 'VERB-aux-AUX', 'VERB-cop-AUX',
    'VERB-mark-SCONJ', 'VERB-cc-CCONJ', 'VERB-parataxis-VERB',
    'NOUN-amod-ADJ', 'NOUN-nmod-NOUN', 'NOUN-case-ADP', 'NOUN-det-DET',
    'NOUN-nummod-NUM', 'NOUN-acl-VERB', 'NOUN-appos-NOUN', 'NOUN-conj-NOUN',
    'ADJ-conj-ADJ', 'ADJ-cc-CCONJ',
]

# Служебные (функциональные) слова — классический стилеметрический
# маркер (Mosteller & Wallace, Burrows). Сопоставляются по лемме,
# поэтому разные словоформы ("ему", "его", "им") сводятся к одной статье.
FUNCTION_WORDS_VOCAB = [
    # предлоги (20)
    'в', 'на', 'с', 'по', 'к', 'от', 'из', 'за', 'у', 'для',
    'о', 'об', 'про', 'при', 'под', 'над', 'через', 'между', 'без', 'до',
    # союзы (12)
    'и', 'а', 'но', 'или', 'как', 'что', 'чтобы', 'если', 'когда', 'потому',
    'хотя', 'тогда',
    # частицы (10)
    'не', 'ни', 'же', 'ли', 'бы', 'уже', 'ещё', 'только', 'даже', 'вот',
    # местоимения и определители (18)
    'я', 'ты', 'он', 'она', 'оно', 'они', 'мы', 'вы',
    'этот', 'тот', 'такой', 'свой', 'его', 'её', 'их',
    'весь', 'сам', 'который',
]

_FUNCTION_WORDS_SET = set(FUNCTION_WORDS_VOCAB)


# ────────────────────────────────────────────────────────────
#  Извлечение признаков из одного предложения
# ────────────────────────────────────────────────────────────

def _get_tree_depth(tokens: list, head_map: dict, root_id: str, memo: dict = None) -> int:
    """
    Вычисляет глубину дерева зависимостей от заданного корня.
    """
    if memo is None:
        memo = {}
    if root_id in memo:
        return memo[root_id]

    children = head_map.get(root_id, [])
    if not children:
        memo[root_id] = 1
        return 1

    max_child_depth = 0
    for child_id in children:
        d = _get_tree_depth(tokens, head_map, child_id, memo)
        if d > max_child_depth:
            max_child_depth = d
    depth = 1 + max_child_depth
    memo[root_id] = depth
    return depth


def _classify_sentence(tokens: list) -> str:
    """
    Определяет тип предложения по синтаксической структуре.

    Returns:
        str: один из CLAUSE_TYPES
    """
    has_ccomp_or_advcl = False
    has_conj_verb = False
    root_count = 0

    dep_rels = set()
    for tok in tokens:
        rel = tok.rel
        dep_rels.add(rel)
        if rel == 'root':
            root_count += 1
        if rel in ('ccomp', 'advcl', 'acl:relcl', 'csubj'):
            has_ccomp_or_advcl = True
        if rel == 'conj' and tok.pos in ('VERB', 'AUX'):
            has_conj_verb = True

    if has_ccomp_or_advcl and has_conj_verb:
        return 'compound_complex'
    elif has_ccomp_or_advcl:
        return 'complex'
    elif has_conj_verb:
        return 'compound'
    else:
        return 'simple'


def _extract_sentence_features(sent_tokens: list) -> dict:
    """
    Извлекает признаки из одного предложения (списка токенов Natasha).

    Returns:
        dict: признаки предложения
    """
    pos_tags = []
    dep_rels = []
    head_map = defaultdict(list)  # head_id -> [child_ids]
    root_id = None
    tok_by_id = {}

    for tok in sent_tokens:
        pos_tags.append(tok.pos)
        dep_rels.append(tok.rel)
        tok_by_id[tok.id] = tok
        if tok.rel == 'root':
            root_id = tok.id
        head_map[tok.head_id].append(tok.id)

    # Глубина дерева
    tree_depth = 0
    if root_id:
        memo = {}
        tree_depth = _get_tree_depth(sent_tokens, head_map, root_id, memo)

    # Ширина дерева = макс. кол-во детей у одного узла
    tree_width = max((len(ch) for ch in head_map.values()), default=0)

    # POS n-граммы
    pos_bigrams = []
    pos_trigrams = []
    for i in range(len(pos_tags) - 1):
        pos_bigrams.append(f"{pos_tags[i]}_{pos_tags[i + 1]}")
    for i in range(len(pos_tags) - 2):
        pos_trigrams.append(f"{pos_tags[i]}_{pos_tags[i + 1]}_{pos_tags[i + 2]}")

    # Синтаксические продукции: (head_POS, dep_rel, child_POS)
    productions = []
    for tok in sent_tokens:
        if tok.rel == 'root':
            continue
        head = tok_by_id.get(tok.head_id)
        if head is None:
            continue
        productions.append(f"{head.pos}-{tok.rel}-{tok.pos}")

    # Леммы функциональных слов (служебные части речи)
    function_word_lemmas = []
    for tok in sent_tokens:
        lemma = (getattr(tok, 'lemma', None) or tok.text).lower()
        if lemma in _FUNCTION_WORDS_SET:
            function_word_lemmas.append(lemma)

    # Тип предложения
    clause_type = _classify_sentence(sent_tokens)

    # Количество слов (без пунктуации)
    word_count = sum(1 for p in pos_tags if p != 'PUNCT')

    return {
        'word_count': word_count,
        'tree_depth': tree_depth,
        'tree_width': tree_width,
        'pos_tags': pos_tags,
        'pos_bigrams': pos_bigrams,
        'pos_trigrams': pos_trigrams,
        'productions': productions,
        'function_word_lemmas': function_word_lemmas,
        'dep_rels': dep_rels,
        'clause_type': clause_type,
    }


# ────────────────────────────────────────────────────────────
#  Извлечение признаков из всего текста
# ────────────────────────────────────────────────────────────

def extract_features_from_text(raw_text: str) -> dict:
    """
    Извлекает полный набор синтаксических признаков из текста.

    Args:
        raw_text: исходный текст

    Returns:
        dict: словарь с признаками и распределениями
    """
    text = normalize_text(raw_text)
    paragraphs = split_into_paragraphs(text)

    all_pos_tags = Counter()
    all_pos_bigrams = Counter()
    all_pos_trigrams = Counter()
    all_dep_rels = Counter()
    all_clause_types = Counter()
    all_productions = Counter()
    all_function_words = Counter()
    tree_depths = []
    tree_widths = []
    sentence_lengths = []
    total_tokens = 0  # общее число токенов (для нормировки функциональных слов)

    for paragraph in paragraphs:
        doc = get_natasha_doc(paragraph)
        for sent in doc.sents:
            # Собираем токены предложения
            sent_tokens = [tok for tok in doc.tokens
                           if tok.start >= sent.start and tok.stop <= sent.stop]
            if not sent_tokens:
                continue

            features = _extract_sentence_features(sent_tokens)

            sentence_lengths.append(features['word_count'])
            tree_depths.append(features['tree_depth'])
            tree_widths.append(features['tree_width'])

            all_pos_tags.update(features['pos_tags'])
            all_pos_bigrams.update(features['pos_bigrams'])
            all_pos_trigrams.update(features['pos_trigrams'])
            all_dep_rels.update(features['dep_rels'])
            all_clause_types[features['clause_type']] += 1
            all_productions.update(features['productions'])
            all_function_words.update(features['function_word_lemmas'])
            total_tokens += features['word_count']

    # Нормализация распределений
    total_pos = sum(all_pos_tags.values()) or 1
    total_bigrams = sum(all_pos_bigrams.values()) or 1
    total_trigrams = sum(all_pos_trigrams.values()) or 1
    total_dep = sum(all_dep_rels.values()) or 1
    total_clauses = sum(all_clause_types.values()) or 1
    total_productions = sum(all_productions.values()) or 1
    total_tokens_safe = total_tokens or 1

    pos_dist = {tag: all_pos_tags.get(tag, 0) / total_pos for tag in POS_TAGS}
    bigram_dist = {bg: count / total_bigrams for bg, count in all_pos_bigrams.most_common(100)}
    trigram_dist = {tg: count / total_trigrams for tg, count in all_pos_trigrams.most_common(100)}
    dep_dist = {dep: all_dep_rels.get(dep, 0) / total_dep for dep in DEP_TYPES}
    clause_dist = {ct: all_clause_types.get(ct, 0) / total_clauses for ct in CLAUSE_TYPES}

    # Частоты целевых POS-биграмм из словаря (нормировка на общее число биграмм)
    pos_bigram_vocab_dist = {
        bg: all_pos_bigrams.get(bg, 0) / total_bigrams
        for bg in POS_BIGRAMS_VOCAB
    }

    # Частоты целевых синтаксических продукций (нормировка на общее число продукций)
    production_dist = {
        prod: all_productions.get(prod, 0) / total_productions
        for prod in SYNTACTIC_PRODUCTIONS_VOCAB
    }

    # Частоты функциональных слов (нормировка на общее число токенов-слов)
    function_word_dist = {
        fw: all_function_words.get(fw, 0) / total_tokens_safe
        for fw in FUNCTION_WORDS_VOCAB
    }

    # Статистики по длинам предложений
    avg_sent_len = np.mean(sentence_lengths) if sentence_lengths else 0
    std_sent_len = np.std(sentence_lengths) if sentence_lengths else 0
    avg_depth = np.mean(tree_depths) if tree_depths else 0
    avg_width = np.mean(tree_widths) if tree_widths else 0

    # Распределение глубин деревьев
    depth_counter = Counter(tree_depths)
    max_depth = max(tree_depths) if tree_depths else 0
    depth_dist = {str(d): depth_counter.get(d, 0) / len(tree_depths)
                  for d in range(1, min(max_depth + 1, 16))}

    return {
        'avg_sentence_length': float(avg_sent_len),
        'std_sentence_length': float(std_sent_len),
        'avg_tree_depth': float(avg_depth),
        'avg_tree_width': float(avg_width),
        'pos_unigram_dist': pos_dist,
        'pos_bigram_dist': bigram_dist,
        'pos_trigram_dist': trigram_dist,
        'dep_type_dist': dep_dist,
        'clause_type_dist': clause_dist,
        'tree_depth_dist': depth_dist,
        'pos_bigram_vocab_dist': pos_bigram_vocab_dist,
        'production_dist': production_dist,
        'function_word_dist': function_word_dist,
        'sentences_count': len(sentence_lengths),
    }


# ────────────────────────────────────────────────────────────
#  Формирование единого вектора признаков
# ────────────────────────────────────────────────────────────

def build_feature_vector(features: dict) -> List[float]:
    """
    Собирает из словаря признаков единый числовой вектор
    фиксированной длины. Используется обоими алгоритмами.

    Структура вектора (порядок фиксирован):
      [0:4]      — скалярные признаки (avg/std длины, avg глубина/ширина)
      [4:21]     — POS-униграммы (17 тегов)
      [21:59]    — типы зависимостей (38 типов)
      [59:63]    — типы предложений (4 типа)
      [63:78]    — распределение глубин деревьев (1..15)
      [78:108]   — POS-биграммы из словаря (30)
      [108:133]  — синтаксические продукции (head_POS-dep-child_POS) (25)
      [133:193]  — функциональные (служебные) слова (60)

    Актуальные размеры блоков выводятся из констант модуля,
    поэтому при расширении словарей вектор растёт автоматически.

    Args:
        features: словарь из extract_features_from_text()

    Returns:
        list[float]: вектор признаков
    """
    vec = []

    # Скалярные признаки
    vec.append(features['avg_sentence_length'])
    vec.append(features['std_sentence_length'])
    vec.append(features['avg_tree_depth'])
    vec.append(features['avg_tree_width'])

    # POS-униграммы
    pos_dist = features['pos_unigram_dist']
    for tag in POS_TAGS:
        vec.append(pos_dist.get(tag, 0.0))

    # Типы зависимостей
    dep_dist = features['dep_type_dist']
    for dep in DEP_TYPES:
        vec.append(dep_dist.get(dep, 0.0))

    # Типы предложений
    clause_dist = features['clause_type_dist']
    for ct in CLAUSE_TYPES:
        vec.append(clause_dist.get(ct, 0.0))

    # Распределение глубин деревьев
    depth_dist = features['tree_depth_dist']
    for d in range(1, 16):
        vec.append(depth_dist.get(str(d), 0.0))

    # POS-биграммы из фиксированного словаря
    pbv = features.get('pos_bigram_vocab_dist', {})
    for bg in POS_BIGRAMS_VOCAB:
        vec.append(pbv.get(bg, 0.0))

    # Синтаксические продукции
    prod_dist = features.get('production_dist', {})
    for prod in SYNTACTIC_PRODUCTIONS_VOCAB:
        vec.append(prod_dist.get(prod, 0.0))

    # Функциональные слова
    fw_dist = features.get('function_word_dist', {})
    for fw in FUNCTION_WORDS_VOCAB:
        vec.append(fw_dist.get(fw, 0.0))

    return vec


def extract_and_vectorize(raw_text: str) -> Tuple[dict, List[float]]:
    """
    Полный пайплайн: текст → признаки → вектор.

    Returns:
        tuple: (dict признаков, list вектора)
    """
    features = extract_features_from_text(raw_text)
    vector = build_feature_vector(features)
    return features, vector


# ────────────────────────────────────────────────────────────
#  Сохранение признаков в БД
# ────────────────────────────────────────────────────────────

def extract_and_save_features(text_obj) -> 'TblSyntacticFeature':
    """
    Извлекает признаки текста и сохраняет в БД.

    Args:
        text_obj: TblText или объект с .get_content() и .id

    Returns:
        TblSyntacticFeature
    """
    from research.authorship.models import TblSyntacticFeature

    # Получаем содержимое текста из SMALT
    words = text_obj.get_content()
    if not words:
        raise ValueError(f"Текст {text_obj.id} не содержит слов")

    # Восстанавливаем текст из слов
    raw_text = ' '.join(w.word for w in words)

    features, vector = extract_and_vectorize(raw_text)

    sf, created = TblSyntacticFeature.objects.update_or_create(
        text=text_obj,
        defaults={
            'avg_sentence_length': features['avg_sentence_length'],
            'std_sentence_length': features['std_sentence_length'],
            'avg_tree_depth': features['avg_tree_depth'],
            'avg_tree_width': features['avg_tree_width'],
            'pos_unigram_dist': features['pos_unigram_dist'],
            'pos_bigram_dist': features['pos_bigram_dist'],
            'pos_trigram_dist': features['pos_trigram_dist'],
            'dep_type_dist': features['dep_type_dist'],
            'clause_type_dist': features['clause_type_dist'],
            'punct_pattern_dist': {},
            'tree_depth_dist': features['tree_depth_dist'],
            'feature_vector': vector,
        }
    )
    return sf


# ────────────────────────────────────────────────────────────
#  Описание вектора признаков (для отчётов)
# ────────────────────────────────────────────────────────────

FEATURE_NAMES = (
    ['avg_sentence_length', 'std_sentence_length',
     'avg_tree_depth', 'avg_tree_width']
    + [f'pos_{tag}' for tag in POS_TAGS]
    + [f'dep_{dep}' for dep in DEP_TYPES]
    + [f'clause_{ct}' for ct in CLAUSE_TYPES]
    + [f'depth_{d}' for d in range(1, 16)]
    + [f'posbi_{bg}' for bg in POS_BIGRAMS_VOCAB]
    + [f'prod_{prod}' for prod in SYNTACTIC_PRODUCTIONS_VOCAB]
    + [f'fw_{fw}' for fw in FUNCTION_WORDS_VOCAB]
)

VECTOR_SIZE = len(FEATURE_NAMES)
