from unittest.mock import Mock, patch

import pytest

from amendements_intelligents.summary.llm_clients import LLMAPIClient
from amendements_intelligents.summary.summary_generation_load_balancer import (
    SummaryGenerationLoadBalancer,
)


@pytest.fixture
def mock_client():
    client = Mock(spec=LLMAPIClient)
    client.generate_summary.side_effect = lambda prompt: f"Summary for {prompt}"
    return client


@pytest.fixture
def load_balancer(mock_client):
    return SummaryGenerationLoadBalancer(clients=[mock_client])


def test_generate_summary_success(load_balancer, mock_client):
    prompt = "Test prompt"
    expected_summary = f"Summary for {prompt}"
    summary = load_balancer.generate_summary(prompt)
    assert summary == expected_summary
    mock_client.generate_summary.assert_called_once_with(prompt)


def test_generate_summary_failure(load_balancer, mock_client):
    mock_client.generate_summary.side_effect = ConnectionError("Connection failed")
    prompt = "Test prompt"
    summary = load_balancer.generate_summary(prompt)
    assert summary == "All clients failed after retries."
    assert mock_client.generate_summary.call_count == load_balancer.max_retries


def test_generate_summaries_concurrent(load_balancer, mock_client):
    prompts = [f"Prompt {i}" for i in range(5)]
    expected_summaries = [f"Summary for {prompt}" for prompt in prompts]
    summaries = load_balancer.generate_summaries_concurrent(prompts)
    assert summaries == expected_summaries
    assert mock_client.generate_summary.call_count == len(prompts)
    for prompt in prompts:
        mock_client.generate_summary.assert_any_call(prompt)
