from unittest.mock import Mock

import pandas as pd
import pytest

from amendements_intelligents.populate_summaries import AmendmentSummarizer


@pytest.fixture
def mock_vllm_client():
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
    df["Objet 70B()"] = ""
    return df


def test_process_amendments(mock_vllm_client, sample_amendments_df):
    processor = AmendmentSummarizer(sample_amendments_df, mock_vllm_client)
    processor.summarize(start_index=0, stop_index=3, max_concurrent=1)

    assert mock_vllm_client.generate_summary.call_count == 2

    print(f'sample_amendments_df["Objet 70B()"] {sample_amendments_df["Objet 70B()"]}')

    assert sample_amendments_df.loc[0, "Objet 70B()"] == "mock_summary"
    assert sample_amendments_df.loc[1, "Objet 70B()"] == "mock_summary"
    assert sample_amendments_df.loc[2, "Objet 70B()"] == "Supprimer cet article"
    assert sample_amendments_df.loc[3, "Objet 70B()"] == "Supprimer cet article"


def test_process_amendments_with_low_stop_index(mock_vllm_client, sample_amendments_df):
    processor = AmendmentSummarizer(sample_amendments_df, mock_vllm_client)
    processor.summarize(start_index=0, stop_index=2, max_concurrent=1)

    assert mock_vllm_client.generate_summary.call_count == 2

    assert sample_amendments_df.loc[0, "Objet 70B()"] == "mock_summary"
    assert sample_amendments_df.loc[1, "Objet 70B()"] == "mock_summary"
    assert sample_amendments_df.loc[2, "Objet 70B()"] == "Supprimer cet article"
    assert sample_amendments_df.loc[3, "Objet 70B()"] == ""


def test_process_amendments_with_high_start_index(
    mock_vllm_client, sample_amendments_df
):
    processor = AmendmentSummarizer(sample_amendments_df, mock_vllm_client)
    processor.summarize(start_index=5, stop_index=3, max_concurrent=1)

    assert mock_vllm_client.generate_summary.call_count == 0

    assert sample_amendments_df.loc[0, "Objet 70B()"] == ""
    assert sample_amendments_df.loc[1, "Objet 70B()"] == ""
    assert sample_amendments_df.loc[2, "Objet 70B()"] == ""
    assert sample_amendments_df.loc[3, "Objet 70B()"] == ""


def test_process_amendments_with_invalid_rows(mock_vllm_client):
    data = {
        "Exposé amdt": ["", "Exposé 2", "", "Exposé 4"],
        "Corps amdt": ["", "Corps 2", "Supprimer l'article 26", ""],
        "Num amdt": [1, 2, 3, 4],
        "amdt_idx": [0, 1, 2, 3],
    }
    df = pd.DataFrame(data)
    df["Objet 70B()"] = ""

    processor = AmendmentSummarizer(df, mock_vllm_client)
    processor.summarize(start_index=0, stop_index=3, max_concurrent=1)

    assert mock_vllm_client.generate_summary.call_count == 1

    assert df.loc[0, "Objet 70B()"] == ""
    assert df.loc[1, "Objet 70B()"] == "mock_summary"
    assert df.loc[2, "Objet 70B()"] == ""
    assert df.loc[3, "Objet 70B()"] == ""
