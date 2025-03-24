from django.urls import path

from research.text_generator.views import text_generator_view, get_texts_for_list, help_view

urlpatterns = [
    path('generator/', text_generator_view, name='text_generator_form'),
    path('texts/', get_texts_for_list, name='text_generator_texts'),
    path('help/', help_view, name='text_generator_help'),
]