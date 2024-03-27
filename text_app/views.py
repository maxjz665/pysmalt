"""
Контроллер обработки запросов на работу с текстами
"""
from django.db.models import Q
from django.http import HttpRequest
from django.shortcuts import render

from text_app.models.tbl_text import TblText
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
    return render(request, "text_app/list_papers.html", context={'texts': texts, "view": view})
