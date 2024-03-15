"""
Контроллер обработки запросов на работу с текстами
"""
from django.http import HttpRequest
from django.shortcuts import render


def index(request: HttpRequest):
    """
    Домашняя страница: отображение текстов
    """
    return render(request, "text_app/home.html", context={})


def list_papers(request: HttpRequest):
    pass
