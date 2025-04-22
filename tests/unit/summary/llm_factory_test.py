import os

import pytest
from pydantic_core import Url

from graal.summary.llm_clients import (
    FakeLLMAPIClient,
    OllamaAPIClient,
    OpenAIAPIClient,
    VllmAPIClient,
)
from graal.summary.llm_factory import (
    create_albert_client,
    create_fake_client,
    create_llm_api_clients,
    create_ollama_client,
    create_scaleway_client,
    create_vllm_client,
    get_rate_limiting_config,
)

# Individual Factory Function Tests


def test_create_scaleway_client():
    """Test creating a Scaleway API client."""
    # Set environment variables for the test
    os.environ["SCALEWAY_BASE_URL"] = "https://test-scaleway.com"
    os.environ["SCALEWAY_API_KEY"] = "test-scaleway-key"  # pragma: allowlist secret
    os.environ["SCALEWAY_MODEL_NAME"] = "test-scaleway-model"

    try:
        # Call the factory function
        client = create_scaleway_client(timeout=45)

        # Verify the client
        assert isinstance(client, OpenAIAPIClient)
        assert client.type == "openai"
        assert client.name.startswith("scaleway_")
        assert client.model_name == "test-scaleway-model"
        assert client.timeout == 45
    finally:
        # Clean up environment variables
        del os.environ["SCALEWAY_BASE_URL"]
        del os.environ["SCALEWAY_API_KEY"]
        del os.environ["SCALEWAY_MODEL_NAME"]


def test_create_albert_client():
    """Test creating an Albert API client."""
    # Set environment variables for the test
    os.environ["ETALAB_BASE_URL"] = "https://test-albert.com"
    os.environ["ETALAB_API_KEY"] = "test-etalab-key"  # pragma: allowlist secret
    os.environ["ETALAB_MODEL_NAME"] = "test-albert-model"

    try:
        # Call the factory function
        client = create_albert_client(timeout=45)

        # Verify the client
        assert isinstance(client, OpenAIAPIClient)
        assert client.type == "openai"
        assert client.name.startswith("albert_")
        assert client.model_name == "test-albert-model"
        assert client.timeout == 45
    finally:
        # Clean up environment variables
        del os.environ["ETALAB_BASE_URL"]
        del os.environ["ETALAB_API_KEY"]
        del os.environ["ETALAB_MODEL_NAME"]


def test_create_albert_client_default_url_and_model():
    """Test creating an Albert API client with default URL and model name."""
    # Set environment variables for the test
    os.environ["ETALAB_API_KEY"] = "test-etalab-key"  # pragma: allowlist secret
    # Intentionally not setting ETALAB_BASE_URL and ETALAB_MODEL_NAME

    try:
        # Call the factory function
        client = create_albert_client()

        # Verify the client
        assert isinstance(client, OpenAIAPIClient)
        assert client.type == "openai"
        assert client.name.startswith("albert_")
        assert client.model_name == "meta-llama/Meta-Llama-3.1-70B-Instruct"
        assert client.timeout == 30
    finally:
        # Clean up environment variables
        del os.environ["ETALAB_API_KEY"]


def test_create_ollama_client():
    """Test creating an Ollama API client."""
    # Set environment variables for the test
    os.environ["OLLAMA_ENDPOINT"] = "https://test-ollama.com"
    os.environ["OLLAMA_MODEL_NAME"] = "test-ollama-model"
    os.environ["OLLAMA_USER"] = "test-ollama-user"
    os.environ["OLLAMA_PASSWORD"] = (
        "test-ollama-password"  # pragma: allowlist secret  # noqa: S105
    )

    try:
        # Call the factory function
        client = create_ollama_client(timeout=45)

        # Verify the client
        assert isinstance(client, OllamaAPIClient)
        assert client.type == "ollama"
        assert client.name.startswith("ollama_")
        assert client.model_name == "test-ollama-model"
        assert client.endpoint == Url("https://test-ollama.com")
        assert client.user == "test-ollama-user"
        assert client.password == (
            "test-ollama-password"  # pragma: allowlist secret  # noqa: S105
        )
        assert client.timeout == 45
    finally:
        # Clean up environment variables
        del os.environ["OLLAMA_ENDPOINT"]
        del os.environ["OLLAMA_MODEL_NAME"]
        del os.environ["OLLAMA_USER"]
        del os.environ["OLLAMA_PASSWORD"]


