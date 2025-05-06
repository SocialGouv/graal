from unittest.mock import Mock, patch

import pandas as pd
import pytest

from graal.summary.amendment_summarizer import AmendmentSummarizer
from graal.summary.summary_generation_load_balancer import SummaryGenerationLoadBalancer
from graal.summary.summary_handler import SummaryHandler


@pytest.fixture
def mock_client():
    client = Mock()
    client.name = "mock_client"
    client.type = "mock_type"
    client.generate_text.side_effect = lambda _: "new_summary"
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
        "Corps amdt": ["Corps 1", "Corps 2", "Corps 3", "Corps 4"],
        "Num amdt": [1, 2, 3, 4],
        "amdt_idx": [0, 1, 2, 3],
        "Objet amdt": ["Existing summary 1", "Existing summary 2", "", ""],
    }
    return pd.DataFrame(data)


def test_summary_handler_should_overwrite_true(load_balancer, sample_amendments_df):
    """Test that when should_overwrite is True, all summaries are regenerated."""
    # Create a SummaryHandler with should_overwrite=True
    handler = SummaryHandler(
        acronym_mapping={},
        amendments_df=sample_amendments_df.copy(),
        summary_gen_load_balancer=load_balancer,
        config_prompt="Test prompt",
        summary_column="Objet amdt",
        should_overwrite=True,
    )

    # Mock the AmendmentSummarizer.summarize method to avoid actual summarization
    with patch(
        "graal.summary.amendment_summarizer.AmendmentSummarizer.summarize"
    ) as mock_summarize:
        # Set up the mock to return the dataframe with all summaries replaced
        result_df = sample_amendments_df.copy()
        result_df["Objet amdt"] = [
            "new_summary",
            "new_summary",
            "new_summary",
            "new_summary",
        ]
        mock_summarize.return_value = result_df

        # Call the populate method
        result = handler.populate()

        # Verify that the AmendmentSummarizer was created with should_overwrite=True
        args, _ = mock_summarize.call_args
        assert handler.should_overwrite is True

        # Verify that all summaries were regenerated
        assert all(summary == "new_summary" for summary in result["Objet amdt"])


def test_summary_handler_should_overwrite_false(load_balancer, sample_amendments_df):
    """Test that when should_overwrite is False, only empty summaries are regenerated."""
    # Create a SummaryHandler with should_overwrite=False
    handler = SummaryHandler(
        acronym_mapping={},
        amendments_df=sample_amendments_df.copy(),
        summary_gen_load_balancer=load_balancer,
        config_prompt="Test prompt",
        summary_column="Objet amdt",
        should_overwrite=False,
    )

    # Mock the AmendmentSummarizer.summarize method to avoid actual summarization
    with patch(
        "graal.summary.amendment_summarizer.AmendmentSummarizer.summarize"
    ) as mock_summarize:
        # Set up the mock to return the dataframe with only empty summaries replaced
        result_df = sample_amendments_df.copy()
        result_df.loc[2, "Objet amdt"] = "new_summary"
        result_df.loc[3, "Objet amdt"] = "new_summary"
        mock_summarize.return_value = result_df

        # Call the populate method
        result = handler.populate()

        # Verify that the AmendmentSummarizer was created with should_overwrite=False
        args, _ = mock_summarize.call_args
        assert handler.should_overwrite is False

        # Verify that only empty summaries were regenerated
        assert result.loc[0, "Objet amdt"] == "Existing summary 1"
        assert result.loc[1, "Objet amdt"] == "Existing summary 2"
        assert result.loc[2, "Objet amdt"] == "new_summary"
        assert result.loc[3, "Objet amdt"] == "new_summary"


def test_amendment_summarizer_should_overwrite_true(
    load_balancer, sample_amendments_df
):
    """Test that AmendmentSummarizer processes all rows when should_overwrite is True."""
    summarizer = AmendmentSummarizer(
        sample_amendments_df.copy(),
        load_balancer,
        config_prompt="Test prompt",
        summary_column="Objet amdt",
        should_overwrite=True,
    )

    # Mock the _store_summary method to avoid modifying the dataframe
    with patch.object(summarizer, "_store_summary") as mock_store:
        summarizer.summarize(start_index=0, stop_index=3)

        # Verify that _store_summary was called for all rows
        assert mock_store.call_count == 4


def test_amendment_summarizer_should_overwrite_false(
    load_balancer, sample_amendments_df
):
    """Test that AmendmentSummarizer skips rows with existing summaries when should_overwrite is False."""
    summarizer = AmendmentSummarizer(
        sample_amendments_df.copy(),
        load_balancer,
        config_prompt="Test prompt",
        summary_column="Objet amdt",
        should_overwrite=False,
    )

    # Mock the _store_summary method to avoid modifying the dataframe
    with patch.object(summarizer, "_store_summary") as mock_store:
        summarizer.summarize(start_index=0, stop_index=3)

        # Verify that _store_summary was called only for rows with empty summaries
        assert mock_store.call_count == 2
