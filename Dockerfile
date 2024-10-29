FROM pytorch/pytorch:2.5.0-cuda12.4-cudnn9-runtime

WORKDIR /app

RUN pip install poetry==1.8.4

COPY pyproject.toml poetry.lock ./

RUN poetry install

RUN poetry run python -c "import nltk; nltk.download('punkt_tab'); nltk.download('stopwords')"

COPY . .

ENV PYTHONPATH="/app"

CMD ["poetry", "run", "python", "/app/amendements_intelligents/full_pipeline.py"]