def test_create_fake_client():
    """Test creating a fake LLM API client."""
    # Call the factory function
    client = create_fake_client()

    # Verify the client
    assert isinstance(client, FakeLLMAPIClient)
    assert client.type == "fake"
    assert client.name.startswith("fake_")


def test_create_vllm_client():
    """Test creating a VLLM API client."""
    # Set environment variables for the test
    os.environ["VLLM_MODEL_NAME"] = "test-vllm-model"
    os.environ["VLLM_ENDPOINT"] = "https://test-vllm.com"
    os.environ["VLLM_USER"] = "test-vllm-user"
    os.environ["VLLM_PASSWORD"] = (
        "test-vllm-password"  # pragma: allowlist secret  # noqa: S105
    )

    try:
        # Call the factory function
        client = create_vllm_client()

        # Verify the client
        assert isinstance(client, VllmAPIClient)
        assert client.type == "vllm"
        assert client.name.startswith("vllm_")
        assert client.model_name == "test-vllm-model"
        assert client.vllm_endpoint == Url("https://test-vllm.com")
        assert client.user == "test-vllm-user"
        assert client.password == (
            "test-vllm-password"  # pragma: allowlist secret # noqa: S105
        )
    finally:
        # Clean up environment variables
        del os.environ["VLLM_MODEL_NAME"]
        del os.environ["VLLM_ENDPOINT"]
        del os.environ["VLLM_USER"]
        del os.environ["VLLM_PASSWORD"]


# Integration Tests


