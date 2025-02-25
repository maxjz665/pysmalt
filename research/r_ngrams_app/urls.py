"""
Маршруты к деревьям решений
"""
from django.urls import path

from research.r_ngrams_app import views

urlpatterns = [
    path('dataset', views.dataset_list, name="r_ngrams_app/dataset_list"),
    path('dataset/add', views.dataset_add_list, name="r_ngrams_app/dataset_add"),
    path('dataset/<int:list_id>', views.dataset_show_list, name="r_ngrams_app/dataset_show"),
    path('dataset/<int:list_id>/check', views.check_text, name="r_ngrams_app/check_text"),
    path('dataset/<int:list_id>/search/<str:ngram_item>', views.search_ngram_dataset, name="r_ngrams_app/search_ngram_dataset"),
    path('dataset/<int:list_id>/search/<str:ngram_item>/<int:text_id>', views.search_ngram_text, name="r_ngrams_app/search_ngram_text"),
]
