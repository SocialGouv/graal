# FROM python:3.11-slim
FROM pytorch/pytorch:2.5.0-cuda12.4-cudnn9-runtime

WORKDIR /app

RUN pip install poetry==1.8.4
# TODO: update poetry.lock
# COPY pyproject.toml poetry.lock ./
COPY pyproject.toml ./
RUN poetry install
RUN poetry run python -c "import nltk; nltk.download('punkt_tab'); nltk.download('stopwords')"

COPY . .

CMD ["python", "amendements_intelligents/full_pipeline.py"]
