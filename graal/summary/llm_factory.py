"""
Factory module for creating LLM API clients based on configuration.
"""
# mypy: ignore-errors

import logging
import logging.config
import os
from typing import Any, Dict, List, cast

import httpx
from pydantic_core import Url

from graal.custom_types import LLMType
from graal.summary.llm_clients import (
    FakeLLMAPIClient,
    LLMAPIClient,
    OllamaAPIClient,
    OpenAIAPIClient,
    VllmAPIClient,
)

logging.config.fileConfig("logging.conf")


def create_scaleway_client(
    base_url: str | None = None,
    api_key: str | None = None,
    model_name: str | None = None,
    timeout: int = 30,
) -> LLMAPIClient:
    """Create a Scaleway API client.

    Args:
        base_url: Base URL for the Scaleway API. If None, uses SCALEWAY_BASE_URL env var.
        api_key: API key for authentication. If None, uses SCALEWAY_API_KEY env var.
        model_name: Model name to use. If None, uses SCALEWAY_MODEL_NAME env var or default.
        timeout: Request timeout in seconds.

    Returns:
        A configured Scaleway LLM API client.
    """
    return OpenAIAPIClient(
        base_url=httpx.URL(base_url or os.environ["SCALEWAY_BASE_URL"]),
        api_key=api_key or os.environ["SCALEWAY_API_KEY"],
        model_name=model_name
        or os.getenv("SCALEWAY_MODEL_NAME", "meta-llama/Meta-Llama-3.3-70B-Instruct"),
        timeout=timeout,
        name="scaleway",
    )


def create_albert_client(
    base_url: str | None = None,
    api_key: str | None = None,
    model_name: str | None = None,
    timeout: int = 30,
) -> LLMAPIClient:
    """Create an Albert API client.

    Args:
        base_url: Base URL for the Albert API. If None, uses ETALAB_BASE_URL env var or default.
        api_key: API key for authentication. If None, uses ETALAB_API_KEY env var.
        model_name: Model name to use. If None, uses ETALAB_MODEL_NAME env var or default.
        timeout: Request timeout in seconds.

    Returns:
        A configured Albert LLM API client.
    """
    return OpenAIAPIClient(
        base_url=httpx.URL(
            base_url
            or os.getenv("ETALAB_BASE_URL", "https://albert.api.etalab.gouv.fr/v1")
        ),
        api_key=api_key or os.environ["ETALAB_API_KEY"],
        model_name=model_name
        or os.getenv("ETALAB_MODEL_NAME", "meta-llama/Meta-Llama-3.1-70B-Instruct"),
        timeout=timeout,
        name="albert",
    )


def create_ollama_client(
    endpoint: str | None = None,
    model_name: str | None = None,
    user: str | None = None,
    password: str | None = None,
    timeout: int = 30,
) -> LLMAPIClient:
    """Create an Ollama API client.

    Args:
        endpoint: Ollama endpoint URL. If None, uses OLLAMA_ENDPOINT env var.
        model_name: Model name to use. If None, uses OLLAMA_MODEL_NAME env var.
        user: Username for authentication. If None, uses OLLAMA_USER env var.
        password: Password for authentication. If None, uses OLLAMA_PASSWORD env var.
        timeout: Request timeout in seconds.

    Returns:
        A configured Ollama LLM API client.
    """
    return OllamaAPIClient(
        endpoint=Url(endpoint or os.environ["OLLAMA_ENDPOINT"]),
        model_name=model_name or os.environ["OLLAMA_MODEL_NAME"],
        user=user or os.environ["OLLAMA_USER"],
        password=password or os.environ["OLLAMA_PASSWORD"],
        timeout=timeout,
        name="ollama",
    )


def create_fake_client() -> LLMAPIClient:
    """Create a fake LLM API client.

    WARNING: This client returns random lorem ipsum text.
    DO NOT use for DSPy optimization. Use create_fake_dspy_client() instead.
    """
    return FakeLLMAPIClient(name="fake")


