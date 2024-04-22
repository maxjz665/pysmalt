"""
Обработка запросов к деревьям решений
"""
from django.db.models import Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, redirect
from sklearn import tree

from research.r_tree_app.models.tbl_tree_description import TblTreeDescription
from text_app.models.tbl_textlist import TblTextListDescription
from text_app.models.tbl_word import TblWord


def tree_list(request: HttpRequest) -> HttpResponse:
    """
    Получение списка деревьев решений
    """
    items = TblTreeDescription.objects.filter(is_deleted=False).filter(Q(public=True) | Q(owner=request.user))
    return render(request, "r_tree_app/tree_list.html", context={"items": items})


def add_list(request: HttpRequest) -> HttpResponse:
    """
    Форма добавления/добавление нового дерева решений
    """
    if not request.user.is_authenticated or (request.user.researcher == 0 and not request.user.has_admin):
        print(request.user.researcher)
        return render(request, "not_found.html", context={"message": "Нет прав на добавление дерева решений",
                                                          "return_url": "r_tree_app/tree_list",
                                                          "return_name": "К списку деревьев решений"})

    input_name = request.POST.get("input_name", "Дерево решений")
    first_list = request.POST.get("first_list", 0)
    second_list = request.POST.get("second_list", 0)
    block_size = request.POST.get("block_size", 200)
    lists = TblTextListDescription.objects.filter(Q(public=True) | Q(owner=request.user))

    print(first_list, second_list)

    if request.method == "GET":
        return render(request, "r_tree_app/add_list.html", context={"lists": lists, "input_name": input_name,
                                                                    'first_list': first_list,
                                                                    'second_list': second_list,
                                                                    'block_size': block_size})
    err_msg = ""

    if input_name == "":
        err_msg = "Введите название дерева решений"
    if first_list == "" or second_list == "":
        err_msg = "Выберите списки текстов"
    if first_list == second_list:
        err_msg = "Списки текстов должны различаться"
    try:
        block_size = int(block_size)
        if block_size <= 0:
            raise ValueError
    except ValueError:
        err_msg = "Размер блока должен быть целым положительным числом"

    if err_msg:
        return render(request, "r_tree_app/add_list.html", context={"lists": lists, "input_name": input_name,
                                                                    'first_list': first_list,
                                                                    'second_list': second_list,
                                                                    'block_size': block_size,
                                                                    "error_message": err_msg})

    try:
        item = TblTreeDescription(name=input_name, owner=request.user, block_size=block_size,
                                  first_list=TblTextListDescription.objects.get(id=first_list),
                                  second_list=TblTextListDescription.objects.get(id=second_list))
        item.save()
        return redirect("r_tree_app/tree_list")
    except Exception as e:
        return render(request, "r_tree_app/add_list.html", context={"lists": lists, "input_name": input_name,
                                                                    'first_list': first_list,
                                                                    'second_list': second_list,
                                                                    'block_size': block_size,
                                                                    "error_message": e})


def _generate_table(text_list: TblTextListDescription, block_size: int, dict_size: int) -> []:
    """
    Генерация таблицы признаков по блокам текстов
    :param text_list: список текстов
    :param block_size: размер блока
    :return: таблица частот встречаемости частей речи в блоках текста
    """
    word_index = 0
    ret = []  # матрица переходов по блокам текста
    ret_item = [0] * dict_size * dict_size  # найденные переходы в текущем блоке текста
    for text in text_list.items:  # бежим по текстам и вытаскиваем слова из текста
        text_data = TblWord.objects.filter(text_id=text.text.id).order_by("chapter_index",
                                                                          "paragraph_index",
                                                                          "sentence_index",
                                                                          "word_index").all()
        prev_pos = -1  # предыдущая часть речи
        for word in text_data: # бежим по словам, вытаскиваем часть речи и строим таблицу переходов
            part_of_speech = word.dictword.param_01
            if part_of_speech < 0:  # если битая часть речи, то пропускаем
                prev_pos = -1
                continue
            if prev_pos < 0:  # если это первое слово в биграмме, то запоминаем его
                prev_pos = part_of_speech
                continue
            ret_item[prev_pos * dict_size + part_of_speech] += 1
            word_index += 1
            if word_index >= block_size:
                ret.append(ret_item)
                ret_item = [0] * dict_size * dict_size

                word_index = 0
    return ret


def show_list(request: HttpRequest, list_id) -> HttpResponse:
    """
    Отображение дерева решений
    """
    list_data = TblTreeDescription.objects.get(id=list_id)
    if list_data is None or (list_data.public == 0 and (not request.user.is_authenticated or
                                                        (
                                                                request.user.id != list_data.owner.id and not request.user.has_admin))):
        render(request, "not_found.html", context={
            "message": "Нет прав на просмотр дерева решений",
            "return_url": "r_tree_app/tree_list",
            "return_name": "К списку деревьев решений"
        })
    first_texts = list_data.first_list.items
    second_texts = list_data.second_list.items

    if request.method == "GET":
        return render(request, "r_tree_app/list_data.html", context={"content": list_data,
                                                                     "first_texts": first_texts,
                                                                     "second_texts": second_texts})

    action = request.POST.get("action")
    if action == "recalc":
        # перестраиваем дерево решений
        table1 = _generate_table(list_data.first_list, list_data.block_size, 23)
        table2 = _generate_table(list_data.second_list, list_data.block_size, 23)
        min_size = min(len(table1), len(table2))
        table1 = table1[:min_size]
        table2 = table2[:min_size]
        print(len(table1), len(table2))
        result = [0] * min_size + [1] * min_size
        clf = tree.DecisionTreeClassifier()
        clf = clf.fit(table1 + table2, result)
        tree.plot_tree(clf)
        pass

    return render(request, "r_tree_app/list_data.html",
                  context={"error_message": "Неизвестная операция над деревом решений",
                           "content": list_data,
                           "first_texts": first_texts,
                           "second_texts": second_texts})
