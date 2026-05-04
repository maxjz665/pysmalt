import gzip
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from research.authorship.models import TblSign, TblSyntacticFeature
from research.authorship.utils.features import extract_and_save_features
from research.authorship.utils.importer import import_text_to_db
from text_app.models.tbl_author import TblAuthor
from text_app.models.tbl_text import TblText
from text_app.models.tbl_textlist import TblTextListDescription, TblTextListItems
from text_app.models.tbl_word import TblWord


SMOKE_LIST_NAME = "Authorship smoke 3x4"
SQL_DUMP_NAME = "smalt.sql.20220421.112227.gz"


@dataclass(frozen=True)
class CorpusSpec:
    key: str
    list_name: str
    authors: Tuple[int, ...]
    texts_per_author: int
    target_list_id: Optional[int] = None


CORPUS_SPECS: Dict[str, CorpusSpec] = {
    "5x8": CorpusSpec(
        key="5x8",
        list_name="Authorship corpus 5x8",
        authors=(10, 1, 15, 32, 14),
        texts_per_author=8,
        target_list_id=3,
    ),
    "5x7": CorpusSpec(
        key="5x7",
        list_name="Authorship corpus 5x7",
        authors=(1, 15, 14, 2, 4),
        texts_per_author=7,
        target_list_id=4,
    ),
    "7x6": CorpusSpec(
        key="7x6",
        list_name="Authorship corpus 7x6",
        authors=(1, 15, 14, 2, 4, 26, 32),
        texts_per_author=6,
        target_list_id=5,
    ),
}


SMOKE_TEXTS: Dict[str, List[Tuple[str, str]]] = {
    "Автор наблюдений": [
        (
            "Сад после дождя",
            "После дождя сад стоял тихо и внимательно. На дорожках темнели "
            "лужицы, листья блестели, и каждая ветка будто прислушивалась к "
            "вечеру. Я долго смотрел на мокрую сирень и думал, что город "
            "становится мягче, когда вода смывает с него дневную пыль.",
        ),
        (
            "Утренний двор",
            "Утром двор просыпался без спешки. Дворник проводил метлой по "
            "камням, в окнах появлялся свет, а над крышами медленно поднимался "
            "пар. В такие минуты даже обычный дом казался живым собеседником.",
        ),
        (
            "Письмо о реке",
            "Река за городом шла широко и спокойно. У берега лежали лодки, "
            "мальчики спорили о рыбе, и песок был теплым от солнца. Я записал "
            "эти мелочи, потому что именно в них держится память о месте.",
        ),
        (
            "Вечерняя улица",
            "К вечеру улица наполнилась редкими шагами. Фонари зажглись не сразу, "
            "и короткая серая полоса сумерек легла между домами. Мне нравилось, "
            "что шум дня уходил постепенно, не разрушая тишину.",
        ),
    ],
    "Автор рассуждений": [
        (
            "О школьном порядке",
            "Порядок в школе начинается не с приказа, а с понятного правила. "
            "Если ученик знает меру требования, он легче принимает труд. "
            "Поэтому всякое распоряжение должно быть кратким, проверяемым и "
            "одинаковым для всех участников дела.",
        ),
        (
            "О городской пользе",
            "Городская польза редко возникает сама собой. Ее создают учет, "
            "бережливость и привычка доводить начатое до конца. Когда решение "
            "объяснено ясно, жители охотнее участвуют в общем деле.",
        ),
        (
            "О чтении",
            "Чтение полезно тогда, когда оно рождает вопрос. Простое накопление "
            "книг не делает человека внимательнее. Надо сравнивать выводы, "
            "отделять доказанное от случайного и возвращаться к трудному месту.",
        ),
        (
            "О ремесле",
            "В каждом ремесле важна последовательность операций. Нельзя требовать "
            "точного результата, если материалы не проверены заранее. Такая "
            "простая дисциплина экономит силы и делает работу надежной.",
        ),
    ],
    "Автор рассказов": [
        (
            "На станции",
            "Поезд задержался, и все сразу стали знакомыми. Купец ругал часы, "
            "студент смеялся над расписанием, а старуха берегла узелок так, "
            "словно в нем лежала вся станция. Через час мы уже делились хлебом.",
        ),
        (
            "Случай в лавке",
            "В лавке пахло яблоками и керосином. Хозяин уверял, что сахар нынче "
            "особенный, но мальчишка за прилавком подмигнул мне и насыпал ровно "
            "на две щепотки больше. Так покупка превратилась в маленькое "
            "соглашение.",
        ),
        (
            "У переправы",
            "Паромщик молчал, пока лодка шла через темную воду. Потом он вдруг "
            "сказал, что река помнит всех торопливых людей и никого не держит "
            "насильно. Пассажиры переглянулись, и спор о дороге сам собою стих.",
        ),
        (
            "Гость",
            "Гость вошел в комнату с таким видом, будто опоздал не на обед, а "
            "на собственную судьбу. Он снял шляпу, попросил чаю и сразу начал "
            "рассказывать историю, в которой все были виноваты понемногу.",
        ),
    ],
}


