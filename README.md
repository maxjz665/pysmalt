[![pipeline status](https://gitlab.dckarelia.ru/smalt/pysmalt/badges/main/pipeline.svg)](https://gitlab.dckarelia.ru/smalt/pysmalt/-/commits/main)
[![coverage report](https://gitlab.dckarelia.ru/smalt/pysmalt/badges/main/coverage.svg)](https://gitlab.dckarelia.ru/smalt/pysmalt/-/commits/main)
[![pylint](https://gitlab.dckarelia.ru/smalt/pysmalt/-/jobs/artifacts/main/raw/pylint/pylint.svg?job=pylint)](https://gitlab.dckarelia.ru/smalt/pysmalt/-/jobs/artifacts/main/raw/pylint/pylint.log?job=pylint)

# SMALT Shower (Python edition)
Приложение для работы с корпусом дореволюционных текстов.

Основные возможности:
- ввод текста
- разбор текста
- запуск инструментария исследователя 

## Локальные настройки
Для изменения настроек по умолчанию можно использовать файл `shower/settings/local.py`.
Данный файл отсутствует в системе и создается вручную.

Пример настройки подключения к БД в `shower/settings/local.py`:
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'smalt',
        'USER': 'smalt',
        'PASSWORD': 'secret-password',
        'HOST': 'localhost',
        'CHARSET': 'utf8mb4'
    }
}
```

## Запуск приложения

Основной веб сервер
```commandline
python manage.py runserver
```

Модуль генерации деревьев решений
```commandline
python manage.py run_tree_worker
```

Модуль генерации датасетов N-грамм
```commandline
python manage.py  run_ngrams_worker
```

## Для разработчиков
### Создание миграций
```shell
python manage.py makemigrations
```
### Применение миграций
```shell
python manage.py migrate
```

Если миграции применяются к уже существующей БД, то можно пропустить создание таблиц с помощью команды
```shell
python manage.py migrate --fake-initial
```

### Запуск тестов
```shell
python manage.py test --settings=shower.settings.test
```

### Консоль отладки Django
Для консоли необходимо установить дополнительно пакет https://django-debug-toolbar.readthedocs.io/en/stable/
```shell
pip install django-debug-toolbar
```
и добавить настройки для консоли
```python
from shower.settings.base import MIDDLEWARE, INSTALLED_APPS

# цепляем профилирование для консоли джанго
MIDDLEWARE = [
    "debug_toolbar.middleware.DebugToolbarMiddleware",
    *MIDDLEWARE,
]

# добавляем консоль джанго в список установленных приложений
INSTALLED_APPS = [
    *INSTALLED_APPS,
    "debug_toolbar",
]

# логирование работы БД
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django.db.backends': {
            'level': 'DEBUG',
            'handlers': ['console'],
        }
    },
}

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# нужно для отображения консоли джанго
INTERNAL_IPS = ["127.0.0.1"]
```
