import random
import re
from django.shortcuts import render
from django.http import HttpRequest, HttpResponse
from django.contrib import messages
from text_app.models.tbl_textlist import TblTextListDescription
from .utils import generate_text_code, parse_code, generate_text_by_code
import nltk

# Загружаем необходимые данные для NLTK (для работы с предложениями)
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

def text_generator_view(request: HttpRequest) -> HttpResponse:
    """
    Представление для генерации текстов.
    Поддерживает два режима: "По параметрам" и "По коду".
    """
    mode = request.GET.get('mode', 'byPars')
    text_lists = TblTextListDescription.get_items(user=request.user, exclude_deleted=True).order_by("name").all()

    if mode == 'byPars':
        if request.method == "GET":
            # Отображаем форму для генерации по параметрам
            return render(request, "text_generator/form.html", context={
                "text_lists": text_lists,
                "mode": mode,
                "percent_of_inserts": 0.20,
                "fragment_size": 10,
                "code_count": 1,
            })

        # Обработка POST-запроса для режима "По параметрам"
        action = request.POST.get('action')
        base_textlist_id = request.POST.get("base_textlist", None)
        other_textlist_id = request.POST.get("other_textlist", None)
        random_texts = request.POST.get("random_texts", "off") == "on"
        base_text_id = request.POST.get("base_text", None)
        other_text_id = request.POST.get("other_text", None)
        percent_of_inserts = request.POST.get("percent_of_inserts", 0.20)
        fragment_size = request.POST.get("fragment_size", 10)
        bind_borders = request.POST.get("bind_borders", "off") == "on"
        code_count = request.POST.get("code_count", 1)

        # Валидация данных
        err_msg = ""
        try:
            if not base_textlist_id or not other_textlist_id:
                err_msg = "Выберите оба списка текстов"
            elif base_textlist_id == other_textlist_id:
                err_msg = "Списки текстов должны различаться"
            else:
                base_textlist = TblTextListDescription.get_item(request.user, int(base_textlist_id))
                other_textlist = TblTextListDescription.get_item(request.user, int(other_textlist_id))

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
            messages.error(request, err_msg)
            return render(request, "text_generator/form.html", context={
                "text_lists": text_lists,
                "mode": mode,
                "percent_of_inserts": percent_of_inserts,
                "fragment_size": fragment_size,
                "code_count": code_count,
                "bind_borders": bind_borders,
            })

        # Логика генерации
        codes = []
        try:
            for _ in range(code_count):
                # Получаем связанные тексты через TblTextListItems
                base_text_items = base_textlist.items
                other_text_items = other_textlist.items

                if not base_text_items or not other_text_items:
                    raise ValueError("Один из списков текстов пуст")

                # Выбираем тексты
                if random_texts:
                    base_text_item = random.choice(base_text_items)
                    other_text_item = random.choice(other_text_items)
                else:
                    base_text_item = next(item for item in base_text_items if str(item.text.id) == base_text_id)
                    other_text_item = next(item for item in other_text_items if str(item.text.id) == other_text_id)

                # Получаем содержимое текстов
                base_content = base_text_item.get_content()
                other_content = other_text_item.get_content()

                # Разбиваем тексты на слова
                base_words = base_content.split()
                other_words = other_content.split()

                base_text_length = len(base_words)
                other_text_length = len(other_words)

                # Генерируем код
                code = generate_text_code(
                    base_id=base_text_item.text.id,
                    other_id=other_text_item.text.id,
                    base_length=base_text_length,
                    other_length=other_text_length,
                    fragment_size=fragment_size,
                    percent_of_inserts=percent_of_inserts,
                    bind_borders=bind_borders,
                    base_text=base_content if bind_borders else None,
                    other_text=other_content if bind_borders else None
                )

                if action == "generate_text":
                    # Генерируем текст
                    generated_text = generate_text_by_code(code, base_content, other_content)
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
            messages.error(request, f"Ошибка при генерации: {str(e)}")
            return render(request, "text_generator/form.html", context={
                "text_lists": text_lists,
                "mode": mode,
                "percent_of_inserts": percent_of_inserts,
                "fragment_size": fragment_size,
                "code_count": code_count,
                "bind_borders": bind_borders,
            })

    elif mode == 'byCode':
        if request.method == "GET":
            # Отображаем форму для генерации по коду
            return render(request, "text_generator/form_by_code.html", context={
                "mode": mode,
            })

        # Обработка POST-запроса для режима "По коду"
        code = request.POST.get("code", "").strip()
        if not code:
            messages.error(request, "Введите код для генерации")
            return render(request, "text_generator/form_by_code.html", context={
                "mode": mode,
            })

        try:
            # Парсим код
            parsed = parse_code(code)
            if not parsed:
                raise ValueError("Неверный формат кода")

            # Получаем тексты по ID
            base_text_item = TblTextListDescription.get_text_by_id(request.user, parsed["id1"])
            other_text_item = TblTextListDescription.get_text_by_id(request.user, parsed["id2"])

            if not base_text_item or not other_text_item:
                raise ValueError("Один из текстов не найден")

            base_content = base_text_item.get_content()
            other_content = other_text_item.get_content()

            # Генерируем текст
            generated_text = generate_text_by_code(code, base_content, other_content)

            return render(request, "text_generator/result.html", context={
                "codes": [{
                    'code': code,
                    'generated_text': generated_text,
                    'base_text_item': base_text_item,
                    'other_text_item': other_text_item,
                }],
                "mode": mode,
                "action": "generate_text_by_code",
            })

        except Exception as e:
            messages.error(request, f"Ошибка при генерации: {str(e)}")
            return render(request, "text_generator/form_by_code.html", context={
                "mode": mode,
            })