"""
Контроллер обработки запросов на работу с текстами
"""
import json
import re
import time
import os
from datetime import datetime, timedelta

import stanza
from prereform2modern import Processor
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models import Q
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.core.paginator import Paginator

from text_app.models.tbl_dict_word import TblDictWord
from text_app.models.tbl_menu_items import TblMenuItems, TblMenuItems2
from text_app.models.tbl_menu_params import TblMenuParams, TblMenuParams2
from text_app.models.tbl_text import TblText
from text_app.models.tbl_word import TblWord
from text_app.models.tbl_textlist import TblTextListDescription
from text_app.models.tbl_author_types import TblAuthorTypes
from text_app.models.tbl_author import TblAuthor
from text_app.models.tbl_magazine import TblMagazine
from text_app.models.parser import Parser
from user_app.models import TblUser
from text_app.models.stanza_analyzer import StanzaAnalyzer


#stanza_analyzer = StanzaAnalyzer(0)


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
    text_lists = TblTextListDescription.get_items(request.user).order_by("name")
    if not (request.user.is_authenticated and request.user.has_level(TblUser.LEVEL_MANAGER)):
        # если пользователь не менеджер, то скрываем удаленные тексты
        texts = texts.filter(~Q(category=1))
    if not (request.user.is_authenticated and request.user.has_level(TblUser.LEVEL_USER)):
        texts = texts.filter(status=2)
    if not request.user.is_authenticated:
        text_lists = text_lists.filter(public=True)
    else:
        if not request.user.has_level(TblUser.LEVEL_ADMIN):
            text_lists = text_lists.filter(owner=request.user)
    texts = texts.order_by('status').order_by('title').all()
    text_lists = text_lists.order_by('name').all()

    return render(request, "text_app/list_papers.html", context={'texts': texts, "view": view,
                                                                 "link": "text_app/papers_data",
                                                                 'text_lists': text_lists})


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


def get_text_lists(request: HttpRequest):
    """
    Отображение списков текстов
    :return: списки текстов
    """
    content = TblTextListDescription.get_items(request.user).order_by("name").all()

    return render(request, "text_app/text_lists.html", context={"content": content})


def text_list_item(request: HttpRequest, list_id: int) -> HttpResponse:
    """
    Печать содержимого списка текстов
    :param request: запрос
    :param list_id: номер списка текстов
    :return: содержимое списка текстов
    """
    try:
        item = TblTextListDescription.get_item(request.user, list_id)
    except ObjectDoesNotExist:
        return render(request, "not_found.html", context={"message": "Список не найден",
                                                          "return_url": "text_app/text_lists",
                                                          "return_name": "К спискам текстов"})
    error_message = None
    success_message = None

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
        texts = TblText.get_texts(request.user, exclude_list=item.item_ids)

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
    item = TblTextListDescription.get_item(request.user, list_id)

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
    try:
        item = TblTextListDescription.get_item(request.user, list_id)
    except ObjectDoesNotExist:
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


# Получает список частей речи и их id
def get_attrs():
    menu_items = TblMenuItems.objects.all()
    menu_params = TblMenuParams.objects.all()
    attrs = []
    i = 0
    for item in menu_params[0]._meta.fields[3:26]:
        item_id = int(getattr(menu_params[0], item.name))
        attrs.append({
            "id": i,
            "name": menu_items[item_id].item_caption,
        })
        # print(menu_items[item_id].item_caption)
        i += 1
    return attrs


