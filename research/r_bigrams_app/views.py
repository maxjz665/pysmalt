"""
Обработки запросов к биграммам
"""
from django.db.models import Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from research.r_bigrams_app.models.tbl_bigram_dataset import TblBigramDataset
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
    return None


def dataset_show_list(request: HttpRequest) -> HttpResponse:
    return None
