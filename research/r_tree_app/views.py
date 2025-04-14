"""
Обработка запросов к деревьям решений
"""
import asyncio
import json

from aiomqtt import Client
from django.db.models import Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, redirect
import graphviz

from research.r_tree_app.models.tbl_tree_description import TblTreeDescription
from research.r_tree_app.utils import get_pos
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


def add_list(request: HttpRequest) -> HttpResponse:
    """
    Форма добавления/добавление нового дерева решений
    """
    if not request.user.is_authenticated or (request.user.researcher == 0 and not request.user.has_admin):
        return render(request, "not_found.html", context={"message": "Нет прав на добавление дерева решений",
                                                          "return_url": "r_tree_app/tree_list",
                                                          "return_name": "К списку деревьев решений"})

    input_name = request.POST.get("input_name", "Дерево решений")
    first_list = request.POST.get("first_list", 0)
    second_list = request.POST.get("second_list", 0)
    block_size = request.POST.get("block_size", 200)
    lists = TblTextListDescription.get_items(request.user).order_by("name").all()

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
                                  first_list=TblTextListDescription.get_item(request.user, first_list),
                                  second_list=TblTextListDescription.get_item(request.user, second_list),
                                  created_by=request.user.id, updated_by=request.user.id)
        item.save()
        return redirect("r_tree_app/tree_list")
    except Exception as e:
        return render(request, "r_tree_app/add_list.html", context={"lists": lists, "input_name": input_name,
                                                                    'first_list': first_list,
                                                                    'second_list': second_list,
                                                                    'block_size': block_size,
                                                                    "error_message": e})


async def send_broker_message(list_id: int):
    async with Client(BROKER_HOST, BROKER_PORT, identifier="django_" + str(list_id)) as client:
        await client.publish("service/tree_worker/build", json.dumps({"project_id": list_id}))
    pass


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
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        task = loop.create_task(send_broker_message(list_id))
        loop.run_until_complete(asyncio.gather(task))
        loop.close()
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
    if list_data is None or (list_data.public == 0 and (not request.user.is_authenticated or
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
    dict_size = len(pos)
    ret = []
    for i in range(parts):  # делим текст на блоки и бежим по блокам
        data = content[i * part_size: (i + 1) * part_size]
        ret_item = [0] * dict_size * dict_size  # найденные переходы в текущем блоке текста
        prev_pos = -1  # предыдущая часть речи
        for word in data:  # для каждого блока вычисляем вектор N-грамм
            part_of_speech = word.dictword.param_01
            if part_of_speech < 0:  # если битая часть речи, то пропускаем
                prev_pos = -1
                continue
            if prev_pos < 0:  # если это первое слово в N-грамме, то запоминаем его
                prev_pos = part_of_speech
                continue
            ret_item[prev_pos * dict_size + part_of_speech] += 1

        # обработка вектора деревом решений
        result = clf.predict_proba([ret_item])
        ret.append({"start": i*part_size, "end": (i+1)*part_size, "pros": result[0][0], "cons": result[0][1]})

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
                                                             "percentCons": percent_cons})
