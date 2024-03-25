"""
Контроллер обработки запросов на работу с текстами
"""
from django.http import HttpRequest
from django.shortcuts import render

from text_app.models.tbl_text import TblText


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
    texts = TblText.objects.filter().all()
    return render(request, "text_app/list_papers.html", context={'texts': texts})
