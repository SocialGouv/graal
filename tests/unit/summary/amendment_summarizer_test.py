from unittest.mock import Mock

import pandas as pd
import pytest

from graal.summary.llm_clients import LLMAPIClient
from graal.summary.summary_generation_load_balancer import (
    SummaryGenerationLoadBalancer,
)
from graal.summary.summary_handler import AmendmentSummarizer


@pytest.fixture
def mock_client():
    client = Mock(spec=LLMAPIClient)
    client.name = "mock_client"
    client.type = "mock_type"
    client.generate_text.side_effect = lambda _: "mock_summary"
    return client


@pytest.fixture
def load_balancer(mock_client):
    return SummaryGenerationLoadBalancer(
        clients=[mock_client], queue_timeout=3.0, rate_limiting_config={}
    )


@pytest.fixture
def sample_amendments_df():
    data = {
        "Exposé amdt": ["Exposé 1", "Exposé 2", "Exposé 3", "Exposé 4"],
        "Corps amdt": [
            "Corps 1",
            "Corps 2",
            "Supprimer cet article.",
            "Supprimer cet article.",
        ],
        "Num amdt": [1, 2, 3, 4],
        "amdt_idx": [0, 1, 2, 3],
    }
    df = pd.DataFrame(data)
    df["Objet amdt"] = ""
    return df


def test_process_amendments(load_balancer, sample_amendments_df):
    summarizer = AmendmentSummarizer(
        sample_amendments_df,
        load_balancer,
        config_prompt="",
        summary_column="Objet amdt",
    )
    summarizer.summarize(start_index=0, stop_index=3)

    assert sample_amendments_df.loc[0, "Objet amdt"] == "mock_summary"
    assert sample_amendments_df.loc[1, "Objet amdt"] == "mock_summary"
    assert sample_amendments_df.loc[2, "Objet amdt"] == "Supprimer cet article."
    assert sample_amendments_df.loc[3, "Objet amdt"] == "Supprimer cet article."


def test_process_amendments_with_custom_summary_column(
    load_balancer, sample_amendments_df
):
    sample_amendments_df["Objet Custom"] = ""
    summarizer = AmendmentSummarizer(
        sample_amendments_df,
        load_balancer,
        config_prompt="",
        summary_column="Objet Custom",
    )
    summarizer.summarize(start_index=0, stop_index=3)
    assert sample_amendments_df.loc[0, "Objet Custom"] == "mock_summary"
    assert sample_amendments_df.loc[1, "Objet Custom"] == "mock_summary"
    assert sample_amendments_df.loc[2, "Objet Custom"] == "Supprimer cet article."
    assert sample_amendments_df.loc[3, "Objet Custom"] == "Supprimer cet article."


def test_process_amendments_with_low_stop_index(load_balancer, sample_amendments_df):
    summarizer = AmendmentSummarizer(
        sample_amendments_df,
        load_balancer,
        config_prompt="",
        summary_column="Objet amdt",
    )
    summarizer.summarize(start_index=0, stop_index=2)

    assert sample_amendments_df.loc[0, "Objet amdt"] == "mock_summary"
    assert sample_amendments_df.loc[1, "Objet amdt"] == "mock_summary"
    assert sample_amendments_df.loc[2, "Objet amdt"] == "Supprimer cet article."
    assert sample_amendments_df.loc[3, "Objet amdt"] == ""


def test_process_amendments_with_high_start_index(load_balancer, sample_amendments_df):
    summarizer = AmendmentSummarizer(
        sample_amendments_df,
        load_balancer,
        config_prompt="",
        summary_column="Objet amdt",
    )
    summarizer.summarize(start_index=5, stop_index=3)

    assert sample_amendments_df.loc[0, "Objet amdt"] == ""
    assert sample_amendments_df.loc[1, "Objet amdt"] == ""
    assert sample_amendments_df.loc[2, "Objet amdt"] == ""
    assert sample_amendments_df.loc[3, "Objet amdt"] == ""


def test_process_amendments_with_invalid_rows(load_balancer):
    data = {
        "Exposé amdt": ["", "Exposé 2", "", "Exposé 4"],
        "Corps amdt": ["", "Corps 2", "Supprimer l'article 26", ""],
        "Num amdt": [1, 2, 3, 4],
        "amdt_idx": [0, 1, 2, 3],
    }
    df = pd.DataFrame(data)
    df["Objet amdt"] = ""

    summarizer = AmendmentSummarizer(
        df, load_balancer, summary_column="Objet amdt", config_prompt=""
    )
    summarizer.summarize(start_index=0, stop_index=3)

    assert df.loc[0, "Objet amdt"] == ""
    assert df.loc[1, "Objet amdt"] == "mock_summary"
    assert df.loc[2, "Objet amdt"] == ""
    assert df.loc[3, "Objet amdt"] == ""
