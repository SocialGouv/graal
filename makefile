test:
	poetry run pytest **/unit/*.py
	@echo "===== Finished running unit tests ====="

integration_test:
	poetry run pytest **/integration/*.py
	@echo "===== Finished running integration tests ====="
