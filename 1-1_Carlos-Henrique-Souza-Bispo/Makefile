.PHONY: install train run test lint docker

install:
	python -m pip install -r requirements-dev.txt

train:
	python -m app.training

run:
	uvicorn app.main:app --reload

test:
	python -m pytest

lint:
	ruff check .

docker:
	docker compose up --build

