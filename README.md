# GRAAL

Système de traitement automatisé des amendements législatifs. Il applique des traitements sur les exports Signale (JSON) : regroupement, attribution, similarité, résumés LLM, opinions — et produit un CSV enrichi.

## Setup

```bash
cp .env.example .env       # configure env vars (S3, DB, LLM...)
docker compose up -d       # start PostgreSQL
make install               # install Python + Node deps
poetry run alembic upgrade head  # apply DB migrations
```

### Key environment variables

```bash
# Database
DATABASE_URL="postgresql+asyncpg://graal_user:graal_local_pass@localhost/graal_dev"

# S3 (OVH Object Storage) — required for config files and similarity DBs
S3_BUCKET_ACCESS_KEY=""
S3_BUCKET_SECRET_KEY=""
S3_BUCKET_ENDPOINT="https://s3.gra.io.cloud.ovh.net"
S3_BUCKET_NAME=""
S3_BUCKET_REGION="gra"
S3_CONFIG_FOLDER="config_graal"
S3_SIMILARITY_DB_FOLDER="similarity_dbs"

# LLM — at least one provider required for summary generation
ETALAB_API_KEY=""                         # Albert (Etalab)
ETALAB_BASE_URL="https://albert.api.etalab.gouv.fr/v1"
SCALEWAY_BASE_URL=""                      # Scaleway
SCALEWAY_API_KEY=""
OLLAMA_ENDPOINT=""                        # Ollama (self-hosted)
OLLAMA_USER=""
OLLAMA_PASSWORD=""
```

**pgAdmin** (local DB UI): http://localhost:5050 — `admin@graal.com` / `admin`

## Commands

| Command | Description |
|---------|-------------|
| `make dev` | Start backend (`:8000`) + frontend (`:5173`) |
| `make web-backend` | Start backend only |
| `make web-frontend` | Start frontend only |
| `make install` | Install all dependencies (Python + Node) |
| `make test` | Run unit tests with coverage |
| `make integration_test` | Run integration tests |
| `make run` | Run the CLI pipeline with `config/default.yml` |
| `make run-no-overwrite` | Run CLI pipeline without overwriting existing values |
| `pnpm --filter frontend generate-types` | Regenerate TypeScript types from backend OpenAPI |
| `poetry run alembic upgrade head` | Apply pending DB migrations |
| `docker build -t graal .` | Build Docker image |
