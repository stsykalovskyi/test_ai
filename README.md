# test_ai

Django-проект для розробки та деплою моделей відмінювання українських імен, звань та посад.

## Швидкий старт
1. Створити та активувати віртуальне середовище (`python -m venv .venv`).
2. Встановити залежності: `python -m pip install -r requirements.txt`.
3. Синхронізувати міграції: `python manage.py migrate`.
4. Запустити сервер: `python manage.py runserver` і перейти до `http://localhost:8000/` (головна), `http://localhost:8000/morphology/dashboard/` (дашборд) або `http://localhost:8000/api/morphology/inflect/` (API).
5. Підготуйте датасет `data/processed/train.csv` (колонки: `lemma,target_case,inflected,gender,animacy,title`) та натисніть "Старт навчання" на дашборді для тренування частотної моделі.

`GET` запит до API покаже опис. Для `POST` можна використати приклад JSON:

```json
{
  "lemma": "Генерал Іванов",
  "target_case": "родовий",
  "gender": "masculine",
  "animacy": "animate"
}
```

## Структура
- `ukrainian_morphology/` – Django app з REST endpoint, service layer та фронтенд-дашбордом.
- `ml/` – заготовки для пайплайнів навчання та збереження моделей.
- `templates/` – HTML-файли (дашборд у `morphology/dashboard.html`).
- `static/` – CSS/JS для дашборду.
- `docs/` – документація по моделі та планам.
- `data/` – (у .gitignore) сирі та оброблені датасети.
- `artifacts/` – (у .gitignore) збережені моделі.

## Синтез мовлення
- Команда `python manage.py text_to_speech` використовує модель Google Gemini (`gemini-2.5-flash-preview-tts`) для генерації аудіо та зберігає результат у WAV.
- Обов'язково задайте ключ `GOOGLE_API_KEY` (або `--api-key`) для доступу до Gemini API. Додаткові параметри – голос (`--voice`, напр. `Kore`), модель (`--model`) та налаштування хвильового файлу (`--channels`, `--sample-rate`, `--sample-width`).
- Приклад: `python manage.py text_to_speech --text "Привіт, світе!" --voice Kore --output /tmp/greet.wav`.
- Текст можна передати через `--text`, файл (`--text-file path.txt`) або через stdin (`echo "..." | python manage.py text_to_speech --output out.wav`).

## Розвиток моделі
- Початковий rule-based fallback знаходиться у `MorphologicalInflector`, але якщо доступний чекпойнт (`artifacts/ukrainian-inflector/checkpoints/latest.json`), використовується частотна модель.
- Конфігурація тренування та шляхи до даних описані у `ml/config.py`.
- План робіт та наступні кроки – `docs/morphology_model.md`.

## Тести
Запустити `python manage.py test ukrainian_morphology`.
