"""
Маршруты для обработки запросов на работу с профилем пользователя
"""

from django.urls import path

from user_app import views

urlpatterns = [
    path('user_app/login', views.log_in, name="user_app/login"),
    path('user_app/profile', views.profile, name="user_app/profile"),
    path('user_app/logout', views.log_out, name="user_app/logout")
]
