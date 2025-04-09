from django.urls import path

from research.hetco_app.views import hetco_app_view

urlpatterns = [
    path('hetco_app/', hetco_app_view, name='hetco_app_form'),
]