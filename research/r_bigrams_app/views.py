"""
Обработки запросов к биграммам
"""
import asyncio
import json

from aiomqtt import Client
from django.db.models import Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, redirect

from research.r_bigrams_app.models.tbl_bigram_dataset import TblBigramDataset
from shower.settings import BROKER_HOST, BROKER_PORT
from text_app.models.tbl_textlist import TblTextListDescription


def dataset_list(request: HttpRequest) -> HttpResponse:
    """
    Получение списка датасетов
    """
    items = TblBigramDataset.objects.filter(is_deleted=False)
    print(len(items))
    if request.user.is_authenticated:
        items = items.filter(Q(is_public=True) | Q(owner__id=request.user.id))
    else:
        items = items.filter(is_public=True)
    print(len(items))
    return render(request, "r_bigrams_app/dataset_list.html", context={"items": items})


def dataset_add_list(request: HttpRequest) -> HttpResponse:
    """
    Форма добавления/добавление нового датасета
    """
    if not request.user.is_authenticated or (request.user.researcher == 0 and not request.user.has_admin):
        return render(request, "not_found.html", context={"message": "Нет прав на добавление датасета биграмм",
                                                          "return_url": "r_bigrams_app/dataset_list",
                                                          "return_name": "К списку датасетов биграмм"})

    input_name = request.POST.get("input_name", "Датасет биграмм")
    max_bigrams = request.POST.get("max_bigrams", 100)
    min_occurrence = request.POST.get("min_occurrence", 1)
    text_group = request.POST.get("text_group", 0)
    is_use_initial = request.POST.get("is_use_initial", False)
    is_sentence_split = request.POST.get("is_sentence_split", True)
    lists = TblTextListDescription.objects.filter(Q(public=True) | Q(owner=request.user))

    if request.method == "GET":
        return render(request, "r_bigrams_app/add_list.html", context={"lists": lists, "input_name": input_name,
                                                                       'max_bigrams': max_bigrams,
                                                                       'min_occurrence': min_occurrence,
                                                                       'text_group': text_group,
                                                                       'is_use_initial': is_use_initial,
                                                                       'is_sentence_split': is_sentence_split})
    # проверка входных данных
    error_msg = ""
    if input_name == "":
        error_msg = "Введите название датасета биграмм"
    try:
        max_bigrams = int(max_bigrams)
        if max_bigrams <= 0:
            raise ValueError
    except ValueError:
        error_msg = "Максимальное число биграмм в датасете должно быть целым положительным числом"

    try:
        min_occurrence = int(min_occurrence)
        if min_occurrence < 0:
            raise ValueError
    except ValueError:
        error_msg = "Минимальное количество встречаемости биграммы должно быть целым неотрицательным числом"

    if error_msg:
        return render(request, "r_bigrams_app/add_list.html", context={"lists": lists, "input_name": input_name,
                                                                       'max_bigrams': max_bigrams,
                                                                       'min_occurrence': min_occurrence,
                                                                       'text_group': text_group,
                                                                       'is_use_initial': is_use_initial,
                                                                       'is_sentence_split': is_sentence_split,
                      "error_message": error_msg})

    try:
        item = TblBigramDataset(name=input_name, max_bigrams=max_bigrams, min_occurrence=min_occurrence, is_use_initial=(True if is_use_initial == "on" else False),
                                is_sentence_split=(True if is_sentence_split == "on" else False), owner=request.user, created_by=request.user.id, updated_by=request.user.id)
        if int(text_group) != 0:
            item.text_group = TblTextListDescription.objects.get(id=text_group)
        item.save()
        return redirect("r_bigrams_app/dataset_list")
    except Exception as e:
        return render(request, "r_bigrams_app/add_list.html", context={"lists": lists, "input_name": input_name,
                                                                       'max_bigrams': max_bigrams,
                                                                       'min_occurrence': min_occurrence,
                                                                       'text_group': text_group,
                                                                       'is_use_initial': is_use_initial,
                                                                       'is_sentence_split': is_sentence_split,
                      "error_message": e})


def dataset_show_list(request: HttpRequest, list_id: int) -> HttpResponse:
    dataset_data = TblBigramDataset.objects.get(id=list_id)
    if dataset_data is None or (dataset_data.is_public == 0 and (not request.user.is_authenticated or
                                                        (request.user.id != dataset_data.owner.id and not request.user.has_admin))):
        return render(request, "not_found.html", context={
            "message": "Нет прав на просмотр датасета биграмм",
            "return_url": "r_bigrams_app/dataset_list",
            "return_name": "К списку датасетов"
        })


    if request.method == "GET":
        return render(request, "r_bigrams_app/dataset_data.html", context={"content": dataset_data})

    action = request.POST.get("action", "")
    if action == "recalc":
        # Обнуление даты генерации дерева и отправка задачи в брокер
        if dataset_data.build_at is None and not request.user.has_admin:
            return render(request, "r_bigrams_app/dataset_data.html", context={"content": dataset_data,
                                                                         "error_message": "Датасет в процессе построения"})
        dataset_data.build_at = None
        dataset_data.build_status = "В очереди"
        dataset_data.save()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        task = loop.create_task(send_broker_message(list_id))
        loop.run_until_complete(asyncio.gather(task))
        loop.close()
        return render(request, "r_bigrams_app/dataset_data.html", context={"content": dataset_data,
                                                                     "success_message": "Запущена задача построения датасета"})

    return render(request, "r_bigrams_app/dataset_data.html",
                  context={"error_message": "Неизвестная операция над деревом решений",
                           "content": dataset_data})

async def send_broker_message(list_id: int):
    async with Client(BROKER_HOST, BROKER_PORT, identifier="django_" + str(list_id)) as client:
        await client.publish("service/bigrams_worker/build", json.dumps({"project_id": list_id}))
    pass


def check_text(request):
    return None