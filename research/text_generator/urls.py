from django.urls import path
from . import views

urlpatterns = [
    path('generator/', views.text_generator_view, name='text_generator_form'),
]