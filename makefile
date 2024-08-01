test:
	poetry run pytest tests/unit/**/*.py
	@echo "===== Finished running unit tests ====="

integration_test:
	poetry run pytest tests/integration/*.py
	@echo "===== Finished running integration tests ====="
