"""
Обработка запросов к деревьям решений
"""
import asyncio
import json
import time
from datetime import datetime

from aiomqtt import Client
from django.db.models import Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, redirect
import graphviz

from research.r_tree_app.models.tbl_tree_description import TblTreeDescription
from research.r_tree_app.utils import get_pos, generate_subslice, fix_pos
from shower.settings import BROKER_HOST, BROKER_PORT
from text_app.models.tbl_text import TblText
from text_app.models.tbl_textlist import TblTextListDescription
from text_app.models.tbl_word import TblWord


def tree_list(request: HttpRequest) -> HttpResponse:
    """
    Получение списка деревьев решений
    """
    items = TblTreeDescription.objects.filter(is_deleted=False)
    if request.user.is_authenticated:
        items = items.filter(Q(public=True) | Q(owner__id=request.user.id))
    else:
        items = items.filter(public=True)
    return render(request, "r_tree_app/tree_list.html", context={"items": items})

def _check_form(input_name, sector_size, block_size, max_depth, first_list, second_list, is_need_uno, is_need_duo) -> str:
    """
    Проверка данных формы (для добавления и изменения)
    """
    msg = ""

    if input_name == "":
        err_msg = "Введите название дерева решений"
    try:
        sector_size = float(sector_size)
        if sector_size < 0 or sector_size > 100:
            raise ValueError
    except ValueError:
        err_msg = "Размер сектора должен быть в пределах 0-100"
    try:
        block_size = int(block_size)
        if block_size <= 0:
            raise ValueError
    except ValueError:
        err_msg = "Размер блока должен быть целым положительным числом"

    try:
        max_depth = int(max_depth)
        if max_depth <= 0:
            raise ValueError
    except ValueError:
        err_msg =  "Глубина дерева решений должна быть целым положительным числом"

    try:
        first_list = int(first_list)
        if first_list <= 0:
            raise ValueError
    except ValueError:
        err_msg = "Выберите список текстов первой группы"

    try:
        second_list = int(second_list)
        if second_list <= 0:
            raise ValueError
    except ValueError:
        err_msg = "Выберите список текстов второй группы"

    if first_list == second_list:
        err_msg = "Списки текстов должны различаться"

    if not is_need_uno and not is_need_duo and sector_size == 0:
        err_msg = "Выберите один из типов деревьев"

    return msg

