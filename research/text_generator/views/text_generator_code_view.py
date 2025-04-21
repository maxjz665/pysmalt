import logging

from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from research.text_generator.dataclasses import *
from research.text_generator.utils import parse_code, generate_text_by_code, export_text, export_parsing
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

    try:
        if not code:
            raise ValueError("Введите код для генерации")
        
        parsed = parse_code(code)
        if not parsed:
            raise ValueError("Неверный формат кода")

        base_text_item = TblTextListDescription.get_text_by_id(request.user, parsed["id1"])
        other_text_item = TblTextListDescription.get_text_by_id(request.user, parsed["id2"])

        if not base_text_item or not other_text_item:
            raise ValueError("Один из текстов не найден")

        # Преобразуем в TextContent
        base_content = TextContent.from_tbl_text(base_text_item) 
        other_content = TextContent.from_tbl_text(other_text_item)

        # Генерируем текст по коду
        generated_text = generate_text_by_code(code, base_content.words, other_content.words)
        
        ##### Обработка экспорта 
        if action in ['export_text', 'export_parsing']:
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