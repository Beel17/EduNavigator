.PHONY: install test run migrate clean

install:
	pip install -r requirements.txt
	playwright install chromium

test:
	pytest tests/ -v

run:
	python run.py

migrate:
	alembic upgrade head

clean:
	find . -type d -name __pycache__ -exec rm -r {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -r {} +
	rm -rf chroma_db/
	rm -rf storage/
	rm -rf .pytest_cache/
	rm -rf htmlcov/