def add_list(request: HttpRequest) -> HttpResponse:
    """
    GET Форма добавления/ POST добавление нового дерева решений
    """
    if not request.user.is_authenticated or (request.user.researcher == 0 and not request.user.has_admin):
        return render(request, "not_found.html", context={"message": "Нет прав на добавление дерева решений",
                                                          "return_url": "r_tree_app/tree_list",
                                                          "return_name": "К списку деревьев решений"})

    pos = get_pos()

    input_name = request.POST.get("input_name", "Дерево решений")
    first_list = request.POST.get("first_list", 0)
    second_list = request.POST.get("second_list", 0)
    is_need_uno = request.POST.get("is_need_uno", False)
    is_need_duo = request.POST.get("is_need_duo", False)
    block_size = request.POST.get("block_size", 200)
    removed_pos = request.POST.getlist("removed_pos", [])
    max_depth = request.POST.get("max_depth", 4)
    sector_size = request.POST.get("sector_size", 0)
    many_sectors = request.POST.get("many_sectors", False)
    lists = TblTextListDescription.get_items(request.user).order_by("name").all()

    try:  # прилетают текстовые значения, конвертируем в числа.
        removed_pos = list(map(int, removed_pos))
    except ValueError:
        removed_pos = []

    if request.method == "GET":
        return render(request, "r_tree_app/add_list.html", context={"lists": lists, "input_name": input_name,
                                                                    'first_list': first_list,
                                                                    'second_list': second_list,
                                                                    'block_size': block_size,
                                                                    'pos': pos,
                                                                    'removed_pos': removed_pos,
                                                                    'max_depth': max_depth,
                                                                    'is_need_uno': is_need_uno,
                                                                    'is_need_duo': is_need_duo,
                                                                    'sector_size': sector_size,
                                                                    'many_sectors': many_sectors})
    err_msg = _check_form(input_name, sector_size, block_size, max_depth, first_list, second_list, is_need_uno, is_need_duo)


    if err_msg:
        return render(request, "r_tree_app/add_list.html", context={"lists": lists, "input_name": input_name,
                                                                    'first_list': first_list,
                                                                    'second_list': second_list,
                                                                    'block_size': block_size,
                                                                    'pos': pos,
                                                                    'removed_pos': removed_pos,
                                                                    'max_depth': max_depth,
                                                                    'is_need_uno': is_need_uno,
                                                                    'is_need_duo': is_need_duo,
                                                                    'sector_size': sector_size,
                                                                    'many_sectors': many_sectors,
                                                                    "error_message": err_msg})

    try:
        item = TblTreeDescription(name=input_name, owner=request.user, block_size=int(block_size),
                                  max_depth=int(max_depth), removed_pos=json.dumps(removed_pos),
                                  is_need_uno=(is_need_uno == "on"), is_need_duo=(is_need_duo == "on"),
                                  sector_size=float(sector_size), many_sectors=(many_sectors == "on"),
                                  is_need_separate=(0 < int(sector_size) < 100),
                                  first_list=TblTextListDescription.get_item(request.user, int(first_list)),
                                  second_list=TblTextListDescription.get_item(request.user, int(second_list)),
                                  created_by=request.user.id, updated_by=request.user.id)
        item.save()
        return redirect("r_tree_app/tree_list")
    except Exception as e:
        return render(request, "r_tree_app/add_list.html", context={"lists": lists, "input_name": input_name,
                                                                    'first_list': first_list,
                                                                    'second_list': second_list,
                                                                    'block_size': block_size,
                                                                    'pos': pos,
                                                                    'removed_pos': removed_pos,
                                                                    'max_depth': max_depth,
                                                                    'is_need_uno': is_need_uno,
                                                                    'is_need_duo': is_need_duo,
                                                                    'sector_size': sector_size,
                                                                    'many_sectors': many_sectors,
                                                                    "error_message": e})


