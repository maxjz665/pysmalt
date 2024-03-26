"""
Настройки для тестирования
"""

from .base import *

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# отключаем задержку при неверном логине
LOGIN_DELAY_SECONDS = 0
