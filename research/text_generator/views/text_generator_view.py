import logging
import random

from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from research.text_generator.utils import generate_text_code, generate_text_by_code, get_random_texts
from research.text_generator.views.text_generator_code_view import text_generator_code_view
from text_app.models.tbl_textlist import TblTextListDescription
from research.text_generator.dataclasses import *

logger = logging.getLogger(__name__)


def text_generator_view(request: HttpRequest) -> HttpResponse:
    """
    Представление для генерации текстов по параметрам.
    """
    mode = request.GET.get('mode', 'byPars')
    
    # Redirect to code view if mode is byCode
    if mode == 'byCode':
        return text_generator_code_view(request)
        
    text_lists = TblTextListDescription.get_items(user=request.user, exclude_deleted=True).order_by("name").all()

    if request.method == "GET":
        logger.debug(f"GET-запрос, mode={mode}")
        # Отображаем форму для генерации по параметрам
        return render(request, "text_generator/form.html", context={
            "text_lists": text_lists,
            "mode": mode,
            "percent_of_inserts": 0.20,
            "fragment_size": 10,
            "code_count": 1,
        })

    # Обработка POST-запроса
    logger.debug(f"POST-запрос, mode={mode}")
    action = request.POST.get('action')
    base_textlist_id = request.POST.get("base_textlist")
    other_textlist_id = request.POST.get("other_textlist")
    random_texts = request.POST.get("random_texts", "off") == "on"
    base_text_id = request.POST.get("base_text")
    other_text_id = request.POST.get("other_text")
    percent_of_inserts = float(request.POST.get("percent_of_inserts", 0.20))
    fragment_size = int(request.POST.get("fragment_size", 10))
    bind_borders = request.POST.get("bind_borders", "off") == "on"
    code_count = int(request.POST.get("code_count", 1))

    logger.debug(f"ID списка базового текста: {base_textlist_id}, ID списка вставляемого текста: {other_textlist_id}")

    # Валидация данных
    err_msg = ""
    try:
        if not base_textlist_id or not other_textlist_id:
            err_msg = "Выберите оба списка текстов"
        else:
            base_textlist = TblTextListDescription.get_item(request.user, int(base_textlist_id))
            other_textlist = TblTextListDescription.get_item(request.user, int(other_textlist_id))
            logger.debug(f"Список базового текста: {base_textlist}, Список вставляемого текста: {other_textlist}")

        percent_of_inserts = float(percent_of_inserts)
        if not 0.01 <= percent_of_inserts <= 0.95:
            err_msg = "Процент вставок должен быть между 0.01 и 0.95"

        fragment_size = int(fragment_size)
        if fragment_size < 5:
            err_msg = "Размер фрагмента должен быть не менее 5"

        code_count = int(code_count)
        if not 1 <= code_count <= 20:
            err_msg = "Количество кодов должно быть между 1 и 20"

        if not random_texts:
            if not base_text_id or not other_text_id:
                err_msg = "Выберите оба текста"

    except ValueError as e:
        err_msg = "Некорректные значения параметров"

    if err_msg:
        return HttpResponse(f"<div class='alert alert-danger'>{err_msg}</div>")

    # Логика генерации
    codes = []
    try:
        for _ in range(code_count):
            # Получаем элементы текстов из списков
            base_text_items = base_textlist.items
            other_text_items = other_textlist.items
            logger.debug(f"Количество элементов базового текста: {len(base_text_items)}, Количество элементов вставляемого текста: {len(other_text_items)}")

            if not base_text_items or not other_text_items:
                raise ValueError("Один из списков текстов пуст")

            # Выбираем тексты
            if random_texts:
                base_text_item, other_text_item = get_random_texts(base_textlist.id, other_textlist.id, base_text_items, other_text_items)
            else:
                base_text_item = next(item for item in base_text_items if str(item.text.id) == base_text_id)
                other_text_item = next(item for item in other_text_items if str(item.text.id) == other_text_id)

            # Создаем объекты TextContent
            base_words = [TextWord(
                word=word.word,
                paragraph_index=word.paragraph_index,
                sentence_index=word.sentence_index,
                word_index=word.word_index
            ) for word in base_text_item.text.get_content()]

            other_words = [TextWord(
                word=word.word,
                paragraph_index=word.paragraph_index,
                sentence_index=word.sentence_index,
                word_index=word.word_index
            ) for word in other_text_item.text.get_content()]

            base_content = TextContent(
                id=base_text_item.text.id,
                words=base_words,
                length=len(base_words)
            )

            other_content = TextContent(
                id=other_text_item.text.id,
                words=other_words,
                length=len(other_words)
            )

            logger.debug(f"ID базового текста: {base_text_item.text.id}")
            logger.debug(f"ID вставляемого текста: {other_text_item.text.id}")
            logger.debug(f"Количество слов в базовом тексте: {len(base_words)}")
            logger.debug(f"Количество слов во вставляемом тексте: {len(other_words)}")

            if not base_words or not other_words:
                raise ValueError("Не удалось получить содержимое одного из текстов")

            logger.debug(f"Длина базового текста: {len(base_words)}")
            logger.debug(f"Длина вставляемого текста: {len(other_words)}")

            base_text_length = len(base_words)
            other_text_length = len(other_words)

            # Генерируем код
            code = generate_text_code(
                base_content,
                other_content,
                fragment_size,
                percent_of_inserts,
                bind_borders
            )
            logger.debug(f"Сгенерированный код: {code}")

            if action == "generate_text":
                # Генерируем текст
                generated_text = generate_text_by_code(code, base_words, other_words)
                codes.append({
                    'code': code,
                    'generated_text': generated_text,
                    'base_text_item': base_text_item,
                    'other_text_item': other_text_item,
                })
            else:
                # Только код
                codes.append({
                    'code': code,
                    'base_text_item': base_text_item,
                    'other_text_item': other_text_item,
                })

        return render(request, "text_generator/result.html", context={
            "codes": codes,
            "mode": mode,
            "action": action,
        })

    except Exception as e:
        logger.exception("Ошибка при генерации текста")
        messages.error(request, f"Ошибка при генерации: {str(e)}")
        return render(request, "text_generator/form.html", context={
            "text_lists": text_lists,
            "mode": mode,
            "percent_of_inserts": percent_of_inserts,
            "fragment_size": fragment_size,
            "code_count": code_count,
            "bind_borders": bind_borders,
        })
