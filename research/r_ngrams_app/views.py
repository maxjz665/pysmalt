"""
Обработки запросов к N-граммам
"""
import asyncio
import json

from aiomqtt import Client
from django.db.models import Q, ObjectDoesNotExist
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, redirect

from research.r_ngrams_app.models.tbl_ngram_dataset import TblBigramDataset
from shower.settings import BROKER_HOST, BROKER_PORT
from text_app.models.tbl_text import TblText
from text_app.models.tbl_textlist import TblTextListDescription


def dataset_list(request: HttpRequest) -> HttpResponse:
    """
    Получение списка датасетов
    """
    items = TblBigramDataset.objects.filter(is_deleted=False)
    if request.user.is_authenticated:
        items = items.filter(Q(is_public=True) | Q(owner__id=request.user.id))
    else:
        items = items.filter(is_public=True)
    return render(request, "r_ngrams_app/dataset_list.html", context={"items": items})


def dataset_add_list(request: HttpRequest) -> HttpResponse:
    """
    Форма добавления/добавление нового датасета
    """
    if not request.user.is_authenticated or (request.user.researcher == 0 and not request.user.has_admin):
        return render(request, "not_found.html", context={"message": "Нет прав на добавление датасета N-грамм",
                                                          "return_url": "r_ngrams_app/dataset_list",
                                                          "return_name": "К списку датасетов N-грамм"})

    input_name = request.POST.get("input_name", "Датасет N-грамм")
    max_ngrams = request.POST.get("max_ngrams", 100)
    min_occurrence = request.POST.get("min_occurrence", 1)
    text_group = request.POST.get("text_group", 0)
    ngram_size = request.POST.get("ngram_size", 2)
    is_use_initial = request.POST.get("is_use_initial", False)
    is_sentence_split = request.POST.get("is_sentence_split", True)
    lists = TblTextListDescription.get_items(request.user).order_by("name").all()

    if request.method == "GET":
        return render(request, "r_ngrams_app/add_list.html", context={"lists": lists, "input_name": input_name,
                                                                       'max_ngrams': max_ngrams,
                                                                       'min_occurrence': min_occurrence,
                                                                       'text_group': int(text_group),
                                                                       'is_use_initial': is_use_initial,
                                                                       'ngram_size': ngram_size,
                                                                       'is_sentence_split': is_sentence_split})
    # проверка входных данных
    error_msg = ""
    if input_name == "":
        error_msg = "Введите название датасета N-грамм"
    try:
        max_ngrams = int(max_ngrams)
        if max_ngrams <= 0:
            raise ValueError
    except ValueError:
        error_msg = "Максимальное число N-грамм в датасете должно быть целым положительным числом"

    try:
        min_occurrence = int(min_occurrence)
        if min_occurrence < 0:
            raise ValueError
    except ValueError:
        error_msg = "Минимальное количество встречаемости N-граммы должно быть целым неотрицательным числом"

    try:
        e_ngram_size = int(ngram_size)
        if e_ngram_size <= 0:
            raise ValueError
    except ValueError:
        error_msg = "Размер N-граммы должен быть целым положительным числом"

    if error_msg:
        return render(request, "r_ngrams_app/add_list.html", context={"lists": lists, "input_name": input_name,
                                                                       'max_ngrams': max_ngrams,
                                                                       'min_occurrence': min_occurrence,
                                                                       'text_group': text_group,
                                                                       'is_use_initial': is_use_initial,
                                                                       'ngram_size': ngram_size,
                                                                       'is_sentence_split': is_sentence_split,
                      "error_message": error_msg})

    try:
        item = TblBigramDataset(name=input_name, ngram_size=ngram_size, max_ngrams=max_ngrams, min_occurrence=min_occurrence, is_use_initial=(is_use_initial == "on"),
                                is_sentence_split=(is_sentence_split == "on"), owner=request.user, created_by=request.user.id, updated_by=request.user.id)
        if int(text_group) != 0:
            item.text_group = TblTextListDescription.get_item(request.user, text_group)
        item.save()
        return redirect("r_ngrams_app/dataset_list")
    except Exception as e:
        return render(request, "r_ngrams_app/add_list.html", context={"lists": lists, "input_name": input_name,
                                                                       'max_ngrams': max_ngrams,
                                                                       'min_occurrence': min_occurrence,
                                                                       'text_group': text_group,
                                                                       'ngram_size': ngram_size,
                                                                       'is_use_initial': is_use_initial,
                                                                       'is_sentence_split': is_sentence_split,
                      "error_message": e})