def import_form(request: HttpRequest):
    """
    Форма загрузки текстов
    """
    if not request.user.is_authenticated or not request.user.has_manager:
        return render(request, "not_found.html", context={"message": "Недостаточно прав"})
    author_types = TblAuthorTypes.objects.all()
    authors = TblAuthor.objects.all()
    magazines = TblMagazine.objects.all()
    attrs = get_attrs()

    if request.method == 'POST':
        if request.POST.get('action') == 'run_import':
            def get_or_none(key):
                value = request.POST.get(key)
                return value if value and value.strip() else None

            # Получаем данные из формы
            title = get_or_none('inputName')
            author = get_or_none('inputAuthor')
            magazine = get_or_none('inputJournal')
            magazine_no = get_or_none('inputJournalNo')
            publication_date = get_or_none('inputDate')
            comment = get_or_none('comment')
            url = get_or_none('inputUrl')
            background = None
            category = get_or_none('category')
            text_type = get_or_none('textType')
            author_verify = get_or_none('authorVerify')
            author_type = get_or_none('authorType')
            author2 = get_or_none('inputAuthor2')
            author2_type = get_or_none('author2Type')
            author3 = get_or_none('inputAuthor3')
            author3_type = get_or_none('author3Type')
            short_title = get_or_none('shortTitle')
            magazine_volume = get_or_none('magazineVolume')
            magazine_section = get_or_none('magazineSection')
            pages = get_or_none('pages')
            censorship = get_or_none('censorship')
            attributions = get_or_none('attributions')
            status = get_or_none('status')
            origin_title = get_or_none('originTitle')

            grm_file = request.FILES.get('grmFile')  # Файл .txt

            words_json = request.POST.get('words_json')
            words = json.loads(words_json)
            print(words)
            print(title, magazine, grm_file.name if grm_file else "Файл не загружен")#удалить
            # логика сохранения в бд отключена для отладки
            '''text_obj = TblText.save_text_in_db(title, author, magazine, magazine_no, publication_date, comment, url, background,
                                    category, text_type, author_verify, author_type, author2, author2_type, author3, author3_type,
                                    short_title, magazine_volume, magazine_section, pages, censorship, attributions,
                                    status, origin_title)'''
            i = 0#удалить
            for word in words:
                #TblWord.save_word(TblText.objects.filter(id=331).get(), word) #логика сохранения в бд отключена для отладки
                print(word)#удалить
                i += 1#удалить
                if i == 4:#удалить
                    break#удалить
            return redirect('home')
    else:
        return render(request, "text_app/import_form.html",
                      context={"type": 'old', "author_types": author_types, "authors": authors, "magazines": magazines,
                               "attrs": attrs})


