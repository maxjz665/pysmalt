from django.urls import path

from research.hetco_app.views import hetco_app_view, get_texts_for_list

urlpatterns = [
    path('hetco_app/', hetco_app_view, name='hetco_app_form'),
    path('research/hetco/texts/', get_texts_for_list, name='hetco_texts'),
]