def dataset_show_list(request: HttpRequest, list_id: int) -> HttpResponse:
    """
    Отображение содержимого датасета
    """
    try:
        dataset_data = TblBigramDataset.get_item(request.user, list_id)
    except ObjectDoesNotExist:
        return render(request, "not_found.html", context={
            "message": "Нет прав на просмотр датасета N-грамм",
            "return_url": "r_ngrams_app/dataset_list",
            "return_name": "К списку датасетов"
        })


    if request.method == "GET":
        return render(request, "r_ngrams_app/dataset_data.html", context={"content": dataset_data})

    if not request.user.is_authenticated or (request.user.researcher == 0 and not request.user.has_admin):
        return render(request, "r_ngrams_app/dataset_data.html", context={"content": dataset_data,
                                                                          "error_message": "Нет прав на управление датасетом"})

    action = request.POST.get("action", "")
    if action == "recalc":
        # Обнуление даты генерации дерева и отправка задачи в брокер
        if dataset_data.build_at is None and not request.user.has_admin:
            return render(request, "r_ngrams_app/dataset_data.html", context={"content": dataset_data,
                                                                         "error_message": "Датасет в процессе построения"})
        dataset_data.build_at = None
        dataset_data.build_status = "В очереди"
        dataset_data.save()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        task = loop.create_task(send_broker_message(list_id))
        loop.run_until_complete(asyncio.gather(task))
        loop.close()
        return render(request, "r_ngrams_app/dataset_data.html", context={"content": dataset_data,
                                                                     "success_message": "Запущена задача построения датасета"})
    if action == "publish":
        if request.user.is_authenticated and (request.user == dataset_data.owner or request.user.has_admin):
            dataset_data.is_public = True
            dataset_data.save()
            return render(request, "r_ngrams_app/dataset_data.html", context={"content": dataset_data, "success_message": "Словарь опубликован"})
        return render(request, "r_ngrams_app/dataset_data.html", context={"content": dataset_data,
                                                                              "error_message": "Нет прав на управление датасетом"})

    if action == "unpublish":
        if request.user.is_authenticated and (request.user == dataset_data.owner or request.user.has_admin):
            dataset_data.is_public = False
            dataset_data.save()
            return render(request, "r_ngrams_app/dataset_data.html",
                          context={"content": dataset_data, "success_message": "Словарь снят с публикации"})
        return render(request, "r_ngrams_app/dataset_data.html", context={"content": dataset_data,
                                                                              "error_message": "Нет прав на управление датасетом"})

    return render(request, "r_ngrams_app/dataset_data.html",
                  context={"error_message": "Неизвестная операция над словарем",
                           "content": dataset_data})

async def send_broker_message(list_id: int):
    async with Client(BROKER_HOST, BROKER_PORT, identifier="django_" + str(list_id)) as client:
        await client.publish("service/ngrams_worker/build", json.dumps({"project_id": list_id}))
    pass


def check_text(request, list_id: int) -> HttpResponse:
    try:
        dataset_data = TblBigramDataset.get_item(request.user, list_id)
    except TblBigramDataset.DoesNotExist:
        return render(request, "not_found.html", context={
            "message": "Нет прав на просмотр датасета N-грамм",
            "return_url": "r_ngrams_app/dataset_list",
            "return_name": "К списку датасетов"
        })

    texts = TblText.get_texts(request.user, exclude_deleted=True, exclude_not_verified=True).all()

    if request.method == "GET":
        return render(request, "r_ngrams_app/check_text_form.html", context={"content": dataset_data, 'texts': texts})

    text_id = request.POST.get("text_id", 0)
    block_size = request.POST.get("block_size", 0)

    if text_id == 0 or not text_id.isdigit():
        return render(request, "r_ngrams_app/check_text_form.html", context={"content": dataset_data, 'texts': texts, "error_message": "Выберите текст",
                                                                             "block_size": block_size})

    if block_size == 0 or not block_size.isdigit():
        return render(request, "r_ngrams_app/check_text_form.html", context={"content": dataset_data, 'texts': texts,
                                                                             "error_message": "Размер блока должен быть целым числом больше нуля",
                                                                             'text_id': text_id,
                                                                             'block_size': block_size})

    result, block_result, _ = dataset_data.check_text(text_id, TblText.get_text(request.user, text_id).get_content(), int(block_size))
    return render(request, "r_ngrams_app/check_text_form.html", context={"content": dataset_data, 'text_id': text_id,
                                                                             'block_size': block_size, 'texts': texts, "result": result,
                                                                         "block_result": block_result})


