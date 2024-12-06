"""
Обработки запросов к биграммам
"""
from django.db.models import Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from research.r_bigrams_app.models.tbl_bigram_dataset import TblBigramDataset


def dataset_list(request: HttpRequest) -> HttpResponse:
    """
    Получение списка датасетов
    """
    items = TblBigramDataset.objects.filter(is_deleted=False)
    if request.user.is_authenticated:
        items = items.filter(Q(is_public=True) | Q(owner__id=request.user.id))
    else:
        items = items.filter(is_public=True)
    return render(request, "r_bigrams_app/dataset_list.html", context={"items": items})


def dataset_add_list(request: HttpRequest) -> HttpResponse:
    return None


def dataset_show_list(request: HttpRequest) -> HttpResponse:
    return None
