"""
Unit tests for DSPy LLM client adapters.
"""

import pytest

from graal.summary.dspy_modules.adapters import (
    GraalLMAdapter,
    create_dspy_adapter,
)
from graal.summary.llm_clients import FakeLLMAPIClient


def test_graal_lm_adapter_initialization():
    """Test that GraalLMAdapter can be initialized."""
    client = FakeLLMAPIClient()
    adapter = GraalLMAdapter(client)

    assert adapter is not None
    assert adapter.client == client


def test_graal_lm_adapter_basic_request():
    """Test that adapter can make basic requests."""
    client = FakeLLMAPIClient()
    adapter = GraalLMAdapter(client)

    response = adapter.basic_request("Test prompt")

    assert isinstance(response, str)
    assert len(response) > 0


def test_graal_lm_adapter_call_returns_list():
    """Test that __call__ returns a list as expected by DSPy."""
    client = FakeLLMAPIClient()
    adapter = GraalLMAdapter(client)

    responses = adapter("Test prompt")

    assert isinstance(responses, list)
    assert len(responses) == 1
    assert isinstance(responses[0], str)


def test_create_dspy_adapter_unsupported_type():
    """Test factory function raises error for unsupported type."""
    # Create a mock client with unsupported type
    client = FakeLLMAPIClient()
    client.type = "unsupported_type"

    with pytest.raises(ValueError, match="Unsupported client type"):
        create_dspy_adapter(client)