def search_ngram_dataset(request, list_id: int, ngram_item: str) -> HttpResponse:
    """
    Поиск N-граммы в текстах датасета
    """
    try:
        dataset_data = TblBigramDataset.get_item(request.user, list_id)
    except TblBigramDataset.DoesNotExist:
        return render(request, "not_found.html", context={
            "message": "Нет прав на просмотр датасета N-грамм",
            "return_url": "r_ngrams_app/dataset_list",
            "return_name": "К списку датасетов"
        })

    for item in dataset_data.content:
        if ngram_item == item[0]:
            texts = TblText.get_texts(request.user, include_list = item[1]["text"])
            return render(request, "r_ngrams_app/dataset_text_list.html", context={"dataset": dataset_data,
                                                                                   "ngram": item, "texts": texts})

    return render(request, "not_found.html", context={
            "message": "N-грамма не найдена в датасете",
            "return_url": "r_ngrams_app/dataset_list",
            "return_name": "К списку датасетов"
        })


def search_ngram_text(request, list_id: int, ngram_item: str, text_id: int) -> HttpResponse:
    """
    Поиск N-граммы в конкретном тексте
    """
    try:
        dataset_data = TblBigramDataset.get_item(request.user, list_id)
    except TblBigramDataset.DoesNotExist:
        return render(request, "not_found.html", context={
            "message": "Нет прав на просмотр датасета N-грамм",
            "return_url": "r_ngrams_app/dataset_list",
            "return_name": "К списку датасетов"
        })

    text = TblText.get_text(request.user, text_id)

    if text is None:
        return render(request, "not_found.html", context={
            "message": "Нет доступа к выбранному тексту",
            "return_url": "r_ngrams_app/dataset_list",
            "return_name": "К списку датасетов"
        })

    content = text.get_content()
    positions = dataset_data.ngram_pos(ngram_item, content)

    return render(request, "r_ngrams_app/show_text.html", context={'dataset': dataset_data, 'content': content, 'paper': text, 'colormap': positions})


def check_group(request, list_id: int) -> HttpResponse:
    """
    Сравнение спектра текста и группы
    """
    try:
        dataset_data = TblBigramDataset.get_item(request.user, list_id)
    except TblBigramDataset.DoesNotExist:
        return render(request, "not_found.html", context={
            "message": "Нет прав на просмотр датасета N-грамм",
            "return_url": "r_ngrams_app/dataset_list",
            "return_name": "К списку датасетов"
        })

    texts = TblText.get_texts(request.user, exclude_deleted=True, exclude_not_verified=True).all()
    text_lists = TblTextListDescription.get_items(request.user).order_by("name").all()

    if request.method == "GET":
        return render(request, "r_ngrams_app/check_group_form.html", context={"content": dataset_data,
                                                                              'texts': texts,
                                                                              'text_lists': text_lists})

    text_id = request.POST.get("text_id", 0)
    group_id = request.POST.get("group_id", 0)
    block_size = request.POST.get("block_size", 0)

    error_msg = None

    if text_id == 0 or not text_id.isdigit():
        error_msg = "Выберите текст из списка"

    if group_id == 0 or not group_id.isdigit():
        error_msg = "Выберите группу текстов из списка"

    if block_size == 0 or not block_size.isdigit():
        error_msg = "Размер блока должен быть целым числом больше нуля"

    if error_msg is not None:
        return render(request, "r_ngrams_app/check_group_form.html", context={"content": dataset_data, 'texts': texts,
                                                                              'text_lists': text_lists,
                                                                              "error_message": error_msg,
                                                                              'text_id': text_id,
                                                                              'group_id': group_id,
                                                                              'block_size': block_size})
    group_ids = TblTextListDescription.get_item(request.user, group_id).items
    group = []
    for item in group_ids:
        if item.text_id != text_id:
            group.append({"text_id": item.text_id, "content": item.get_content()})

    result, block_result = dataset_data.check_group(text_id, TblText.get_text(request.user, text_id).get_content(), int(block_size), group)
    return render(request, "r_ngrams_app/check_group_form.html", context={"content": dataset_data, 'text_id': text_id,
                                                                          'group_id': group_id, 'text_lists': text_lists,
                                                                          'block_size': block_size, 'texts': texts, "result": result,
                                                                          "block_result": block_result})
