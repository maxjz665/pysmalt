"""
Маршруты к деревьям решений
"""
from django.urls import path

from research.r_bigrams_app import views

urlpatterns = [
    path('dataset', views.dataset_list, name="r_bigrams_app/dataset_list"),
    path('dataset/add', views.dataset_add_list, name="r_bigrams_app/dataset_add"),
    path('dataset/<int:list_id>', views.dataset_show_list, name="r_bigrams_app/dataset_show"),
]
