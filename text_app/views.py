"""
Контроллер обработки запросов на работу с текстами
"""
from django.db import transaction
from django.db.models import Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, redirect

from text_app.models.tbl_menu_items import TblMenuItems, TblMenuItems2
from text_app.models.tbl_menu_params import TblMenuParams, TblMenuParams2
from text_app.models.tbl_text import TblText
from text_app.models.tbl_textlist import TblTextListDescription
from text_app.models.tbl_word import TblWord
from user_app.models import TblUser


def index(request: HttpRequest):
    """
    Домашняя страница: отображение текстов
    """
    return render(request, "text_app/home.html", context={})


def list_papers(request: HttpRequest):
    """
    Отображение перечня произведений
    :param request: параметры запроса
    :return: перечень произведений
    """
    # получение параметров просмотра списка
    view = request.GET.get("view", "list")

    texts = TblText.get_texts(request.user)
    if not (request.user.is_authenticated and request.user.has_level(TblUser.LEVEL_MANAGER)):
        texts = texts.filter(~Q(category=1))
    texts = texts.order_by('status').order_by('title').all()
    return render(request, "text_app/list_papers.html", context={'texts': texts, "view": view,
                                                                 "link": "text_app/papers_data"})


def list_attrs(request: HttpRequest):
    """
    Отображение дерева атрибутов
    :param request: параметры запроса
    :return: дерево атрибутов
    """
    useOldType = request.GET.get("type", "old")
    if useOldType == "old":
        menu_items = TblMenuItems.objects.all()
        menu_params = TblMenuParams.objects.all()
    else:
        menu_items = TblMenuItems2.objects.all()
        menu_params = TblMenuParams2.objects.all()

    attrs = generate_tree(menu_items, menu_params, user=request.user)

    return render(request, "text_app/list_attrs.html", context={"attrs": attrs, "type": useOldType})


def generate_tree(menu_items, menu_params, start_param=0, user=None):
    """
    Генерация дерева на основе списков названий параметров и значений и пользователя
    :param start_param: стартовый узел дерева
    :param menu_items: названия параметров атрибутов
    :param menu_params: значения параметров атрибутов
    :param user: пользователь текущий
    :return: дерево
    """
    param_row = menu_params.get(id=start_param)
    key = param_row.param_caption
    values = []
    for i in range(1, param_row.items_count + 1):
        item_value = getattr(param_row, 'item_' + str(i))
        value_row = menu_items.get(id=item_value)
        items = []
        if user.is_authenticated and user.has_level(TblUser.LEVEL_EDITOR):
            for j in range(1, value_row.params_count + 1):
                items.append(generate_tree(menu_items, menu_params,
                                           start_param=getattr(value_row, "param_" + str(j)), user=user))
        values.append({"id": item_value, "name": value_row.item_caption, "attr_items": items})
    return {"id": start_param, "name": key, "attr_values": values}


def paper_data(request: HttpRequest, paper_id: int) -> HttpResponse:
    """
    Печать содержимого статьи
    :return: содержимое статьи
    """
    use_old_type = request.GET.get("type", "old")

    text_data = TblText.objects.filter(id=paper_id).get()

    content = text_data.get_content()

    if text_data is None or content is None:
        return render(request, "not_found.html", context={"message": "Текст не найден",
                                                          "return_url": "text_app/papers_list",
                                                          "return_name": "К списку текстов"})

    return render(request, "text_app/paper_data.html",
                  context={"type": use_old_type, "text_data": text_data, "content": content})


def text_lists(request: HttpRequest):
    """
    Отображение списков текстов
    :return: списки текстов
    """
    content = TblTextListDescription.objects.filter(is_deleted=False).all()

    return render(request, "text_app/text_lists.html", context={"content": content})


