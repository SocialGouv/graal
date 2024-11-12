test:
	poetry run pytest tests/unit
	python scripts/check_coverage.py coverage.json
	@echo "===== Finished running unit tests ====="

integration_test:
	poetry run pytest tests/integration
	@echo "===== Finished running integration tests ====="

install:
	poetry install
	poetry run python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords')"

run:
	python amendements_intelligents/full_pipeline.py --config=config/default.json

run-no-overwrite:
	python amendements_intelligents/full_pipeline.py --config=config/no_overwrite.json
