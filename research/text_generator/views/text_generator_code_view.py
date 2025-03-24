import logging
from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from research.text_generator.dataclasses import TextWord
from research.text_generator.utils import parse_code, generate_text_by_code
from text_app.models.tbl_textlist import TblTextListDescription

logger = logging.getLogger(__name__)

def text_generator_code_view(request: HttpRequest) -> HttpResponse:
    """Представление для генерации текстов по коду."""
    mode = 'byCode'
    
    if request.method == "GET":
        return render(request, "text_generator/form_by_code.html", context={
            "mode": mode,
        })

    code = request.POST.get("code", "").strip()
    action = request.POST.get('action')
    
    if not code:
        messages.error(request, "Введите код для генерации")
        return render(request, "text_generator/form_by_code.html", context={
            "mode": mode,
        })

    try:
        parsed = parse_code(code)
        if not parsed:
            raise ValueError("Неверный формат кода")

        base_text_item = TblTextListDescription.get_text_by_id(request.user, parsed["id1"])
        other_text_item = TblTextListDescription.get_text_by_id(request.user, parsed["id2"])

        if not base_text_item or not other_text_item:
            raise ValueError("Один из текстов не найден")

        # Создаем объекты TextWord
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

        # Генерируем текст
        generated_text = generate_text_by_code(code, base_words, other_words)

        return render(request, "text_generator/result.html", context={
            "codes": [{
                'code': code,
                'generated_text': generated_text if action == "generate_text" else None,
                'base_text_item': base_text_item,
                'other_text_item': other_text_item,
            }],
            "mode": mode,
            "action": action,
        })

    except Exception as e:
        logger.exception("Ошибка при генерации текста")
        messages.error(request, f"Ошибка при генерации: {str(e)}")
        return render(request, "text_generator/form_by_code.html", context={
            "mode": mode,
        })