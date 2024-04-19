"""
Маршруты к работе с текстом (просмотр и редактирование)
"""
from django.urls import path

from text_app import views

urlpatterns = [
    path('', views.index, name='home'),
    path('papers', views.list_papers, name="text_app/papers_list"),
    path('papers/<int:paper_id>', views.paper_data, name="text_app/papers_data"),
    path('attrs', views.list_attrs, name="text_app/attrs_list"),
    path('lists', views.text_lists, name="text_app/text_lists"),
    path('lists/<int:list_id>', views.text_list_item, name="text_app/text_list_item"),
    path('lists/<int:list_id>/edit', views.text_list_edit, name="text_app/text_list_edit"),
    path('lists/<int:list_id>/delete', views.text_list_delete, name="text_app/text_list_delete"),
    path('lists/new', views.text_list_create, name="text_app/text_list_create"),
]
