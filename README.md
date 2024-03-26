[![pipeline status](https://gl.petrsu.ru/platform/api/badges/develop/pipeline.svg)](https://gl.petrsu.ru/platform/api/-/commits/develop)
[![coverage report](https://gl.petrsu.ru/platform/api/badges/develop/coverage.svg)](https://gl.petrsu.ru/platform/api/-/commits/develop)
[![pylint](https://gl.petrsu.ru/platform/api/-/jobs/artifacts/develop/raw/pylint/pylint.svg?job=pylint)](https://gl.petrsu.ru/platform/api/-/jobs/artifacts/develop/raw/pylint/pylint.log?job=pylint)

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

### Запуск тестов
```shell
python manage.py test --settings=shower.settings.test
```