# Функция при передаче post-запроса анализирует текст (ищет в словаре совпадения) и выводит информацию по каждому слову
def analyze_text(request):
    if request.method == "POST":
        start_time = time.time()
        res = ""
        data = json.loads(request.body)
        text = data.get("text", "")

        mod_text = get_modern_word(text)
        stanza_analyzer.analyze_text(mod_text)
        #print(stanza_analyzer.text_doc.sentences)

        sections = list(filter(None, re.split(r"\n|\r\n", text)))
        parser = Parser()
        lines = parser.parseTextFile(sections)

        res += f"<p>Found {len(sections)} lines<br>"

        output = ""

        section = 0
        chapter_index = 1
        paragraph_index = 1
        sentence_index = 1
        word_index = 1
        for item in lines:
            try:
                ret = parser.encode_in_old_type(item)
            except Exception as e:
                print("\n", str(e), "\n", e.__traceback__)
                break
            if isinstance(item, (list, tuple)) and len(item) > 0 and isinstance(item[0], str) and len(item[0]) > 0:
                check_str = ret["ENCODED_WORD"]

                if ret["WORD"] == check_str:
                    if "ID" in ret:
                        printed_word = f"{ret['WORD']}({ret['ID']},P={ret['PARAM_01']})"
                        if ret['PARAM_01'] < 0:     # если часть речи отсуствует(значение < 0)
                            output += f"<a href='#' class='not-found' data-word='{ret['WORD']}' style='color:red'>{ret['WORD']}</a>" \
                                      f"<span data-word='{ret['WORD']}' data-id='' data-pos=''>(Х)</span>"
                        else:      # обычные слова присутствующие в словаре
                            output += f"<a href='#' class='found' data-word='{ret['WORD']}' style='color:black'>{ret['WORD']}</a>" \
                                      f"<span data-word='{ret['WORD']}' data-id='{ret['ID']}' data-pos='{ret['PARAM_01']}'>({ret['ID']},P={ret['PARAM_01']})</span>"
                    else:   # слова отсуствующие в словаре
                        output += f"<a href='#' class='not-found' data-word='{ret['WORD']}' style='color:blueviolet'>{ret['WORD']}</a>" \
                                  f"<span data-word='{ret['WORD']}' data-id='' data-pos=''>(Х)</span>"
                else:
                    output += f"<a href='#' class='not-found' data-word='{ret['WORD']}' style='color:red'>{ret['WORD']}</a>" \
                              f"<span data-word='{ret['WORD']}' data-id='' data-pos=''>(Х - {check_str})</span>"

                output += f"[{chapter_index}:{paragraph_index}:{sentence_index}:{word_index}] "     # вывод индексов
                section = 0
                word_index += 1
            else:
                section += 1
                if section == 1:
                    output += "| "
                    word_index = 1
                    sentence_index += 1
                elif section == 2:
                    output += "<br/>"
                    word_index = 1
                    sentence_index = 1
                    paragraph_index += 1
                else:
                    if word_index != 1 or sentence_index != 1 or paragraph_index != 1:
                        output += "</p><p>"
                        word_index = 1
                        sentence_index = 1
                        paragraph_index = 1
                        chapter_index += 1

        res += output + "</p>"

        # Разница во времени
        diff = time.time() - start_time  # в секундах, с дробной частью
        # Вычисляем минуты и секунды
        diff_minutes = int(diff // 60)
        diff_seconds = int(diff % 60)
        date = f"{diff_minutes:02}:{diff_seconds:02}"
        # Микросекунды
        fdiff = f"{int((diff - int(diff)) * 10_000_000):07d}"
        # Подсчёт total
        total = parser.miss + parser.hit
        res += f"<p>Время работы (мин:сек): {date}.{fdiff}<br>Miss: {parser.miss}, Hit: {parser.hit}, Total: {total} Not found: {parser.notFound}</p>"

        return JsonResponse({"result": res})
    return JsonResponse({"error": "Invalid request"}, status=400)

def get_modern_word(word):
    text_res, changes, s_json = Processor.process_text(
        text=word,
        show=False,
        delimiters=False,
        check_brackets=False
    )
    return text_res

# Функция анализирует текст с помощью станзы
def analyze_word(request):
    if request.method == "POST":
        import json
        data = json.loads(request.body)
        word = data.get('word', '')

        attrs = get_attrs()

        if word:
            mdrn_word = get_modern_word(word)
            print(mdrn_word)
            word_st = stanza_analyzer.analyze_word(mdrn_word)
            pos = word_st.upos  # либо .upos для более общего типа
            print(word_st)
            print(word_st.xpos)
            id_pos = stanza_analyzer.get_pos_id(word_st)
            if id_pos >= 0:
                attr_data = list(filter(lambda x: x['id'] == id_pos, attrs))[0]
                id = attr_data["id"]
                pos = attr_data['name']
            else:
                pos = "None"
                id = "None"

            return JsonResponse({"part_of_speech": pos, "id": id})

    return JsonResponse({"error": "Invalid request"}, status=400)


def entries_list(request: HttpRequest):
    if not request.user.is_authenticated or not request.user.has_manager:
        return render(request, "not_found.html", context={"message": "Недостаточно прав"})
    query = request.GET.get("q", "")
    dictwords = TblDictWord.objects.all()  # или как у тебя называется модель
    if query:
        dictwords = dictwords.filter(Q(word__icontains=query))
    paginator = Paginator(dictwords, 50)  # 50 слов на страницу
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    attrs = get_attrs()
    print(attrs)
    return render(request, "text_app/entries_list.html",
                  context={"dictwords": page_obj, "query": query, "attrs": attrs})
