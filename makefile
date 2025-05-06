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

build_simil_db_ppl_fdv:
	poetry run python graal/utils/build_similarity_db.py --projects PPL_FIN_DE_VIE_2025 --output data/preprocessed/DB_PPL_FIN_DE_VIE_2025.pkl --drop-empty-columns "Objet amdt"

run:
	poetry run python graal/full_pipeline.py --config=config/default.yml