def create_vllm_client(
    endpoint: str | None = None,
    model_name: str | None = None,
    user: str | None = None,
    password: str | None = None,
    timeout: int = 30,
) -> LLMAPIClient:
    """Create a VLLM API client.

    Args:
        endpoint: VLLM endpoint URL. If None, uses VLLM_ENDPOINT env var.
        model_name: Model name to use. If None, uses VLLM_MODEL_NAME env var.
        user: Username for authentication. If None, uses VLLM_USER env var.
        password: Password for authentication. If None, uses VLLM_PASSWORD env var.
        timeout: Request timeout in seconds.

    Returns:
        A configured VLLM LLM API client.
    """
    return VllmAPIClient(
        model_name=model_name or os.environ["VLLM_MODEL_NAME"],
        vllm_endpoint=Url(endpoint or os.environ["VLLM_ENDPOINT"]),
        user=user or os.environ["VLLM_USER"],
        password=password or os.environ["VLLM_PASSWORD"],
        name="vllm",
        timeout=timeout,
    )


def create_llm_api_clients(
    config: Dict[str, Any], credentials: Dict[str, Dict[str, Any]] | None = None
) -> List[LLMAPIClient]:
    """
    Create LLM API clients based on the configuration.

    Args:
        config: The configuration dictionary.
        credentials: Optional dictionary mapping client types to their credentials.
                    Credentials will be passed to client creation functions.
                    If not provided, clients will use environment variables.

    Returns:
        A list of LLM API clients.
    """
    llm_api_clients: List[LLMAPIClient] = []
    credentials = credentials or {}

    # If no LLM clients configuration is provided, use default OpenAI configuration
    if "llm_clients" not in config:
        raise ValueError(
            "No LLM clients configuration found. Please provide a valid configuration."
        )

    llm_clients_config = config["llm_clients"]

    for client_type, client_config in llm_clients_config.items():
        nb_instances = client_config.get("nb_instances", 1)
        timeout = client_config.get("timeout", 30)
        client_credentials = credentials.get(client_type, {})

        for _ in range(nb_instances):
            if client_type == "scaleway":
                llm_api_clients.append(
                    create_scaleway_client(
                        base_url=client_credentials.get("base_url"),
                        api_key=client_credentials.get("api_key"),
                        model_name=client_credentials.get("model_name"),
                        timeout=timeout,
                    )
                )
            elif client_type == "ollama":
                llm_api_clients.append(
                    create_ollama_client(
                        endpoint=client_credentials.get("endpoint"),
                        model_name=client_credentials.get("model_name"),
                        user=client_credentials.get("user"),
                        password=client_credentials.get("password"),
                        timeout=timeout,
                    )
                )
            elif client_type == "albert":
                llm_api_clients.append(
                    create_albert_client(
                        base_url=client_credentials.get("base_url"),
                        api_key=client_credentials.get("api_key"),
                        model_name=client_credentials.get("model_name"),
                        timeout=timeout,
                    )
                )
            elif client_type == "fake":
                llm_api_clients.append(create_fake_client())
            elif client_type == "vllm":
                llm_api_clients.append(
                    create_vllm_client(
                        endpoint=client_credentials.get("endpoint"),
                        model_name=client_credentials.get("model_name"),
                        user=client_credentials.get("user"),
                        password=client_credentials.get("password"),
                        timeout=timeout,
                    )
                )
            else:
                raise ValueError(
                    f"Unsupported LLM client type: {client_type}. "
                    f"Supported types are: 'scaleway', 'ollama', 'albert', 'fake', 'fake_dspy', 'vllm'."
                )

    return llm_api_clients


def get_rate_limiting_config(config: Dict[str, Any]) -> Dict[LLMType, int]:
    """
    Get rate limiting configuration from the config.

    Args:
        config: The configuration dictionary.

    Returns:
        A dictionary mapping client types to rate limits.
    """
    rate_limiting: Dict[LLMType, int] = {}

    # Support both new and legacy config formats
    if "llm_clients" in config:
        # New config format
        llm_clients_config = config["llm_clients"]

        for client_type, client_config in llm_clients_config.items():
            if "rate_limiting" in client_config:
                rate_limiting[cast(LLMType, client_type)] = client_config[
                    "rate_limiting"
                ]

    return rate_limiting
