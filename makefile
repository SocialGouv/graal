test:
	poetry run pytest tests/unit
	@echo "===== Finished running unit tests ====="

integration_test:
	poetry run pytest tests/integration
	@echo "===== Finished running integration tests ====="

install:
	poetry install
	poetry run python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords')"
