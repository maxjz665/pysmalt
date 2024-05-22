"""
Обработка запросов к деревьям решений
"""
import asyncio
import json

from aiomqtt import Client
from django.db.models import Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, redirect

from research.r_tree_app.models.tbl_tree_description import TblTreeDescription
from shower.settings import BROKER_HOST, BROKER_PORT
from text_app.models.tbl_textlist import TblTextListDescription


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
                                  second_list=TblTextListDescription.objects.get(id=second_list),
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

    action = request.POST.get("action", "")
    if action == "recalc":
        # Обнуление даты генерации дерева и отправка задачи в брокер
        if list_data.build_at is None and not request.user.has_admin:
            return render(request, "r_tree_app/list_data.html", context={"content": list_data,
                                                                     "first_texts": first_texts,
                                                                     "second_texts": second_texts,
                                                                     "error_message": "Дерево в прцессе построения"})
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

    return render(request, "r_tree_app/list_data.html",
                  context={"error_message": "Неизвестная операция над деревом решений",
                           "content": list_data,
                           "first_texts": first_texts,
                           "second_texts": second_texts})
