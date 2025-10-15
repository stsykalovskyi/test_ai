# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Django-based project for developing and deploying Ukrainian name/title/rank inflection models. The system combines a REST API endpoint with a web dashboard for model training.

## Development Commands

**Setup and run server:**
```bash
python -m venv .venv  # Create virtual environment
python -m pip install -r requirements.txt  # Install dependencies
python manage.py migrate  # Run migrations
python manage.py runserver  # Start server on localhost:8000
```

**Makefile shortcuts:**
- `make install` - Install production dependencies
- `make dev` - Install development dependencies
- `make server` - Run migrations and start server on 0.0.0.0:8000
- `make lint` - Run flake8, isort, and black checks
- `make format` - Format code with isort and black
- `make test` - Run pytest
- `make migrations` - Create and apply migrations

**Testing:**
```bash
pytest  # Run all tests
python manage.py test ukrainian_morphology  # Django test runner
```

## Architecture

**Django app structure:**
- Main project: `test_ai/` (settings, URLs, root views)
- Morphology app: `ukrainian_morphology/` (API endpoints, services, dashboard)

**Model pipeline:**
The system uses a frequency-based model that memorizes inflections from training data:

1. **Model loading** (`ukrainian_morphology/services/inflection.py`):
   - `MorphologicalInflector` checks for checkpoint at `artifacts/ukrainian-inflector/checkpoints/latest.json`
   - Falls back to rule-based mock if no checkpoint exists

2. **Training** (`ml/training/pipeline.py`):
   - `TrainingPipeline` loads CSV from `data/processed/train.csv`
   - Expects columns: `lemma,target_case,inflected,gender,animacy,title`
   - Calls `InflectorModel.fit()` to build frequency mapping
   - Saves checkpoint to `artifacts/ukrainian-inflector/checkpoints/latest.json`

3. **Model implementation** (`ml/models/inflector.py`):
   - `InflectorModel` builds key from (lemma, target_case, gender, animacy, title)
   - Stores most frequent inflection for each key
   - JSON checkpoint format with pipe-delimited keys

**Configuration** (`ml/config.py`):
- `TrainingConfig` uses Pydantic validation
- Paths default to `DATA_DIR/processed/*.csv` and `ARTIFACTS_DIR/ukrainian-inflector/`
- All paths are defined in `test_ai/settings.py` (configurable via environment variables)

**Key paths** (from `test_ai/settings.py`):
- `DATA_DIR` = `BASE_DIR / "data"` (or env var `TRAINING_DATA_DIR`)
- `ARTIFACTS_DIR` = `BASE_DIR / "artifacts"` (or env var `ARTIFACTS_DIR`)
- `MODEL_CACHE_DIR` = `BASE_DIR / ".cache/models"` (or env var `MODEL_CACHE_DIR`)

## API Endpoints

- `/` - Home page
- `/morphology/dashboard/` - Training dashboard (frontend)
- `/api/morphology/inflect/` - REST endpoint for inflection

**API request format:**
```json
{
  "lemma": "Генерал Іванов",
  "target_case": "родовий",
  "gender": "masculine",
  "animacy": "animate"
}
```

## Training Workflow

1. Prepare dataset at `data/processed/train.csv` with required columns
2. Navigate to dashboard at `/morphology/dashboard/`
3. Click "Старт навчання" to trigger training
4. Model saves to `artifacts/ukrainian-inflector/checkpoints/latest.json`
5. API automatically uses new checkpoint on next request

## Environment Variables

Create `.env` file (see `.env.example`):
- `DJANGO_SECRET_KEY` - Django secret key
- `DJANGO_DEBUG` - Debug mode (default: True)
- `ALLOWED_HOSTS` - Comma-separated host list
- `TRAINING_DATA_DIR` - Override data directory
- `ARTIFACTS_DIR` - Override artifacts directory
- `MODEL_CACHE_DIR` - Override cache directory
