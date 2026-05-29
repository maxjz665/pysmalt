# SMALT Authorship: запуск и руководство

Модуль `research.authorship` реализует пайплайн атрибуции авторства:

`текст → Natasha/Razdel → 193-мерный вектор → Profile/ML → результаты`

Synthetic fallback не используется в CLI/web/demo по умолчанию.

---

## Быстрый старт

### Windows — smoke (без dump)

```
run_smoke_authorship.bat
```

Скрипт автоматически:
1. Создаёт `.venv` и устанавливает зависимости
2. Загружает smoke-корпус (3 автора × 4 текста)
3. Запускает worker в отдельном окне
4. Запускает сервер на http://127.0.0.1:8000/research/authorship/

Откройте браузер, нажмите кнопку **Profile** или **ML** для запуска
эксперимента — worker выполнит его в фоне.

### Windows — полный запуск (5x8 / 5x7 / 7x6)

1. Положите `smalt.sql.20260115.070144.gz` рядом с `manage.py` (или папкой выше)
2. Запустите:

```
run_full_authorship.bat
```

Скрипт загрузит три дипломных корпуса из dump и запустит worker + сервер.
Первый запуск эксперимента может занять несколько минут — признаки
извлекаются через Natasha/Razdel-пайплайн.

### Linux / macOS

```bash
bash run_smoke_authorship.sh       # smoke без dump
bash run_full_authorship.sh        # полный запуск (нужен dump)
```

### Docker (только smoke)

```bash
docker compose up --build
```

---

## A. Smoke-корпус 3×4

Smoke-корпус встроен в проект. Назначение — проверить запуск, не требует dump.
- 3 автора × 4 коротких текста
- Признаки извлекаются при первом запуске
- Не является основным научным корпусом из отчётов

---

## B. Полные корпуса 5×8 / 5×7 / 7×6

Загружаются из dump SMALT. Dump не хранится в GitHub.

Первичный dump: `smalt.sql.20260115.070144.gz`
Запасной dump:  `smalt.sql.20220421.112227.gz`

### Загрузка корпусов вручную

```bash
# Все три сразу (рекомендуется):
python manage.py load_authorship_demo --corpus=all \
    --source-sql=/path/to/smalt.sql.20260115.070144.gz \
    --no-extract --settings=shower.settings.demo

# Или по одному:
python manage.py load_authorship_demo --corpus=5x8 \
    --source-sql=/path/to/smalt.sql.20260115.070144.gz \
    --settings=shower.settings.demo
```

`--no-extract` пропускает Natasha/Razdel при загрузке; признаки будут
извлечены автоматически при первом запуске эксперимента (worker).

### Запуск экспериментов через CLI

```bash
python manage.py run_authorship \
    --list-name="Authorship corpus 5x8" \
    --method=profile --extract-features --queue \
    --settings=shower.settings.demo

python manage.py run_authorship \
    --list-name="Authorship corpus 5x8" \
    --method=ml --queue \
    --settings=shower.settings.demo
```

`--queue` создаёт задачу в очереди — worker должен быть запущен.

---

## C. Worker

Web-кнопки **Profile** и **ML** создают эксперимент со статусом `queued`.
Для выполнения задач должен быть запущен worker:

```bash
# Windows (из отдельного окна):
RUN_AUTHORSHIP_WORKER.bat

# Windows PowerShell:
.\RUN_AUTHORSHIP_WORKER.ps1

# Linux / напрямую (демо):
python manage.py run_authorship_worker --settings=shower.settings.demo
```

Bat/sh-скрипты запуска (`run_smoke_authorship.bat` / `run_full_authorship.bat`)
запускают worker **автоматически** в отдельном окне.

Статус эксперимента: `queued → running → completed / failed`.
Страница эксперимента обновляется автоматически раз в 5 секунд пока задача активна.

### systemd (Linux, production)

Authorship-worker оформлен по той же схеме, что tree/ngram-воркеры SMALT
(см. `service/`):

- `service/smalt-authorship-app.service`
- `service/smalt-authorship-app.sh`

Установка — как в `service/readme.md`: поправить пути, скопировать
`*.service` в `/etc/systemd/system`, включить и запустить. На боевом сервере
worker идёт в основную БД (без `--settings=shower.settings.demo`).

---

## D. Атрибуция фрагментов (экспериментальный режим)

Доступна по адресу: `/research/authorship/attribute/fragments/`

Текст разбивается на фрагменты, для каждого определяется наиболее близкий
авторский профиль. Параметры: режим (`word_window` / `paragraphs`),
размер окна, шаг, порог надёжности, метрика.

**Ограничения:**
- Только профильный метод, ML не применяется
- Результаты по коротким фрагментам (< порога надёжности) менее устойчивы
- Для работы необходимо, чтобы профили уже были построены

---

## E. Технические детали

| Параметр | Значение |
|---|---|
| Признаков | 193 (Natasha/Razdel синтаксические) |
| Profile-метод | Манхэттенская/косинусная дистанция до медианного профиля |
| ML-метод | StandardScaler → SelectKBest → SVC(RBF), LOO-кросс-валидация |
| Параллелизм | Worker последовательный (n_jobs=1), подходит для 1 ядра |
| Worker | Опрос DB раз в 5 секунд, по одному эксперименту за раз |

---

## F. Ручной запуск (без скриптов)

```bash
python -m venv .venv
source .venv/bin/activate          # Linux/macOS
# .venv\Scripts\activate.bat       # Windows

pip install -r requirements.txt
python manage.py check --settings=shower.settings.demo
python manage.py migrate --settings=shower.settings.demo
python manage.py load_authorship_demo --settings=shower.settings.demo
python manage.py run_authorship_worker --settings=shower.settings.demo &
python manage.py runserver --settings=shower.settings.demo
```

---

## G. Проверочные команды

```bash
python manage.py check --settings=shower.settings.demo
python manage.py migrate --settings=shower.settings.demo
python manage.py test research.authorship --settings=shower.settings.demo
```

Ожидается: 0 issues, no migrations, 10 тестов OK.
