from unittest.mock import MagicMock

import pytest

from graal.summary.llm_clients import LLMAPIClient
from graal.summary.summary_generation_load_balancer import (
    SummaryGenerationLoadBalancer,
)


@pytest.fixture
def mock_clients():
    client1 = MagicMock(spec=LLMAPIClient)
    client1.generate_text.return_value = "Summary 1"
    client1.name = "Client 1"
    client1.type = "mock_type"

    client2 = MagicMock(spec=LLMAPIClient)
    client2.generate_text.return_value = "Summary 2"
    client2.name = "Client 2"
    client2.type = "mock_type"

    return [client1, client2]


def test_generate_summaries_concurrent(mock_clients):
    load_balancer = SummaryGenerationLoadBalancer(
        clients=mock_clients, queue_timeout=1, rate_limiting_config={}
    )
    prompts = ["Prompt 1", "Prompt 2"]
    results = load_balancer.generate_summaries_concurrent(prompts)
    assert results == ["Summary 1", "Summary 2"]
    assert load_balancer.summary_count == 2


def test_obtain_client_success(mock_clients):
    load_balancer = SummaryGenerationLoadBalancer(
        clients=mock_clients, queue_timeout=1, rate_limiting_config={}
    )
    client = load_balancer._obtain_client()
    assert client in mock_clients


def test_obtain_client_timeout():
    load_balancer = SummaryGenerationLoadBalancer(
        clients=[], queue_timeout=0.1, rate_limiting_config={}
    )
    with pytest.raises(
        TimeoutError,
        match="No available clients in the pool within the timeout period.",
    ):
        load_balancer._obtain_client()


def test_generate_text_success(mock_clients):
    load_balancer = SummaryGenerationLoadBalancer(
        clients=mock_clients, queue_timeout=1, rate_limiting_config={}
    )
    result = load_balancer.generate_text("Test prompt")
    assert result == "Summary 1"
    assert load_balancer.summary_count == 1


def test_generate_text_retry_success(mock_clients):
    mock_clients[0].generate_text.side_effect = [Exception("Error")]
    load_balancer = SummaryGenerationLoadBalancer(
        clients=mock_clients, queue_timeout=1, rate_limiting_config={}
    )
    result = load_balancer.generate_text("Test prompt")
    assert result == "Summary 2"
    assert load_balancer.summary_count == 1


def test_generate_text_all_fail(mock_clients):
    for client in mock_clients:
        client.generate_text.side_effect = Exception("Error")
    load_balancer = SummaryGenerationLoadBalancer(
        clients=mock_clients, queue_timeout=1, max_retries=2, rate_limiting_config={}
    )
    result = load_balancer.generate_text("Test prompt")
    assert result == ""
    assert load_balancer.summary_count == 0


def test_rerun_long_results(mock_clients):
    load_balancer = SummaryGenerationLoadBalancer(
        clients=mock_clients, queue_timeout=1, rate_limiting_config={}
    )
    results = [
        "Short summary",
        "This is a very long summary that exceeds the word limit",
    ]
    expected_results = ["Short summary", "Summary 1"]

    new_results = load_balancer.rerun_long_results(results, max_words=5)

    assert new_results == expected_results
    assert load_balancer.summary_count == 1