def text_list_item(request: HttpRequest, list_id: int) -> HttpResponse:
    """
    Печать содержимого списка текстов
    :param request: запрос
    :param list_id: номер списка текстов
    :return: содержимое списка текстов
    """
    item = TblTextListDescription.objects.filter(id=list_id).first()
    error_message = None
    success_message = None

    if item is None:
        return render(request, "not_found.html", context={"message": "Список не найден",
                                                          "return_url": "text_app/text_lists",
                                                          "return_name": "К спискам текстов"})

    if request.GET.get("action") is not None:
        action = request.GET.get("action")
        if action == "unpublish":
            if not request.user.is_authenticated or not request.user.has_manager:
                return render(request, "not_found.html", context={"message": "Недостаточно прав"})
            item.public = False
            item.save()
            return redirect("text_app/text_lists")
        if action == "publish":
            if not request.user.is_authenticated or not request.user.has_manager:
                return render(request, "not_found.html", context={"message": "Недостаточно прав"})
            item.public = True
            item.save()
            return redirect("text_app/text_lists")
        return render(request, "not_found.html",
                      context={"message": "Неизвестное действие " + request.GET.get("action"),
                               "return_url": "text_app/text_list_item",
                               "return_param": list_id,
                               "return_name": "К списку текстов"})

    if request.POST.get("action") is not None:
        try:
            action = request.POST.get("action")
            if action == "insertText":
                text_id = request.POST.get("selectionTextId")
                if text_id is None or int(text_id) == 0:
                    raise ValueError("Не задан идентификатор текста")
                if not request.user.is_authenticated or (
                        not request.user.has_level(TblUser.LEVEL_ADMIN) and request.user.id != item.owner.id):
                    raise PermissionError("Нет прав на добавление текста")
                item.append_text(text_id)
                success_message = "Текст успешно добавлен к списку"
            elif action == "removeText":
                text_id = request.POST.get("textId")
                if text_id is None or int(text_id) == 0:
                    raise ValueError("Не задан идентификатор текста")
                if not request.user.is_authenticated or (
                        not request.user.has_level(TblUser.LEVEL_ADMIN) and request.user.id != item.owner.id):
                    raise PermissionError("Нет прав на удаление текста")
                item.remove_text(text_id)
                success_message = "Текст успешно удален из списка"
            else:
                return render(request, "not_found.html",
                              context={"message": "Неизвестное действие " + request.POST.get("action"),
                                       "return_url": "text_app/text_list_item",
                                       "return_param": list_id,
                                       "return_name": "К списку текстов"})
        except Exception as e:
            error_message = str(e)

    texts = []
    if request.user.is_authenticated:
        # если пользователь авторизован, то показываем ему список текстов
        texts = TblText.get_texts(request.user, item.item_ids)

    return render(request, "text_app/text_list_item.html",
                  context={"content": item, "link": "text_app/papers_data", "texts": texts,
                           "error_message": error_message, "success_message": success_message})


def text_list_create(request: HttpRequest):
    """
    Создание списка текстов
    """
    if not request.user.is_authenticated:
        return render(request, "not_found.html",
                      context={"message": "Нет прав на создание списка",
                               "return_url": "text_app/text_lists",
                               "return_name": "К спискам текстов"})

    if request.method == "GET":
        texts = TblText.get_texts(request.user)
        return render(request, "text_app/text_list_create.html", context={"texts": texts})

    list_name = request.POST.get("inputName")
    items = request.POST.getlist("item")
    if list_name is None or len(list_name) == 0 or items is None or len(items) == 0:
        texts = TblText.get_texts(request.user)
        return render(request, "text_app/text_list_create.html",
                      context={"texts": texts, 'inputName': list_name, 'items': items,
                               "error_message": "Введите название списка и выберите тексты"})

    list_item = TblTextListDescription(name=list_name, owner=request.user, public=False, is_deleted=False)
    try:
        with transaction.atomic():
            list_item.save()
            for text in items:
                list_item.append_text(text)
    except Exception as e:
        texts = TblText.get_texts(request.user)
        return render(request, "text_app/text_list_create.html",
                      context={"texts": texts, 'inputName': list_name, 'items': items,
                               "error_message": "Введите название списка и выберите тексты"})
    return redirect("text_app/text_list_item", list_id=list_item.id)


def text_list_edit(request: HttpRequest, list_id: int) -> HttpResponse:
    item = TblTextListDescription.objects.filter(id=list_id).first()

    if not request.user.is_authenticated or (
            not request.user.has_level(TblUser.LEVEL_ADMIN) and request.user.id != item.owner.id):
        return render(request, "not_found.html",
                      context={"message": "Нет прав на редактирование списка",
                               "return_url": "text_app/text_list_item",
                               "return_param": list_id,
                               "return_name": "К списку текстов"})

    if request.method == "GET":
        return render(request, "text_app/text_list_edit.html", context={"content": item})

    item.name = request.POST.get("inputName")
    item.save()
    return redirect("text_app/text_list_item", list_id=list_id)


def text_list_delete(request: HttpRequest, list_id: int) -> HttpResponse:
    item = TblTextListDescription.objects.filter(id=list_id).first()

    if item is None:
        return render(request, "not_found.html", context={"message": "Список не найден",
                                                          "return_url": "text_app/text_lists",
                                                          "return_name": "К спискам текстов"})

    if not request.user.is_authenticated or (
            not request.user.has_level(TblUser.LEVEL_ADMIN) and request.user.id != item.owner.id):
        return render(request, "not_found.html",
                      context={"message": "Нет прав на удаление списка",
                               "return_url": "text_app/text_list_item",
                               "return_param": list_id,
                               "return_name": "К списку текстов"})

    item.delete()
    return redirect("text_app/text_lists")
