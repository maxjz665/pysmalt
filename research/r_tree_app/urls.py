"""
Маршруты к деревьям решений
"""
from django.urls import path

from research.r_tree_app import views

urlpatterns = [
    path('list', views.tree_list, name="r_tree_app/tree_list"),
    path('list/add', views.add_list, name="r_tree_app/add_list"),
    path('list/<int:list_id>', views.show_list, name="r_tree_app/show_list"),
]
