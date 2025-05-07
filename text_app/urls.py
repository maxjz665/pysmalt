"""
Маршруты к работе с текстом (просмотр и редактирование)
"""
from django.urls import path

from text_app import views

urlpatterns = [
    path('', views.list_papers, name='home'),
    path('papers', views.list_papers, name="text_app/papers_list"),
    path('papers/<int:paper_id>', views.paper_data, name="text_app/papers_data"),
    path('papers/<int:paper_id>/synt_analysis', views.paper_data_synt_analysis, name="text_app/synt_analysis"),
    path('attrs', views.list_attrs, name="text_app/attrs_list"),
    path('lists', views.get_text_lists, name="text_app/text_lists"),
    path('lists/<int:list_id>', views.text_list_item, name="text_app/text_list_item"),
    path('lists/<int:list_id>/edit', views.text_list_edit, name="text_app/text_list_edit"),
    path('lists/<int:list_id>/delete', views.text_list_delete, name="text_app/text_list_delete"),
    path('lists/new', views.text_list_create, name="text_app/text_list_create"),
    path('entries_list/', views.entries_list, name="text_app/entries_list"),
    path('entries_list/<int:id>/edit', views.entries_list_edit, name='text_app/entries_list_edit'),
    path('import/', views.import_form, name="text_app/import"),
    path('analyze/', views.analyze_text, name='analyze_text'),
    path('analyze_word/', views.analyze_word, name='analyze_word'),
]