def test_create_llm_api_clients_with_all_client_types():
    """Test creating LLM API clients with all client types."""
    # Set environment variables for the test
    os.environ["SCALEWAY_BASE_URL"] = "https://test-scaleway.com"
    os.environ["SCALEWAY_API_KEY"] = "test-scaleway-key"  # pragma: allowlist secret
    os.environ["SCALEWAY_MODEL_NAME"] = "test-scaleway-model"
    os.environ["ETALAB_API_KEY"] = "test-etalab-key"  # pragma: allowlist secret
    os.environ["ETALAB_BASE_URL"] = "https://test-albert.com"
    os.environ["ETALAB_MODEL_NAME"] = "test-albert-model"
    os.environ["OLLAMA_ENDPOINT"] = "https://test-ollama.com"
    os.environ["OLLAMA_MODEL_NAME"] = "test-ollama-model"
    os.environ["OLLAMA_USER"] = "test-ollama-user"
    os.environ["OLLAMA_PASSWORD"] = (
        "test-ollama-password"  # pragma: allowlist secret  # noqa: S105
    )
    os.environ["VLLM_MODEL_NAME"] = "test-vllm-model"
    os.environ["VLLM_ENDPOINT"] = "https://test-vllm.com"
    os.environ["VLLM_USER"] = "test-vllm-user"
    os.environ["VLLM_PASSWORD"] = (
        "test-vllm-password"  # pragma: allowlist secret  # noqa: S105
    )

    # Create a test configuration
    config = {
        "llm_clients": {
            "scaleway": {"nb_instances": 2, "timeout": 60},
            "ollama": {"nb_instances": 1, "timeout": 30},
            "albert": {"nb_instances": 1},
            "fake": {"nb_instances": 1},
            "vllm": {"nb_instances": 2},
        }
    }

    try:
        # Call the factory function
        clients = create_llm_api_clients(config)

        # Verify the clients
        assert len(clients) == 7  # 2 scaleway + 1 ollama + 1 albert + 1 fake + 2 vllm

        # Count the number of each type of client
        client_counts = {"scaleway": 0, "ollama": 0, "albert": 0, "fake": 0, "vllm": 0}

        for client in clients:
            if client.name.startswith("scaleway_"):
                client_counts["scaleway"] += 1
                assert isinstance(client, OpenAIAPIClient)
                assert client.timeout == 60
            elif client.name.startswith("ollama_"):
                client_counts["ollama"] += 1
                assert isinstance(client, OllamaAPIClient)
                assert client.timeout == 30
            elif client.name.startswith("albert_"):
                client_counts["albert"] += 1
                assert isinstance(client, OpenAIAPIClient)
            elif client.name.startswith("fake_"):
                client_counts["fake"] += 1
                assert isinstance(client, FakeLLMAPIClient)
            elif client.name.startswith("vllm_"):
                client_counts["vllm"] += 1
                assert isinstance(client, VllmAPIClient)

        assert client_counts["scaleway"] == 2
        assert client_counts["ollama"] == 1
        assert client_counts["albert"] == 1
        assert client_counts["fake"] == 1
        assert client_counts["vllm"] == 2
    finally:
        # Clean up environment variables
        del os.environ["SCALEWAY_BASE_URL"]
        del os.environ["SCALEWAY_API_KEY"]
        del os.environ["SCALEWAY_MODEL_NAME"]
        del os.environ["ETALAB_API_KEY"]
        del os.environ["ETALAB_BASE_URL"]
        del os.environ["ETALAB_MODEL_NAME"]
        del os.environ["OLLAMA_ENDPOINT"]
        del os.environ["OLLAMA_MODEL_NAME"]
        del os.environ["OLLAMA_USER"]
        del os.environ["OLLAMA_PASSWORD"]
        del os.environ["VLLM_MODEL_NAME"]
        del os.environ["VLLM_ENDPOINT"]
        del os.environ["VLLM_USER"]
        del os.environ["VLLM_PASSWORD"]


def test_create_llm_api_clients_with_no_config():
    """Test creating LLM API clients with no configuration."""
    with pytest.raises(ValueError, match="No LLM clients configuration found"):
        create_llm_api_clients({})


def test_create_llm_api_clients_with_unsupported_type():
    """Test creating LLM API clients with an unsupported client type."""
    config = {"llm_clients": {"unsupported_type": {"nb_instances": 1}}}

    with pytest.raises(
        ValueError, match="Unsupported LLM client type: unsupported_type"
    ):
        create_llm_api_clients(config)


# Rate Limiting Tests


def test_get_rate_limiting_config():
    """Test getting rate limiting configuration."""
    # Create a test configuration
    config = {
        "llm_clients": {
            "scaleway": {"nb_instances": 2, "timeout": 60, "rate_limiting": 10},
            "ollama": {"nb_instances": 1, "timeout": 30, "rate_limiting": 5},
            "albert": {"nb_instances": 1, "rate_limiting": 20},
            "fake": {"nb_instances": 1},
            "vllm": {"nb_instances": 2, "rate_limiting": 15},
        }
    }

    # Call the function
    rate_limiting = get_rate_limiting_config(config)

    # Verify the result
    assert rate_limiting == {"scaleway": 10, "ollama": 5, "albert": 20, "vllm": 15}


def test_get_rate_limiting_config_empty():
    """Test getting rate limiting configuration with empty config."""
    rate_limiting = get_rate_limiting_config({})

    assert rate_limiting == {}


def test_get_rate_limiting_config_no_rate_limiting():
    """Test getting rate limiting configuration with no rate limiting specified."""
    # Create a test configuration
    config = {"llm_clients": {"fake": {"nb_instances": 1}}}

    # Call the function
    rate_limiting = get_rate_limiting_config(config)

    # Verify the result
    assert rate_limiting == {}