class CorpusLoadError(RuntimeError):
    pass


def find_sql_dump(explicit_path: Optional[str] = None) -> Optional[Path]:
    candidates: List[Path] = []
    if explicit_path:
        candidates.append(Path(explicit_path))

    base_dir = Path(settings.BASE_DIR)
    candidates.extend([
        base_dir / SQL_DUMP_NAME,
        base_dir.parent / SQL_DUMP_NAME,
        base_dir.parent.parent / SQL_DUMP_NAME,
    ])

    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    return None


def _safe_text(value: Optional[str]) -> str:
    return value or ""


def _get_or_create_author(name: str, origin_name: str = "", real_name: str = "") -> TblAuthor:
    author = TblAuthor.objects.filter(name=name).first()
    if author:
        changed = False
        if origin_name and not author.origin_name:
            author.origin_name = origin_name
            changed = True
        if real_name and not author.real_name:
            author.real_name = real_name
            changed = True
        if changed:
            author.save(update_fields=["origin_name", "real_name"])
        return author
    return TblAuthor.objects.create(
        name=name,
        origin_name=origin_name,
        real_name=real_name,
    )


def _get_or_create_list(name: str, target_id: Optional[int] = None) -> TblTextListDescription:
    text_list = TblTextListDescription.objects.filter(name=name).first()
    if text_list:
        if not text_list.public or text_list.is_deleted:
            text_list.public = True
            text_list.is_deleted = False
            text_list.save(update_fields=["public", "is_deleted"])
        return text_list

    if target_id and not TblTextListDescription.objects.filter(id=target_id).exists():
        return TblTextListDescription.objects.create(
            id=target_id,
            name=name,
            public=True,
            is_deleted=False,
        )
    return TblTextListDescription.objects.create(
        name=name,
        public=True,
        is_deleted=False,
    )


def _ensure_list_item(text_list: TblTextListDescription, text: TblText) -> None:
    if not TblTextListItems.objects.filter(list=text_list, text=text).exists():
        TblTextListItems.objects.create(list=text_list, text=text)


def _upsert_text_shell(idkey: str, title: str, author: TblAuthor) -> TblText:
    text = TblText.objects.filter(idkey=idkey).first()
    defaults = {
        "title": title,
        "author": author,
        "inuse1": 1,
        "inuse2": 0,
        "syntax": 1,
        "category": 0,
        "text_type": 0,
        "author_verify": 1,
        "status": 2,
        "idkey": idkey,
        "origin_title": title,
    }
    if text:
        for field, value in defaults.items():
            setattr(text, field, value)
        text.save()
        return text
    return TblText.objects.create(**defaults)


def _extract_feature_if_needed(text: TblText, force: bool = False):
    if force or not TblSyntacticFeature.objects.filter(text=text, vector_size=193).exists():
        return extract_and_save_features(text)
    return TblSyntacticFeature.objects.get(text=text)


def load_smoke_corpus(extract_features: bool = True, force_extract: bool = False) -> dict:
    text_list = _get_or_create_list(SMOKE_LIST_NAME)
    loaded_texts: List[TblText] = []
    extracted = 0

    with transaction.atomic():
        for author_name, texts in SMOKE_TEXTS.items():
            author = _get_or_create_author(author_name)
            for index, (title, raw_text) in enumerate(texts, start=1):
                idkey = f"authorship-smoke-{author_name}-{index}".lower().replace(" ", "-")
                text = _upsert_text_shell(idkey=idkey, title=title, author=author)
                import_text_to_db(text, raw_text)
                _ensure_list_item(text_list, text)
                loaded_texts.append(text)

    if extract_features:
        for text in loaded_texts:
            _extract_feature_if_needed(text, force=force_extract)
            extracted += 1

    return {
        "corpus": "smoke",
        "list_id": text_list.id,
        "list_name": text_list.name,
        "texts": len(loaded_texts),
        "authors": len(SMOKE_TEXTS),
        "features_extracted": extracted,
        "source": "bundled smoke texts parsed by Natasha",
    }


