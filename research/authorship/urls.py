"""
Маршруты модуля определения авторства текста.
"""
from django.urls import path

from research.authorship.views.authorship_views import (
    authorship_home,
    demo_view,
    extract_features_view,
    text_features_view,
    run_experiment_view,
    experiment_detail_view,
    experiment_list_view,
    attribute_text_view,
    compare_methods_view,
    fragment_attribution_view,
)

urlpatterns = [
    path('', authorship_home, name='authorship/home'),
    path('demo/', demo_view, name='authorship/demo'),
    path('features/extract', extract_features_view, name='authorship/extract_features'),
    path('features/<int:text_id>', text_features_view, name='authorship/text_features'),
    path('experiments/', experiment_list_view, name='authorship/experiment_list'),
    path('experiments/run', run_experiment_view, name='authorship/run_experiment'),
    path('experiments/<int:experiment_id>', experiment_detail_view, name='authorship/experiment_detail'),
    path('attribute/', attribute_text_view, name='authorship/attribute_text'),
    path('attribute/fragments/', fragment_attribution_view, name='authorship/fragment_attribution'),
    path('compare/', compare_methods_view, name='authorship/compare_methods'),
]
