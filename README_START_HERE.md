# SMALT Authorship: запуск демо и полного пайплайна

Модуль `research.authorship` реализует пайплайн атрибуции авторства:

`текст -> Natasha/Razdel -> 193-мерный вектор -> profile/ML -> результаты`

Synthetic fallback не используется в CLI/web/demo по умолчанию.

---

## Запуск на Windows

Для быстрой проверки — двойной клик на `run_smoke_authorship.bat`.
Скрипт создаст `.venv`, поставит зависимости и запустит сервер.

```
run_smoke_authorship.bat
```

Для полного прогона по корпусам 5×8, 5×7, 7×6 нужен файл `smalt.sql.20220421.112227.gz`
рядом с `manage.py`, затем:

```
run_full_authorship.bat
```

Docker — альтернативный вариант, без установки Python. Запускает только smoke-сценарий:

```bash
docker compose up --build
```

Адрес после запуска: http://127.0.0.1:8000/research/authorship/

---

## A. Быстрый smoke-test 3x4

Smoke-корпус нужен только для проверки запуска: 3 автора x 4 коротких текста.
Это не основной научный корпус из отчётов.

### Docker

```bash
docker compose up --build
```

Docker выполняет:

```bash
python manage.py migrate --settings=shower.settings.demo
python manage.py load_authorship_demo --settings=shower.settings.demo
python manage.py runserver 0.0.0.0:8000 --settings=shower.settings.demo
```

Откройте:

```text
http://127.0.0.1:8000/research/authorship/
```

### Без Docker

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate --settings=shower.settings.demo
python manage.py load_authorship_demo --settings=shower.settings.demo
python manage.py run_authorship --method=profile --extract-features --settings=shower.settings.demo
python manage.py run_authorship --method=ml --settings=shower.settings.demo
python manage.py runserver --settings=shower.settings.demo
```

Откройте:

```text
http://127.0.0.1:8000/research/authorship/
```

## B. Полные корпуса 5x8 / 5x7 / 7x6

Полные корпуса загружаются отдельной командой; при `docker compose up` они не импортируются.

Нужен дамп SMALT:

```text
smalt.sql.20220421.112227.gz
```

Положите в корень проекта или передайте путь явно:

```bash
python manage.py load_authorship_demo --corpus=5x8 --source-sql=/path/to/smalt.sql.20220421.112227.gz --settings=shower.settings.demo
python manage.py load_authorship_demo --corpus=5x7 --source-sql=/path/to/smalt.sql.20220421.112227.gz --settings=shower.settings.demo
python manage.py load_authorship_demo --corpus=7x6 --source-sql=/path/to/smalt.sql.20220421.112227.gz --settings=shower.settings.demo
```

Или все три сразу:

```bash
python manage.py load_authorship_demo --corpus=all --source-sql=/path/to/smalt.sql.20220421.112227.gz --settings=shower.settings.demo
```

Команда печатает `list_id`. После загрузки:

```bash
python manage.py run_authorship --list_id=<id> --method=profile --extract-features --settings=shower.settings.demo
python manage.py run_authorship --list_id=<id> --method=ml --settings=shower.settings.demo
python manage.py authorship_report --list_id=<id> --include-ml --settings=shower.settings.demo
```

Для всех отчётных корпусов разом:

```bash
python manage.py authorship_report --all --include-ml --settings=shower.settings.demo
```

## Что смотреть на странице

На `/research/authorship/`:

- список текстовых списков
- запуск Profile/ML эксперимента
- результаты экспериментов с accuracy и macro F1
- форма вставки произвольного текста
- ранжирование авторов по profile-методу

## Проверочные команды

```bash
python manage.py check --settings=shower.settings.demo
python manage.py migrate --settings=shower.settings.demo
python manage.py load_authorship_demo --settings=shower.settings.demo
python manage.py run_authorship --method=profile --extract-features --settings=shower.settings.demo
python manage.py run_authorship --method=ml --settings=shower.settings.demo
python manage.py test research.authorship --settings=shower.settings.demo
```
