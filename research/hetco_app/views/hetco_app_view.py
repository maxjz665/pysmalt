from django.http import HttpResponse, HttpRequest, FileResponse
from django.shortcuts import render

from research.hetco_app.utils import HetcoUtils, WordData
from research.text_generator.dataclasses import TextContent, GeneratedWord
from research.text_generator.utils import parse_code, generate_text_by_code
from text_app.models.tbl_textlist import TblTextListDescription


def hetco_app_view(request: HttpRequest) -> HttpResponse:
    """Форма анализа метрик Хетсо."""
    if request.method == "GET":
        text_lists = TblTextListDescription.get_items(request.user).order_by("name")
        return render(request, "hetco_app/hetco_app_form.html", {
            "text_lists": text_lists
        })
    
    # POST запрос
    source_type = request.POST.get("source_type")
    other_list_id = int(request.POST.get("other_list", 0))
    
    if not other_list_id:
        return HttpResponse("Выберите список для сравнения", status=400)

    # Получаем список для сравнения
    other_list = TblTextListDescription.get_item(request.user, other_list_id)
    if not other_list:
        return HttpResponse("Список для сравнения не найден", status=404)


    words = None
    text_name = "Generated Text"

    try:
        if source_type == "code":
            # Обработка через код генерации
            code = request.POST.get("code_input", "").strip()
            if not code:
                return HttpResponse("Введите код генерации", status=400)

            # Парсим код
            parsed = parse_code(code)
            if not parsed:
                return HttpResponse("Неверный формат кода", status=400)

            # Получаем тексты из кода
            base_text = TblTextListDescription.get_text_by_id(request.user, parsed["id1"])
            other_text = TblTextListDescription.get_text_by_id(request.user, parsed["id2"])

            if not base_text or not other_text:
                return HttpResponse("Тексты из кода не найдены", status=404)

            # Генерируем текст по коду
            base_content = TextContent.from_tbl_text(base_text)
            other_content = TextContent.from_tbl_text(other_text)
            generated_words = generate_text_by_code(code, base_content.words, other_content.words)
            # Преобразуем слова в WordData
            words = [WordData.from_generated_word(w) for w in generated_words]
        else:
            # Обработка готового текста
            text_list_id = int(request.POST.get("text_list", 0))
            text_id = int(request.POST.get("text_id", 0))
            
            if not text_list_id:
                return HttpResponse("Выберите список текстов", status=400)
            if not text_id:
                return HttpResponse("Выберите текст для анализа", status=400)

            text = TblTextListDescription.get_text_by_id(request.user, text_id)
            if not text:
                return HttpResponse("Текст не найден", status=404)

            # Получаем слова в формате WordData 
            words = WordData.from_tbl_words(text_id)
            text_name = text.text.title

        if not words:
            return HttpResponse("Ошибка получения текста", status=500)

        # Создаем экземпляр HetcoUtils
        hetco = HetcoUtils(words, other_list, other_list.name, text_name)
        # Выполняем анализ
        table9 = hetco.process_point_9()
        alpha10 = hetco.process_point_10()
        table11 = hetco.process_point_11()
        alpha12 = hetco.process_point_12()
        ld13 = hetco.process_point_13()
        ld14 = hetco.process_point_14()
        res15 = hetco.process_point_15()
        ld13m = hetco.process_point_13mod()
        ld14m = hetco.process_point_14mod()
        res15m = hetco.process_point_15mod()

        # Записываем результаты в Excel
        excel_data = hetco.write_to_excel(table9, alpha10, table11, alpha12,
                                       ld13, ld14, res15, ld13m, ld14m, res15m)

        response = HttpResponse(
            excel_data,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="hetco-{other_list.name}.xlsx"'
        return response

    except Exception as e:
        return HttpResponse(f"Ошибка при обработке: {str(e)}", status=500)