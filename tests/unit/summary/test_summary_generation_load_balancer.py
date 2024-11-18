import logging
from unittest.mock import MagicMock

import pytest

from graal.summary.llm_clients import LLMAPIClient
from graal.summary.summary_generation_load_balancer import (
    SummaryGenerationLoadBalancer,
)


@pytest.fixture
def mock_clients():
    client1 = MagicMock(spec=LLMAPIClient)
    client1.generate_summary.return_value = "Summary 1"
    client1.name = "Client 1"

    client2 = MagicMock(spec=LLMAPIClient)
    client2.generate_summary.return_value = "Summary 2"
    client2.name = "Client 2"

    return [client1, client2]


def test_generate_summaries_concurrent(mock_clients):
    load_balancer = SummaryGenerationLoadBalancer(clients=mock_clients, queue_timeout=1)
    prompts = ["Prompt 1", "Prompt 2"]
    results = load_balancer.generate_summaries_concurrent(prompts)
    assert results == ["Summary 1", "Summary 2"]
    assert load_balancer.summary_count == 2


def test_obtain_client_success(mock_clients):
    load_balancer = SummaryGenerationLoadBalancer(clients=mock_clients, queue_timeout=1)
    client = load_balancer._obtain_client()
    assert client in mock_clients


def test_obtain_client_timeout():
    load_balancer = SummaryGenerationLoadBalancer(clients=[], queue_timeout=0.1)
    with pytest.raises(
        TimeoutError,
        match="No available clients in the pool within the timeout period.",
    ):
        load_balancer._obtain_client()


def test_generate_summary_success(mock_clients):
    load_balancer = SummaryGenerationLoadBalancer(clients=mock_clients, queue_timeout=1)
    result = load_balancer.generate_summary("Test prompt")
    assert result == "Summary 1"
    assert load_balancer.summary_count == 1


def test_generate_summary_retry_success(mock_clients):
    mock_clients[0].generate_summary.side_effect = [Exception("Error")]
    load_balancer = SummaryGenerationLoadBalancer(clients=mock_clients, queue_timeout=1)
    result = load_balancer.generate_summary("Test prompt")
    assert result == "Summary 2"
    assert load_balancer.summary_count == 1


def test_generate_summary_all_fail(mock_clients):
    for client in mock_clients:
        client.generate_summary.side_effect = Exception("Error")
    load_balancer = SummaryGenerationLoadBalancer(
        clients=mock_clients, queue_timeout=1, max_retries=2
    )
    with pytest.raises(RuntimeError, match="All llm clients failed after retries."):
        load_balancer.generate_summary("Test prompt")
    assert load_balancer.summary_count == 0


def test_generate_summary_logging(mock_clients, caplog):
    mock_clients[0].generate_summary.side_effect = Exception("Error")
    load_balancer = SummaryGenerationLoadBalancer(
        clients=mock_clients, queue_timeout=1, max_retries=1
    )
    with caplog.at_level(logging.ERROR):
        with pytest.raises(RuntimeError):
            load_balancer.generate_summary("Test prompt")
    assert "Error with client Client 1: Error" in caplog.text


def test_rerun_long_results(mock_clients):
    load_balancer = SummaryGenerationLoadBalancer(clients=mock_clients, queue_timeout=1)
    results = [
        "Short summary",
        "This is a very long summary that exceeds the word limit",
    ]
    expected_results = ["Short summary", "Summary 1"]

    new_results = load_balancer.rerun_long_results(results, max_words=5)

    assert new_results == expected_results
    assert load_balancer.summary_count == 1
