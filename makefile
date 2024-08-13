test:
	poetry run pytest tests/unit
	@echo "===== Finished running unit tests ====="

integration_test:
	poetry run pytest tests/integration
	@echo "===== Finished running integration tests ====="
