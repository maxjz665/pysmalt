"""
Контроллер обработки запросов на работу с текстами
"""
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

    texts = TblText.objects.filter(inuse1=1)
    if not (request.user.is_authenticated and request.user.has_level(TblUser.LEVEL_USER)):
        texts = texts.filter(status=2)
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

    content = TblWord.objects.filter(text_id=paper_id).order_by("chapter_index",
                                                                "paragraph_index",
                                                                "sentence_index",
                                                                "word_index").all()

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

    texts = []
    if request.user.is_authenticated:
        # если пользователь авторизован, то показываем ему список текстов
        texts = TblText.objects.filter(inuse1=1, status=2).all()

    return render(request, "text_app/text_list_item.html", context={"content": item, "link": "text_app/papers_data", "texts": texts})


def text_list_create(request: HttpRequest):
    """
    Создание списка текстов
    :return:
    """
    return None
