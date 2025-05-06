"""
Маршруты к деревьям решений
"""
from django.urls import path

from research.r_ngrams_app import views

urlpatterns = [
    # GET список датасетов
    path('dataset', views.dataset_list, name="r_ngrams_app/dataset_list"),
    # GET/POST добавление датасета
    path('dataset/add', views.dataset_add_list, name="r_ngrams_app/dataset_add"),
    # GET/POST просмотр датасета/ выполнение команд
    path('dataset/<int:list_id>', views.dataset_show_list, name="r_ngrams_app/dataset_show"),
    # GET/POST редактирование датасета
    path('dataset/<int:list_id>/edit', views.edit_item, name="r_ngrams_app/edit_item"),
    # GET удаление датасета
    path('dataset/<int:list_id>/delete', views.delete_item, name="r_ngrams_app/delete_item"),
    path('dataset/<int:list_id>/check_text', views.check_text, name="r_ngrams_app/check_text"),
    path('dataset/<int:list_id>/check_group', views.check_group, name="r_ngrams_app/check_group"),
    path('dataset/<int:list_id>/search/<str:ngram_item>', views.search_ngram_dataset, name="r_ngrams_app/search_ngram_dataset"),
    path('dataset/<int:list_id>/search/<str:ngram_item>/<int:text_id>', views.search_ngram_text, name="r_ngrams_app/search_ngram_text"),
]
