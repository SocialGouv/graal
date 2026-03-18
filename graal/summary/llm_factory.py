"""Factory module for creating LLM API clients.

Historically, the pipeline created clients from YAML (`config["llm_clients"]` and
`config["llm_credentials"]`).

The DB-backed web app now uses admin-managed `LlmConfig` records as the source of
truth. The pipeline should create clients from those DB configs only.
"""

import logging
import logging.config
import os
from typing import cast

import httpx

from graal.custom_types import LLMType
from graal.database.enums import LlmProviderEnum
from graal.database.models import LlmConfig
from graal.summary.llm_clients import FakeLLMAPIClient, LLMAPIClient, OpenAIAPIClient

logging.config.fileConfig("logging.conf")


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

    resolved_base_url = (
        base_url
        or os.getenv("ETALAB_BASE_URL")
        or "https://albert.api.etalab.gouv.fr/v1"
    )

    resolved_model_name = (
        model_name
        or os.getenv("ETALAB_MODEL_NAME")
        or "meta-llama/Meta-Llama-3.1-70B-Instruct"
    )

    return OpenAIAPIClient(
        base_url=httpx.URL(resolved_base_url),
        api_key=api_key or os.environ["ETALAB_API_KEY"],
        model_name=resolved_model_name,
        timeout=timeout,
        name="albert",
        type="albert",
    )


def create_fake_client() -> LLMAPIClient:
    """Create a fake LLM API client.

    WARNING: This client returns random lorem ipsum text.
    """
    return FakeLLMAPIClient(name="fake")


def create_llm_api_clients_from_llm_config(
    llm_config: LlmConfig,
    *,
    timeout: int = 30,
) -> list[LLMAPIClient]:
    """Create a pool of LLM API clients from a DB-backed `LlmConfig`.

    Concurrency is implemented by instantiating `max_concurrent_requests` client
    instances and letting `SummaryGenerationLoadBalancer` schedule work across
    them.
    """

    if llm_config.max_concurrent_requests < 1:
        raise ValueError("max_concurrent_requests must be >= 1")

    clients: list[LLMAPIClient] = []
    provider = llm_config.provider

    if provider == LlmProviderEnum.albert:
        for _ in range(llm_config.max_concurrent_requests):
            clients.append(
                create_albert_client(
                    base_url=llm_config.base_url,
                    api_key=llm_config.api_key,
                    model_name=llm_config.model_name,
                    timeout=timeout,
                )
            )
        return clients

    raise ValueError(
        f"Unsupported LLM provider: {provider}. Supported providers: {list(LlmProviderEnum)}"
    )


def get_rate_limiting_config_from_llm_config(
    llm_config: LlmConfig,
) -> dict[LLMType, int]:
    """Return the per-provider RPM config for the load balancer."""

    return {cast(LLMType, llm_config.provider.value): llm_config.rate_limit_per_minute}
