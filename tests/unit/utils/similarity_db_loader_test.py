"""Tests for :mod:`graal.utils.similarity_db_loader`."""

from unittest.mock import AsyncMock, MagicMock

import pandas as pd
import pytest

from graal.utils.similarity_db_loader import SimilarityDatabaseLoader


@pytest.fixture
def mock_s3_service(monkeypatch: pytest.MonkeyPatch):
    """Provide a fake S3 service with a mock database sub-service."""

    mock_db_service = MagicMock()
    mock_db_service.load_database_parquet = AsyncMock()

    mock_s3 = MagicMock()
    mock_s3.database = mock_db_service
    mock_s3.similarity_db_folder = "similarity_dbs"

    monkeypatch.setattr(
        "graal.utils.similarity_db_loader.get_s3_service",
        lambda: mock_s3,
    )

    return mock_db_service


@pytest.fixture
def loader(mock_s3_service: MagicMock) -> SimilarityDatabaseLoader:  # noqa: ARG001
    loader = SimilarityDatabaseLoader()
    loader.clear_cache()
    return loader


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "requested_path,expected_name",
    [
        ("PLFSS/2024.parquet", "PLFSS/2024.parquet"),
        ("similarity_dbs/PLFSS/2024.parquet", "PLFSS/2024.parquet"),
        ("/similarity_dbs/PLFSS/2024.parquet", "PLFSS/2024.parquet"),
    ],
)
async def test_load_from_s3_normalizes_paths(
    loader: SimilarityDatabaseLoader,
    mock_s3_service: MagicMock,
    requested_path: str,
    expected_name: str,
):
    fake_df = pd.DataFrame({"col": [1]})
    mock_s3_service.load_database_parquet.return_value = fake_df

    await loader.load_from_s3(requested_path)

    mock_s3_service.load_database_parquet.assert_awaited_with(expected_name)


@pytest.mark.asyncio
async def test_load_from_s3_caches_normalized_key(
    loader: SimilarityDatabaseLoader,
    mock_s3_service: MagicMock,
):
    fake_df = pd.DataFrame({"col": [1]})
    mock_s3_service.load_database_parquet.return_value = fake_df

    await loader.load_from_s3("similarity_dbs/foo.parquet")
    await loader.load_from_s3("foo.parquet")

    mock_s3_service.load_database_parquet.assert_awaited_once_with("foo.parquet")
