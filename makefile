test:
	poetry run pytest tests/unit
	@rm -f .coverage.* || true
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

# Web application development
web-backend:
	poetry run python start_web_server.py

web-frontend:
	cd frontend && yarn dev

dev:
	@echo "Starting GRAAL web application..."
	@echo "Backend will be available at: http://localhost:8000"
	@echo "Frontend will be available at: http://localhost:5173"
	@echo "Press Ctrl+C to stop both servers"
	@trap 'kill %1 %2 2>/dev/null; exit' INT; \
	poetry run python start_web_server.py & \
	cd frontend && yarn dev & \
	wait

dev-help:
	@echo "GRAAL Web Application Development Commands:"
	@echo "  make dev           - Start both backend and frontend servers"
	@echo "  make web-backend   - Start only the backend server"
	@echo "  make web-frontend  - Start only the frontend server"
	@echo ""
	@echo "URLs:"
	@echo "  Backend API: http://localhost:8000"
	@echo "  Frontend:    http://localhost:5173"
	@echo "  API Docs:    http://localhost:8000/docs"

s3-list:
	AWS_ACCESS_KEY_ID=${S3_BUCKET_ACCESS_KEY} AWS_SECRET_ACCESS_KEY=${S3_BUCKET_SECRET_KEY} aws s3 ls s3://$(S3_BUCKET_NAME)/${S3_CONFIG_FOLDER}/ --endpoint-url=$(S3_BUCKET_ENDPOINT) --region=$(S3_BUCKET_REGION)
	AWS_ACCESS_KEY_ID=${S3_BUCKET_ACCESS_KEY} AWS_SECRET_ACCESS_KEY=${S3_BUCKET_SECRET_KEY} aws s3 ls s3://$(S3_BUCKET_NAME)/${S3_SIMILARITY_DB_FOLDER}/ --endpoint-url=$(S3_BUCKET_ENDPOINT) --region=$(S3_BUCKET_REGION)

s3-upload-config:
	poetry run python scripts/s3_upload.py data/config_graal/* --destination $(S3_CONFIG_FOLDER)
