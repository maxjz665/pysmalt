from django.apps import AppConfig


class RBigramsAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'research.r_ngrams_app'
    verbose_name = 'Исследование "Лексический спектр N-грамм"'
