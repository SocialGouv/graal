test:
	poetry run pytest tests/unit
	python scripts/check_coverage.py coverage.json
	@echo "===== Finished running unit tests ====="

integration_test:
	poetry run pytest tests/integration
	@echo "===== Finished running integration tests ====="

install:
	poetry install
	poetry run pre-commit install --allow-missing-config -f
	poetry run detect-secrets scan > .secrets.baseline
	poetry run python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords')"

similarity-db-all:
	poetry run python graal/utils/build_similarity_db.py

run:
	python graal/full_pipeline.py --config=config/default.json

