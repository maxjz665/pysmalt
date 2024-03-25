"""
Маршруты для обработки запросов на работу с профилем пользователя
"""

from django.urls import path

from user_app import views

urlpatterns = [
    path('user_app/login', views.login, name="user_app/login")
]
