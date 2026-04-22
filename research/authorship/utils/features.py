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

    for tok in sent_tokens:
        pos_tags.append(tok.pos)
        dep_rels.append(tok.rel)
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
    tree_depths = []
    tree_widths = []
    sentence_lengths = []

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

    # Нормализация распределений
    total_pos = sum(all_pos_tags.values()) or 1
    total_bigrams = sum(all_pos_bigrams.values()) or 1
    total_trigrams = sum(all_pos_trigrams.values()) or 1
    total_dep = sum(all_dep_rels.values()) or 1
    total_clauses = sum(all_clause_types.values()) or 1

    pos_dist = {tag: all_pos_tags.get(tag, 0) / total_pos for tag in POS_TAGS}
    bigram_dist = {bg: count / total_bigrams for bg, count in all_pos_bigrams.most_common(100)}
    trigram_dist = {tg: count / total_trigrams for tg, count in all_pos_trigrams.most_common(100)}
    dep_dist = {dep: all_dep_rels.get(dep, 0) / total_dep for dep in DEP_TYPES}
    clause_dist = {ct: all_clause_types.get(ct, 0) / total_clauses for ct in CLAUSE_TYPES}

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
      [0:4]     — avg/std sentence length, avg depth, avg width
      [4:21]    — POS-униграммы (17 тегов)
      [21:58]   — типы зависимостей (37 типов)
      [58:62]   — типы предложений (4 типа)
      [62:77]   — распределение глубин деревьев (1..15)
    Итого: 77 признаков.

    Args:
        features: словарь из extract_features_from_text()

    Returns:
        list[float]: вектор длиной 77
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
)

VECTOR_SIZE = len(FEATURE_NAMES)  # 77
