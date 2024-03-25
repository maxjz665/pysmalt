# SMALT Shower (Python edition)
Приложение для работы с корпусом дореволюционных текстов.

Основные возможности:
- ввод текста
- разбор текста
- запуск инструментария исследователя

## Локальные настройки
Для изменения настроек по умолчанию можно использовать файл `shower/local_settings.py`.
Данный файл отсутствует в системе и создается вручную.

Пример настройки подключения к БД в `shower/local_settings.py`:
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