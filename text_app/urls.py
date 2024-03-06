"""
Маршруты к работе с текстом (просмотр и редактирование)
"""
from django.urls import path

from text_app import views

urlpatterns = [
    path('', views.index, name='home')
]