def _open_dump(path: Path):
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8", errors="replace")
    return path.open("rt", encoding="utf-8", errors="replace")


def _split_insert_rows(values_sql: str) -> Iterable[str]:
    in_quote = False
    escaped = False
    depth = 0
    buf: List[str] = []

    for ch in values_sql:
        if in_quote:
            buf.append(ch)
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == "'":
                in_quote = False
            continue

        if ch == "'":
            in_quote = True
            buf.append(ch)
        elif ch == "(":
            if depth == 0:
                buf = []
            else:
                buf.append(ch)
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                yield "".join(buf)
                buf = []
            else:
                buf.append(ch)
        else:
            if depth > 0:
                buf.append(ch)


def _parse_sql_row(row_sql: str) -> List[object]:
    values: List[object] = []
    buf: List[str] = []
    in_quote = False
    escaped = False

    def flush() -> None:
        raw = "".join(buf).strip()
        buf.clear()
        if raw.upper() == "NULL":
            values.append(None)
        elif len(raw) >= 2 and raw[0] == "'" and raw[-1] == "'":
            values.append(_decode_sql_string(raw[1:-1]))
        else:
            try:
                values.append(int(raw))
            except ValueError:
                values.append(raw)

    for ch in row_sql:
        if in_quote:
            buf.append(ch)
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == "'":
                in_quote = False
            continue

        if ch == "'":
            in_quote = True
            buf.append(ch)
        elif ch == ",":
            flush()
        else:
            buf.append(ch)

    flush()
    return values


def _decode_sql_string(value: str) -> str:
    out: List[str] = []
    escaped = False
    escapes = {
        "0": "\0",
        "n": "\n",
        "r": "\r",
        "t": "\t",
        "b": "\b",
        "Z": "\x1a",
        "\\": "\\",
        "'": "'",
        '"': '"',
    }
    for ch in value:
        if escaped:
            out.append(escapes.get(ch, ch))
            escaped = False
        elif ch == "\\":
            escaped = True
        else:
            out.append(ch)
    if escaped:
        out.append("\\")
    return "".join(out)


def _iter_table_rows(path: Path, table: str) -> Iterable[List[object]]:
    prefix = f"INSERT INTO `{table}`"
    with _open_dump(path) as fh:
        for line in fh:
            if not line.startswith(prefix):
                continue
            marker = " VALUES "
            try:
                values_sql = line.split(marker, 1)[1]
            except IndexError:
                continue
            values_sql = values_sql.rstrip().rstrip(";")
            for row_sql in _split_insert_rows(values_sql):
                yield _parse_sql_row(row_sql)


def _read_sql_authors(path: Path) -> Dict[int, Tuple[str, str, str]]:
    authors: Dict[int, Tuple[str, str, str]] = {}
    for row in _iter_table_rows(path, "author"):
        authors[int(row[0])] = (_safe_text(row[1]), _safe_text(row[2]), _safe_text(row[3]))
    return authors


def _read_sql_texts(path: Path, author_ids: Sequence[int]) -> Dict[int, List[dict]]:
    wanted = set(author_ids)
    by_author: Dict[int, List[dict]] = defaultdict(list)
    for row in _iter_table_rows(path, "text"):
        author_id = row[2]
        if author_id not in wanted:
            continue
        by_author[int(author_id)].append({
            "source_id": int(row[0]),
            "title": _safe_text(row[1]) or f"Text {row[0]}",
            "publication_date": row[5],
            "idkey": _safe_text(row[27]),
            "origin_title": _safe_text(row[28]),
        })
    for texts in by_author.values():
        texts.sort(key=lambda item: item["source_id"])
    return by_author


def _select_sql_texts(path: Path, spec: CorpusSpec) -> Tuple[Dict[int, Tuple[str, str, str]], List[dict]]:
    authors = _read_sql_authors(path)
    texts_by_author = _read_sql_texts(path, spec.authors)
    selected: List[dict] = []
    missing: List[str] = []

    for author_id in spec.authors:
        pool = texts_by_author.get(author_id, [])
        if len(pool) < spec.texts_per_author:
            author_name = authors.get(author_id, (f"author #{author_id}", "", ""))[0]
            missing.append(f"{author_name}: need {spec.texts_per_author}, found {len(pool)}")
            continue
        for item in pool[:spec.texts_per_author]:
            item["author_id"] = author_id
            selected.append(item)

    if missing:
        raise CorpusLoadError("SQL dump does not contain enough texts: " + "; ".join(missing))

    return authors, selected


