from unittest.mock import Mock, patch

import pandas as pd
import pytest

from amendements_intelligents.populate_summaries import AmendmentSummarizer


@pytest.fixture
def mock_llm_client():
    mock = Mock()
    mock.generate_summary.return_value = "mock_summary"
    return mock


@pytest.fixture
def sample_amendments_df():
    data = {
        "Exposé amdt": ["Exposé 1", "Exposé 2", "Exposé 3", "Exposé 4"],
        "Corps amdt": [
            "Corps 1",
            "Corps 2",
            "Supprimer cet article",
            "Supprimer cet article.",
        ],
        "Num amdt": [1, 2, 3, 4],
        "amdt_idx": [0, 1, 2, 3],
    }
    df = pd.DataFrame(data)
    df["Objet amdt"] = ""
    return df


def test_process_amendments(mock_llm_client, sample_amendments_df):
    processor = AmendmentSummarizer(
        sample_amendments_df, mock_llm_client, summary_column="Objet amdt"
    )
    processor.summarize(start_index=0, stop_index=3, max_concurrent=1)

    assert mock_llm_client.generate_summary.call_count == 2

    assert sample_amendments_df.loc[0, "Objet amdt"] == "mock_summary"
    assert sample_amendments_df.loc[1, "Objet amdt"] == "mock_summary"
    assert sample_amendments_df.loc[2, "Objet amdt"] == "Supprimer cet article"
    assert sample_amendments_df.loc[3, "Objet amdt"] == "Supprimer cet article"


def test_process_amendments_with_custom_summary_column(
    mock_llm_client, sample_amendments_df
):
    processor = AmendmentSummarizer(
        sample_amendments_df, mock_llm_client, summary_column="Objet Custom"
    )
    processor.summarize(start_index=0, stop_index=3, max_concurrent=1)

    assert mock_llm_client.generate_summary.call_count == 2

    assert sample_amendments_df.loc[0, "Objet Custom"] == "mock_summary"
    assert sample_amendments_df.loc[1, "Objet Custom"] == "mock_summary"
    assert sample_amendments_df.loc[2, "Objet Custom"] == "Supprimer cet article"
    assert sample_amendments_df.loc[3, "Objet Custom"] == "Supprimer cet article"


def test_process_amendments_with_low_stop_index(mock_llm_client, sample_amendments_df):
    processor = AmendmentSummarizer(
        sample_amendments_df, mock_llm_client, summary_column="Objet amdt"
    )
    processor.summarize(start_index=0, stop_index=2, max_concurrent=1)

    assert mock_llm_client.generate_summary.call_count == 2

    assert sample_amendments_df.loc[0, "Objet amdt"] == "mock_summary"
    assert sample_amendments_df.loc[1, "Objet amdt"] == "mock_summary"
    assert sample_amendments_df.loc[2, "Objet amdt"] == "Supprimer cet article"
    assert sample_amendments_df.loc[3, "Objet amdt"] == ""


def test_process_amendments_with_high_start_index(
    mock_llm_client, sample_amendments_df
):
    processor = AmendmentSummarizer(
        sample_amendments_df, mock_llm_client, summary_column="Objet amdt"
    )
    processor.summarize(start_index=5, stop_index=3, max_concurrent=1)

    assert mock_llm_client.generate_summary.call_count == 0

    assert sample_amendments_df.loc[0, "Objet amdt"] == ""
    assert sample_amendments_df.loc[1, "Objet amdt"] == ""
    assert sample_amendments_df.loc[2, "Objet amdt"] == ""
    assert sample_amendments_df.loc[3, "Objet amdt"] == ""


def test_process_amendments_with_invalid_rows(mock_llm_client):
    data = {
        "Exposé amdt": ["", "Exposé 2", "", "Exposé 4"],
        "Corps amdt": ["", "Corps 2", "Supprimer l'article 26", ""],
        "Num amdt": [1, 2, 3, 4],
        "amdt_idx": [0, 1, 2, 3],
    }
    df = pd.DataFrame(data)
    df["Objet amdt"] = ""

    processor = AmendmentSummarizer(df, mock_llm_client, summary_column="Objet amdt")
    processor.summarize(start_index=0, stop_index=3, max_concurrent=1)

    assert mock_llm_client.generate_summary.call_count == 1

    assert df.loc[0, "Objet amdt"] == ""
    assert df.loc[1, "Objet amdt"] == "mock_summary"
    assert df.loc[2, "Objet amdt"] == ""
    assert df.loc[3, "Objet amdt"] == ""


def test_retry_logic(mock_llm_client, sample_amendments_df):
    mock_llm_client.generate_summary.side_effect = [
        Exception("API Error"),
        "mock_summary",
    ]

    with patch("time.sleep") as mock_sleep:
        processor = AmendmentSummarizer(
            sample_amendments_df,
            mock_llm_client,
            summary_column="Objet amdt",
            max_retries=1,
            base_linear_backoff_sec=10,
        )
        processor.summarize(start_index=0, stop_index=0, max_concurrent=1)

        assert mock_llm_client.generate_summary.call_count == 2
        assert sample_amendments_df.loc[0, "Objet amdt"] == "mock_summary"
        assert mock_sleep.call_count == 1
        assert mock_sleep.call_args[0][0] == 10


def test_retry_task(mock_llm_client, sample_amendments_df):
    processor = AmendmentSummarizer(
        sample_amendments_df,
        mock_llm_client,
        summary_column="Objet amdt",
        max_retries=1,
    )
    executor = Mock()
    futures_to_index = {}

    processor._retry_task(0, 1, futures_to_index, executor)

    assert executor.submit.call_count == 1
    assert futures_to_index
    future = list(futures_to_index.keys())[0]
    assert future.retries == 1
    assert futures_to_index[future] == 0
