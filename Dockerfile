# Multi-stage build pour optimiser la taille finale
FROM python:3.11-slim as builder

# Variables d'environnement pour optimiser pip
ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Installation des dépendances système nécessaires
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Installation de Poetry
RUN pip install poetry==1.8.4

# Configuration de Poetry
ENV POETRY_NO_INTERACTION=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

WORKDIR /app

# Copie des fichiers de dépendances en premier pour optimiser le cache Docker
COPY pyproject.toml poetry.lock ./

# Export des dépendances et installation avec pip
RUN poetry lock --no-update && \
    poetry export -f requirements.txt --output requirements.txt --without-hashes && \
    pip install --no-cache-dir -r requirements.txt && \
    rm -rf $POETRY_CACHE_DIR

# Stage final - image de runtime
FROM python:3.11-slim as runtime

# Variables d'environnement
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH="/app"

# Installation uniquement des dépendances runtime
RUN apt-get update && apt-get install -y \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Création d'un utilisateur non-root pour la sécurité (avec UID explicite pour Kubernetes)
RUN groupadd -r -g 1000 appuser && useradd -r -u 1000 -g appuser appuser

WORKDIR /app

# Copie des dépendances Python depuis le builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copie du code source
COPY --chown=appuser:appuser . .

# Changement vers l'utilisateur non-root (UID numérique pour Kubernetes)
USER 1000

# Health check pour vérifier que l'application fonctionne
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# Commande par défaut
CMD ["python", "/app/graal/full_pipeline.py"]
