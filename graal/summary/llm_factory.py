"""
Factory module for creating LLM API clients based on configuration.
"""
# mypy: ignore-errors

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


def create_scaleway_client(timeout: int = 30) -> LLMAPIClient:
    """Create a Scaleway API client."""
    return OpenAIAPIClient(
        base_url=httpx.URL(os.environ["SCALEWAY_BASE_URL"]),
        api_key=os.environ["SCALEWAY_API_KEY"],
        model_name=os.getenv(
            "SCALEWAY_MODEL_NAME", "meta-llama/Meta-Llama-3.3-70B-Instruct"
        ),
        timeout=timeout,
        name="scaleway",
    )


def create_albert_client(timeout: int = 30) -> LLMAPIClient:
    """Create an Albert API client."""
    return OpenAIAPIClient(
        base_url=httpx.URL(
            os.getenv("ETALAB_BASE_URL", "https://albert.api.etalab.gouv.fr/v1")
        ),
        api_key=os.environ["ETALAB_API_KEY"],
        model_name=os.getenv(
            "ETALAB_MODEL_NAME", "meta-llama/Meta-Llama-3.1-70B-Instruct"
        ),
        timeout=timeout,
        name="albert",
    )


def create_ollama_client(timeout: int = 30) -> LLMAPIClient:
    """Create an Ollama API client."""
    return OllamaAPIClient(
        endpoint=Url(os.environ["OLLAMA_ENDPOINT"]),
        model_name=os.environ["OLLAMA_MODEL_NAME"],
        user=os.environ["OLLAMA_USER"],
        password=os.environ["OLLAMA_PASSWORD"],
        timeout=timeout,
        name="ollama",
    )


def create_fake_client() -> LLMAPIClient:
    """Create a fake LLM API client."""
    return FakeLLMAPIClient(name="fake")


def create_vllm_client() -> LLMAPIClient:
    """Create a VLLM API client."""
    return VllmAPIClient(
        model_name=os.environ["VLLM_MODEL_NAME"],
        vllm_endpoint=Url(os.environ["VLLM_ENDPOINT"]),
        user=os.environ["VLLM_USER"],
        password=os.environ["VLLM_PASSWORD"],
        name="vllm",
    )


def create_llm_api_clients(config: Dict[str, Any]) -> List[LLMAPIClient]:
    """
    Create LLM API clients based on the configuration.

    Args:
        config: The configuration dictionary.

    Returns:
        A list of LLM API clients.
    """
    llm_api_clients: List[LLMAPIClient] = []

    # If no LLM clients configuration is provided, use default OpenAI configuration
    if "llm_clients" not in config:
        raise ValueError(
            "No LLM clients configuration found. Please provide a valid configuration."
        )

    llm_clients_config = config["llm_clients"]

    for client_type, client_config in llm_clients_config.items():
        nb_instances = client_config.get("nb_instances", 1)
        timeout = client_config.get("timeout", 30)

        for _ in range(nb_instances):
            if client_type == "scaleway":
                llm_api_clients.append(create_scaleway_client())
            elif client_type == "ollama":
                llm_api_clients.append(create_ollama_client(timeout))
            elif client_type == "albert":
                llm_api_clients.append(create_albert_client(timeout))
            elif client_type == "fake":
                llm_api_clients.append(create_fake_client())
            elif client_type == "vllm":
                llm_api_clients.append(create_vllm_client())
            else:
                raise ValueError(
                    f"Unsupported LLM client type: {client_type}. Supported types are: 'scaleway', 'ollama', 'albert', 'fake', 'vllm'."
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