def _collect_sql_words(path: Path, source_text_ids: Sequence[int]) -> Dict[int, List[Tuple[int, int, int, int, str]]]:
    wanted = set(source_text_ids)
    words: Dict[int, List[Tuple[int, int, int, int, str]]] = defaultdict(list)
    for row in _iter_table_rows(path, "word"):
        if row[1] is None:
            continue
        text_id = int(row[1])
        if text_id not in wanted:
            continue
        words[text_id].append((int(row[3]), int(row[4]), int(row[5]), int(row[6]), _safe_text(row[8])))
    for text_words in words.values():
        text_words.sort(key=lambda item: (item[0], item[1], item[2], item[3]))
    return words


def _replace_text_words(text: TblText, rows: Sequence[Tuple[int, int, int, int, str]]) -> None:
    TblSign.objects.filter(text=text).delete()
    TblWord.objects.filter(text=text).delete()
    now = timezone.now()
    objects = [
        TblWord(
            text=text,
            word_length=len(word),
            chapter_index=chapter,
            paragraph_index=paragraph,
            sentence_index=sentence,
            word_index=word_index,
            chdate=now,
            word=word,
            dictword=None,
            dictword2=None,
            wordorder=0,
            wordno=0,
        )
        for chapter, paragraph, sentence, word_index, word in rows
        if word
    ]
    TblWord.objects.bulk_create(objects, batch_size=1000)


def load_sql_corpus(
    corpus: str,
    sql_path: Path,
    extract_features: bool = True,
    force_extract: bool = False,
) -> dict:
    if corpus not in CORPUS_SPECS:
        raise CorpusLoadError(f"Unknown corpus: {corpus}")

    spec = CORPUS_SPECS[corpus]
    authors_from_sql, selected = _select_sql_texts(sql_path, spec)
    words_by_source_id = _collect_sql_words(sql_path, [item["source_id"] for item in selected])

    text_list = _get_or_create_list(spec.list_name, target_id=spec.target_list_id)
    loaded_texts: List[TblText] = []

    with transaction.atomic():
        for author_id in spec.authors:
            name, origin_name, real_name = authors_from_sql[author_id]
            _get_or_create_author(name, origin_name, real_name)

        for item in selected:
            author_name, origin_name, real_name = authors_from_sql[item["author_id"]]
            author = _get_or_create_author(author_name, origin_name, real_name)
            source_id = item["source_id"]
            words = words_by_source_id.get(source_id)
            if not words:
                raise CorpusLoadError(f"SQL dump has no word rows for text {source_id}")

            idkey = f"authorship-{corpus}-sql-{source_id}"
            text = _upsert_text_shell(idkey=idkey, title=item["title"], author=author)
            _replace_text_words(text, words)
            _ensure_list_item(text_list, text)
            loaded_texts.append(text)

    extracted = 0
    if extract_features:
        for text in loaded_texts:
            _extract_feature_if_needed(text, force=force_extract)
            extracted += 1

    return {
        "corpus": corpus,
        "list_id": text_list.id,
        "list_name": text_list.name,
        "texts": len(loaded_texts),
        "authors": len(spec.authors),
        "features_extracted": extracted,
        "source": str(sql_path),
    }


def load_corpus(
    corpus: str = "smoke",
    sql_path: Optional[str] = None,
    extract_features: bool = True,
    force_extract: bool = False,
) -> List[dict]:
    if corpus == "smoke":
        return [load_smoke_corpus(extract_features=extract_features, force_extract=force_extract)]

    if corpus == "all":
        keys = ("5x8", "5x7", "7x6")
    else:
        keys = (corpus,)

    dump_path = find_sql_dump(sql_path)
    if not dump_path:
        raise CorpusLoadError(
            "Full corpora require the real SMALT SQL dump. Put "
            f"{SQL_DUMP_NAME} in the project root, next to the project root, "
            "or pass --source-sql=/path/to/dump. No synthetic full corpus is used."
        )

    results = []
    for key in keys:
        results.append(
            load_sql_corpus(
                key,
                sql_path=dump_path,
                extract_features=extract_features,
                force_extract=force_extract,
            )
        )
    return results


def get_default_authorship_list() -> Optional[TblTextListDescription]:
    names = [SMOKE_LIST_NAME] + [spec.list_name for spec in CORPUS_SPECS.values()]
    for name in names:
        text_list = TblTextListDescription.objects.filter(name=name, is_deleted=False).first()
        if text_list:
            return text_list
    return TblTextListDescription.objects.filter(public=True, is_deleted=False).order_by("id").first()
