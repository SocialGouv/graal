"""
LLM client adapters for DSPy compatibility.

This module provides adapters to wrap GRAAL's existing LLM clients (Albert,
Scaleway, Ollama, VLLM) into DSPy-compatible LM objects.
"""

import logging
from typing import Any

import dspy

from graal.summary.llm_clients import LLMAPIClient


class GraalLMAdapter(dspy.LM):
    """Base adapter for GRAAL LLM clients to DSPy LM interface.

    This adapter wraps existing GRAAL LLM clients to make them compatible
    with DSPy's language model interface.
    """

    def __init__(self, client: LLMAPIClient, model_type: str = "text"):
        """Initialize the adapter with a GRAAL LLM client.

        Args:
            client: GRAAL LLM API client instance
            model_type: Type of model ("text" or "chat")
        """
        super().__init__(model=client.name)
        self.client = client
        self.model_type = model_type
        self.history: list[dict[str, Any]] = []

    def basic_request(self, prompt: str, **kwargs) -> str:
        """Make a basic text generation request.

        Args:
            prompt: Input prompt string
            **kwargs: Additional arguments (ignored for GRAAL clients)

        Returns:
            Generated text response
        """
        try:
            response = self.client.generate_text(prompt)

            return response
        except Exception as e:
            logging.error(f"Error in {self.client.name} adapter: {e}")
            raise

    def __call__(self, prompt: str, **kwargs) -> list[str]:
        """Call the LM to generate responses.

        DSPy expects this method to return a list of completions.

        Args:
            prompt: Input prompt string
            **kwargs: Additional generation parameters

        Returns:
            List containing the generated response
        """
        response = self.basic_request(prompt, **kwargs)
        return [response]


class AlbertDSPyAdapter(GraalLMAdapter):
    """DSPy adapter specifically for Albert LLM client."""

    def __init__(self, client: LLMAPIClient):
        """Initialize Albert adapter.

        Args:
            client: Albert LLM API client instance
        """
        super().__init__(client, model_type="chat")
        logging.info(f"Initialized Albert DSPy adapter with model {client.name}")


class ScalewayDSPyAdapter(GraalLMAdapter):
    """DSPy adapter specifically for Scaleway LLM client."""

    def __init__(self, client: LLMAPIClient):
        """Initialize Scaleway adapter.

        Args:
            client: Scaleway LLM API client instance
        """
        super().__init__(client, model_type="chat")
        logging.info(f"Initialized Scaleway DSPy adapter with model {client.name}")


class OllamaDSPyAdapter(GraalLMAdapter):
    """DSPy adapter specifically for Ollama LLM client."""

    def __init__(self, client: LLMAPIClient):
        """Initialize Ollama adapter.

        Args:
            client: Ollama LLM API client instance
        """
        super().__init__(client, model_type="text")
        logging.info(f"Initialized Ollama DSPy adapter with model {client.name}")


class VllmDSPyAdapter(GraalLMAdapter):
    """DSPy adapter specifically for VLLM LLM client."""

    def __init__(self, client: LLMAPIClient):
        """Initialize VLLM adapter.

        Args:
            client: VLLM LLM API client instance
        """
        super().__init__(client, model_type="text")
        logging.info(f"Initialized VLLM DSPy adapter with model {client.name}")


def create_dspy_adapter(client: LLMAPIClient) -> GraalLMAdapter:
    """Factory function to create the appropriate DSPy adapter for a client.

    Args:
        client: GRAAL LLM API client instance

    Returns:
        Appropriate DSPy adapter for the client type

    Raises:
        ValueError: If client type is not supported

    Note:
        FakeLLMAPIClient (type="fake") returns random text and will break optimization.
    """
    adapter_map = {
        "albert": AlbertDSPyAdapter,
        "scaleway": ScalewayDSPyAdapter,
        "ollama": OllamaDSPyAdapter,
        "vllm": VllmDSPyAdapter,
        "openai": ScalewayDSPyAdapter,  # Scaleway uses OpenAI client
    }

    adapter_class = adapter_map.get(client.type)
    if adapter_class is None:
        raise ValueError(
            f"Unsupported client type: {client.type}. "
            f"Supported types: {list(adapter_map.keys())}"
        )

    return adapter_class(client)
