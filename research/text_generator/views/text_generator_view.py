import logging

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from research.text_generator.dataclasses import *
from research.text_generator.utils import generate_text_code, generate_text_by_code, get_random_texts, export_text, \
    export_parsing
from research.text_generator.views.text_generator_code_view import text_generator_code_view
from text_app.models.tbl_textlist import TblTextListDescription

logger = logging.getLogger(__name__)


def text_generator_view(request: HttpRequest) -> HttpResponse:
    """
    Представление для генерации текстов по параметрам.
    """
    mode = request.GET.get('mode', 'byPars')

    # Редирект в режим byCode
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

    # Обработка экспорта
    if action in ['export_text', 'export_parsing']:
        code = request.POST.get('code')
        base_text_id = int(request.POST.get('base_text_id'))
        other_text_id = int(request.POST.get('other_text_id'))

        # Получаем тексты напрямую
        base_text = TblTextListDescription.get_text_by_id(request.user, base_text_id)
        other_text = TblTextListDescription.get_text_by_id(request.user, other_text_id)

        # Преобразуем в TextContent
        base_content = TextContent.from_tbl_text(base_text)
        other_content = TextContent.from_tbl_text(other_text)

        # Генерируем текст по коду
        generated_text = generate_text_by_code(code, base_content.words, other_content.words)

        if action == 'export_text':
            text = export_text(generated_text)
            response = HttpResponse(text, content_type='text/plain')
            response['Content-Disposition'] = 'attachment; filename="generated_text.txt"'
            return response
        elif action == 'export_parsing':
            csv_data = export_parsing(generated_text)
            response = HttpResponse(csv_data, content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="parsing.csv"'
            return response

    params = GeneratorParams(
        base_textlist_id=request.POST.get("base_textlist"),
        other_textlist_id=request.POST.get("other_textlist"),
        random_texts=request.POST.get("random_texts", "off") == "on",
        base_text_id=request.POST.get("base_text"),
        other_text_id=request.POST.get("other_text"),
        percent_of_inserts=float(request.POST.get("percent_of_inserts", 0.20)),
        fragment_size=int(request.POST.get("fragment_size", 10)),
        bind_borders=request.POST.get("bind_borders", "off") == "on",
        code_count=int(request.POST.get("code_count", 1)),
    )

    logger.debug(
        f"ID списка базового текста: {params.base_textlist_id}, ID списка вставляемого текста: {params.other_textlist_id}")

    # Валидация данных
    valid, err_msg = params.validate()

    if not valid:
        return HttpResponse(f"<div class='alert alert-danger'>{err_msg}</div>")

    base_textlist = TblTextListDescription.get_item(request.user, int(params.base_textlist_id))
    other_textlist = TblTextListDescription.get_item(request.user, int(params.other_textlist_id))

    # Логика генерации
    codes = []
    try:
        for _ in range(params.code_count):
            # Получаем элементы текстов из списков
            base_text_items = base_textlist.items
            other_text_items = other_textlist.items

            if not base_text_items or not other_text_items:
                raise ValueError("Один из списков текстов пуст")

            # Выбираем тексты
            if params.random_texts:
                base_text_item, other_text_item = get_random_texts(base_textlist.id, other_textlist.id, base_text_items,
                                                                   other_text_items)
            else:
                base_text_item = next(item for item in base_text_items if str(item.text.id) == params.base_text_id)
                other_text_item = next(item for item in other_text_items if str(item.text.id) == params.other_text_id)

            # Создаем объекты TextContent
            base_content = TextContent.from_tbl_text(base_text_item.text)
            other_content = TextContent.from_tbl_text(other_text_item.text)

            base_words = base_content.words
            other_words = other_content.words

            if not base_words or not other_words:
                raise ValueError("Не удалось получить содержимое одного из текстов")

            base_text_length = len(base_words)
            other_text_length = len(other_words)

            ##### Генерируем код
            code = generate_text_code(
                base_content,
                other_content,
                params.fragment_size,
                params.percent_of_inserts,
                params.bind_borders
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
        return HttpResponse(
            f"<div class='alert alert-danger'>{str(e)}</div>",
            status=400
        )
