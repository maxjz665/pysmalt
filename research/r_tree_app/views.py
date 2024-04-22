"""
Обработка запросов к деревьям решений
"""
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


def tree_list(request: HttpRequest) -> HttpResponse:
    """
    Получение списка деревьев решений
    :param request:
    :return:
    """
    return render(request, "r_tree_app/tree_list.html")


def add_list(request: HttpRequest) -> HttpResponse:
    """
    Форма добавления/добавление нового дерева решений
    :return:
    """
    return render(request, "r_tree_app/add_list.html")
