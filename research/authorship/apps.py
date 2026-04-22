from django.apps import AppConfig


class AuthorshipConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'research.authorship'
    verbose_name = 'Определение авторства текста'
