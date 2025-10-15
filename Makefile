.PHONY: install dev server lint format test migrations

install:
	python -m pip install -r requirements.txt

dev:
	python -m pip install -r requirements-dev.txt

server:
	python manage.py migrate
	python manage.py runserver 0.0.0.0:8000

lint:
	flake8
	isort --check --diff .
	black --check .

format:
	isort .
	black .

test:
	pytest

migrations:
	python manage.py makemigrations
	python manage.py migrate
