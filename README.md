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

```commandline
python manage.py runserver
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