def show_list(request: HttpRequest, list_id) -> HttpResponse:
    """
    Отображение дерева решений
    """
    list_data = TblTreeDescription.objects.get(id=list_id)
    if list_data is None or (list_data.public == 0 and (not request.user.is_authenticated or
                                                        (request.user.id != list_data.owner.id and not request.user.has_admin))):
        return render(request, "not_found.html", context={
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

    action = request.POST.get("action", "")
    if action == "recalc":
        # Обнуление даты генерации дерева и отправка задачи в брокер
        if list_data.build_at is None and not request.user.has_admin:
            return render(request, "r_tree_app/list_data.html", context={"content": list_data,
                                                                     "first_texts": first_texts,
                                                                     "second_texts": second_texts,
                                                                     "error_message": "Дерево в процессе построения"})
        list_data.build_at = None
        list_data.build_status = "В очереди"
        list_data.save()
        return render(request, "r_tree_app/list_data.html", context={"content": list_data,
                                                                     "first_texts": first_texts,
                                                                     "second_texts": second_texts,
                                                                     "success_message": "Запущена задача построения дерева"})
    if action == "publish":
        if request.user.is_authenticated and (request.user == list_data.owner or request.user.has_admin):
            list_data.public = True
            list_data.save()
            return render(request, "r_tree_app/list_data.html", context={"content": list_data,
                                                                              "first_texts": first_texts,
                                                                              "second_texts": second_texts,
                                                                              "success_message": "Дерево опубликовано"})
        return render(request, "r_tree_app/list_data.html", context={"content": list_data,
                                                                          "first_texts": first_texts,
                                                                          "second_texts": second_texts,
                                                                          "error_message": "Нет прав на управление деревом"})

    if action == "unpublish":
        if request.user.is_authenticated and (request.user == list_data.owner or request.user.has_admin):
            list_data.public = False
            list_data.save()
            return render(request, "r_tree_app/list_data.html", context={"content": list_data,
                                                                              "first_texts": first_texts,
                                                                              "second_texts": second_texts,
                                                                              "success_message": "Дерево снято с публикации"})
        return render(request, "r_tree_app/list_data.html", context={"content": list_data,
                                                                          "first_texts": first_texts,
                                                                          "second_texts": second_texts,
                                                                          "error_message": "Нет прав на управление деревом"})

    if action == "delete":
        if request.user.is_authenticated and (request.user == list_data.owner or request.user.has_admin):
            list_data.is_deleted = True
            list_data.save()
            return redirect("r_tree_app/tree_list")
        return render(request, "r_tree_app/list_data.html", context={"content": list_data,
                                                                 "first_texts": first_texts,
                                                                 "second_texts": second_texts,
                                                                 "error_message": "Нет прав на управление деревом"})

    if action == "restore":
        if request.user.is_authenticated and (request.user == list_data.owner or request.user.has_admin):
            list_data.is_deleted = False
            list_data.save()
            return render(request, "r_tree_app/list_data.html", context={"content": list_data,
                                                                 "first_texts": first_texts,
                                                                 "second_texts": second_texts})
        return render(request, "r_tree_app/list_data.html", context={"content": list_data,
                                                                 "first_texts": first_texts,
                                                                 "second_texts": second_texts,
                                                                 "error_message": "Нет прав на управление деревом"})
    return render(request, "r_tree_app/list_data.html",
                  context={"error_message": "Неизвестная операция над деревом решений",
                           "content": list_data,
                           "first_texts": first_texts,
                           "second_texts": second_texts})


def get_graph(request: HttpRequest, list_id) -> HttpResponse:
    """
    Получение картинки графа дерева решений
    """
    list_data = TblTreeDescription.objects.get(id=list_id)
    if list_data is None or (list_data.public == 0 and (not request.user.is_authenticated or
                                                        (request.user.id != list_data.owner.id and not request.user.has_admin))):
        return render(request, "not_found.html", context={
            "message": "Нет прав на просмотр дерева решений",
            "return_url": "r_tree_app/tree_list",
            "return_name": "К списку деревьев решений"
        })
    graph = graphviz.Source(list_data.graph_dot)
    return HttpResponse(graph.pipe(format='svg', encoding='utf-8'), content_type="image/svg+xml")


def check_text(request: HttpRequest, list_id):
    """
    Проверка текста в дереве решений
    """
    list_data = TblTreeDescription.objects.get(id=list_id)
    if list_data is None or list_data.is_deleted or (list_data.public == 0 and (not request.user.is_authenticated or
                                                        (request.user.id != list_data.owner.id and not request.user.has_admin))):
        render(request, "not_found.html", context={
            "message": "Нет прав на просмотр дерева решений",
            "return_url": "r_tree_app/tree_list",
            "return_name": "К списку деревьев решений"
        })

    texts = TblText.get_texts(request.user)
    paper_id = request.POST.get("selectionTextId", None)
    if paper_id is not None:
        paper_id = int(paper_id)
        paper = texts.get(id=paper_id)
    else:
        paper = None

    if request.method == "GET":
        # выдаем форму для GET запроса
        return render(request, "r_tree_app/check.html", context={"content": list_data, "texts": texts,
                                                                 "link": "text_app/papers_data",
                                                                 "selectionTextId": paper_id})

    # получаем текст и разбиваем его на блоки
    content = TblWord.objects.filter(text_id=paper_id).order_by("chapter_index",
                                                                "paragraph_index",
                                                                "sentence_index",
                                                                "word_index").all()

    clf = list_data.graph_pickle

    part_size = list_data.block_size
    parts = int(len(content) / part_size)
    pos = get_pos()
    removed_pos = json.loads(list_data.removed_pos)
    dict_size = len(pos) - len(removed_pos)
    ret = []
    total_diff = 0 # общее время работы деревьев решений
    for i in range(parts):  # делим текст на блоки и бежим по блокам
        data = content[i * part_size: (i + 1) * part_size]
        if list_data.is_need_uno or list_data.is_need_separate:
            ret_uno_item = [0] * dict_size
        else:
            ret_uno_item = []
        if list_data.is_need_duo:
            ret_duo_item = [0] * dict_size * dict_size # найденные переходы в текущем блоке текста
        else:
            ret_duo_item = []
        prev_pos = -1  # предыдущая часть речи
        for word in data:  # для каждого блока вычисляем вектор N-грамм
            part_of_speech = word.dictword.param_01
            if part_of_speech < 0:  # если битая часть речи, то пропускаем
                prev_pos = -1
                continue
            if prev_pos < 0:  # если это первое слово в N-грамме, то запоминаем его
                prev_pos = part_of_speech
                continue
            if list_data.is_need_uno or list_data.is_need_separate:
                ret_uno_item[fix_pos(part_of_speech, removed_pos)] += 1
            if list_data.is_need_duo:
                ret_duo_item[fix_pos(prev_pos, removed_pos) * dict_size + fix_pos(part_of_speech, removed_pos)] += 1
            prev_pos = part_of_speech

        # построение матрицы поворотов
        if list_data.is_need_separate:
            ret_separate_item = []
            assert 0 < list_data.sector_size < 100
            if list_data.many_sectors:
                n = 1.0
                while list_data.sector_size * n < 100:
                    ret_separate_item.extend(generate_subslice(ret_uno_item, len(ret_uno_item), n * list_data.sector_size))
                    n += 1
            else:
                ret_separate_item = generate_subslice(ret_uno_item, len(ret_uno_item), list_data.sector_size)

            if not list_data.is_need_uno:
                ret_uno_item = []
        else:
            ret_separate_item = []

        # обработка вектора деревом решений
        start = time.time()
        result = clf.predict_proba([[*ret_uno_item, *ret_duo_item, *ret_separate_item]])
        diff = time.time() - start
        total_diff += diff
        ret.append({"start": i*part_size, "end": (i+1)*part_size, "pros": result[0][0], "cons": result[0][1], "time": diff})

    percent_pros = 0
    percent_equal = 0
    percent_cons = 0
    for item in ret:
        if item["pros"] < 0.33:
            percent_cons += 1
        elif item["pros"] < 0.66:
            percent_equal += 1
        else:
            percent_pros += 1

    if len(ret) > 0:
        percent_cons = percent_cons / len(ret) * 100
        percent_pros = percent_pros / len(ret) * 100
        percent_equal = percent_equal / len(ret) * 100
    return render(request, "r_tree_app/check.html", context={"content": list_data, "texts": texts,
                                                             "link": "text_app/papers_data", "selectionTextId": paper_id,
                                                             "paper": paper,
                                                             "text": content, "colormap": ret, "percentPros": percent_pros, "percentEqual": percent_equal,
                                                             "percentCons": percent_cons, "total_diff": total_diff})


def edit_list(request: HttpRequest, list_id):
    """
    Обработка редактирования метаданных дерева решений
    """
    list_data = TblTreeDescription.objects.get(id=list_id)
    if list_data is None or (request.user.id != list_data.owner.id and not request.user.has_admin):
        first_texts = list_data.first_list.items
        second_texts = list_data.second_list.items
        return render(request, "not_found.html", context={
            "message": "Нет прав на редактирование дерева решений",
            "return_url": "r_tree_app/tree_list",
            "return_name": "К списку деревьев решений"
        })

    pos = get_pos()

    input_name = request.POST.get("input_name", list_data.name)
    first_list = request.POST.get("first_list", list_data.first_list.id)
    second_list = request.POST.get("second_list", list_data.second_list.id)
    is_need_uno = request.POST.get("is_need_uno", "on" if list_data.is_need_uno else "")
    is_need_duo = request.POST.get("is_need_duo", "on" if list_data.is_need_duo else "")
    block_size = request.POST.get("block_size", list_data.block_size)
    removed_pos = request.POST.getlist("removed_pos", json.loads(list_data.removed_pos))
    max_depth = request.POST.get("max_depth", list_data.max_depth)
    sector_size = request.POST.get("sector_size", list_data.sector_size)
    many_sectors = request.POST.get("many_sectors", "on" if list_data.many_sectors else "")
    lists = TblTextListDescription.get_items(request.user).order_by("name").all()

    try:  # прилетают текстовые значения, конвертируем в числа.
        removed_pos = list(map(int, removed_pos))
    except ValueError:
        removed_pos = []

    if request.method == "GET":
        return render(request, "r_tree_app/add_list.html", context={"lists": lists, "input_name": input_name,
                                                                    'data': list_data,
                                                                    'first_list': first_list,
                                                                    'second_list': second_list,
                                                                    'block_size': block_size,
                                                                    'pos': pos,
                                                                    'removed_pos': removed_pos,
                                                                    'max_depth': max_depth,
                                                                    'is_need_uno': is_need_uno,
                                                                    'is_need_duo': is_need_duo,
                                                                    'sector_size': sector_size,
                                                                    'many_sectors': many_sectors})

    err_msg = _check_form(input_name, sector_size, block_size, max_depth, first_list, second_list, is_need_uno, is_need_duo)
    if err_msg:
        return render(request, "r_tree_app/add_list.html", context={"lists": lists, "input_name": input_name,
                                                                    'data': list_data,
                                                                    'first_list': first_list,
                                                                    'second_list': second_list,
                                                                    'block_size': block_size,
                                                                    'pos': pos,
                                                                    'removed_pos': removed_pos,
                                                                    'max_depth': max_depth,
                                                                    'is_need_uno': is_need_uno,
                                                                    'is_need_duo': is_need_duo,
                                                                    'sector_size': sector_size,
                                                                    'many_sectors': many_sectors,
                                                                    "error_message": err_msg})

    try:
        list_data.name = input_name
        list_data.block_size = int(block_size)
        list_data.max_depth = int(max_depth)
        list_data.removed_pos = json.dumps(removed_pos)
        list_data.sector_size = float(sector_size)
        list_data.many_sectors = (many_sectors == "on")
        list_data.is_need_uno = (is_need_uno == "on")
        list_data.is_need_duo = (is_need_duo == "on")
        list_data.is_need_separate = (0 < float(sector_size) < 100)
        list_data.first_list = TblTextListDescription.get_item(request.user, int(first_list))
        list_data.second_list=TblTextListDescription.get_item(request.user, int(second_list))
        list_data.updated_by = request.user.id
        list_data.updated_at = datetime.now()
        list_data.clean_calcs()
        list_data.save()
        return redirect("r_tree_app/show_list", list_id)
    except Exception as e:
        return render(request, "r_tree_app/add_list.html", context={"lists": lists, "input_name": input_name,
                                                                    'data': list_data,
                                                                    'first_list': first_list,
                                                                    'second_list': second_list,
                                                                    'block_size': block_size,
                                                                    'pos': pos,
                                                                    'removed_pos': removed_pos,
                                                                    'max_depth': max_depth,
                                                                    'is_need_uno': is_need_uno,
                                                                    'is_need_duo': is_need_duo,
                                                                    'sector_size': sector_size,
                                                                    'many_sectors': many_sectors,
                                                                    "error_message": e})
