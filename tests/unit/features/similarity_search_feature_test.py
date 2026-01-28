"""Unit tests for SimilaritySearchFeature."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pandas as pd
import pytest

from graal.core.feature_interface import FeatureInput
from graal.features.similarity_search_feature import SimilaritySearchFeature


def _build_config() -> dict:
    return {
        "similarity_search": {
            "enabled": True,
            "database_id": "db-123",
            "columns_to_copy": {
                "Réponse": {"enabled": True},
            },
        }
    }


def test_similarity_search_feature_columns():
    feature = SimilaritySearchFeature(config=_build_config())

    output_columns = feature.get_output_columns()
    assert "Réponse" in output_columns
    assert "Commentaires" in output_columns
    assert "Sort" not in output_columns


def test_similarity_search_feature_required_columns():
    feature = SimilaritySearchFeature(config=_build_config())

    required_columns = feature.get_required_columns()
    assert required_columns == {"Corps amdt", "Exposé amdt", "amdt_idx", "Num article"}


def test_similarity_search_prepare_loads_database(monkeypatch: pytest.MonkeyPatch):
    feature = SimilaritySearchFeature(config=_build_config())
    manifest_service_mock = MagicMock()
    manifest_service_mock.resolve_s3_path_for_db = AsyncMock(
        return_value="similarity/db.parquet"
    )
    loader_mock = MagicMock()
    fake_df = pd.DataFrame({"amdt_idx": [1], "Corps amdt": ["foo"]})
    loader_mock.load_from_s3 = AsyncMock(return_value=fake_df)

    monkeypatch.setattr(
        "graal.features.similarity_search_feature.get_similarity_db_manifest_service",
        lambda: manifest_service_mock,
    )
    monkeypatch.setattr(
        "graal.features.similarity_search_feature.get_similarity_db_loader",
        lambda: loader_mock,
    )

    feature_input = FeatureInput(
        amendments_df=pd.DataFrame({"amdt_idx": [1]}),
        config=_build_config(),
    )

    def fake_run(main_coroutine):
        return asyncio.get_event_loop().run_until_complete(main_coroutine)

    monkeypatch.setattr(
        "graal.features.similarity_search_feature.run_async_on_main_loop",
        fake_run,
    )

    feature.prepare(feature_input)

    manifest_service_mock.resolve_s3_path_for_db.assert_awaited_once_with("db-123")
    loader_mock.load_from_s3.assert_awaited_once_with("similarity/db.parquet")
    assert feature._cached_similarity_df is not None


def test_similarity_search_process_without_prepare_raises():
    feature = SimilaritySearchFeature(config=_build_config())
    feature_input = FeatureInput(
        amendments_df=pd.DataFrame({"amdt_idx": [1]}),
        config=_build_config(),
    )

    with pytest.raises(RuntimeError):
        feature.process(feature_input)
