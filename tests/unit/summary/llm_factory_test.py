import os

from graal.database.enums import LlmProviderEnum
from graal.database.models import LlmConfig
from graal.summary.llm_clients import (
    FakeLLMAPIClient,
    OpenAIAPIClient,
)
from graal.summary.llm_factory import (
    create_albert_client,
    create_fake_client,
    create_llm_api_clients_from_llm_config,
    get_rate_limiting_config_from_llm_config,
)

# Individual Factory Function Tests


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
        assert client.type == "albert"
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
        assert client.type == "albert"
        assert client.name.startswith("albert_")
        assert client.model_name == "meta-llama/Meta-Llama-3.1-70B-Instruct"
        assert client.timeout == 30
    finally:
        # Clean up environment variables
        del os.environ["ETALAB_API_KEY"]


def test_create_fake_client():
    """Test creating a fake LLM API client."""
    # Call the factory function
    client = create_fake_client()

    # Verify the client
    assert isinstance(client, FakeLLMAPIClient)
    assert client.type == "fake"
    assert client.name.startswith("fake_")


# Rate Limiting Tests


def test_create_llm_api_clients_from_llm_config():
    """Test creating multiple client instances from a DB LlmConfig."""

    llm_config = LlmConfig(
        name="test",
        provider=LlmProviderEnum.albert,
        model_name="test-albert-model",
        base_url="https://test-albert.com",
        api_key="test-etalab-key",  # pragma: allowlist secret
        rate_limit_per_minute=20,
        max_concurrent_requests=3,
    )

    clients = create_llm_api_clients_from_llm_config(llm_config, timeout=45)

    assert len(clients) == 3
    assert all(isinstance(client, OpenAIAPIClient) for client in clients)
    assert all(client.type == "albert" for client in clients)
    assert all(client.model_name == "test-albert-model" for client in clients)
    assert all(client.timeout == 45 for client in clients)


def test_get_rate_limiting_config_from_llm_config():
    """Test getting rate limiting configuration from a DB LlmConfig."""

    llm_config = LlmConfig(
        name="test",
        provider=LlmProviderEnum.albert,
        model_name="test-albert-model",
        base_url="https://test-albert.com",
        api_key="test-etalab-key",  # pragma: allowlist secret
        rate_limit_per_minute=20,
        max_concurrent_requests=1,
    )

    rate_limiting = get_rate_limiting_config_from_llm_config(llm_config)

    assert rate_limiting == {"albert": 20}
