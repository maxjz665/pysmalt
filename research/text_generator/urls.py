"""
Маршруты к деревьям решений
"""
from django.urls import path
from research.text_generator import views

urlpatterns = [ 
    path('list', views.tree_list, name="text_generator/tree_list"),
    path('list/add', views.add_list, name="text_generator/add_list"),
    path('list/<int:list_id>', views.show_list, name="text_generator/show_list"),
    path('list/<int:list_id>/graph', views.get_graph, name="text_generator/list_graph"),
    path('check/<int:list_id>', views.check_text, name="text_generator/check_text"),
]
