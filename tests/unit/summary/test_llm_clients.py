from unittest.mock import MagicMock, patch

import pytest
import requests
from requests.models import Response

from amendements_intelligents.summary.llm_clients import (
    GroqAPIClient,
    LLMInferenceAPIClient,
    VllmAPIClient,
)
from amendements_intelligents.types import TxtContent


@pytest.fixture
def vllm_client():
    return VllmAPIClient(
        model_name="test-model",
        vllm_endpoint="https://test-host/v1/completions",
        user="test-user",
        password="test-password",
    )


@pytest.fixture
def groq_client():
    return GroqAPIClient()


@pytest.fixture
def llm_inference_client():
    return LLMInferenceAPIClient(url="https://test-inference-api/v1/generate")


def test_generate_summary(vllm_client):
    prompt = "Test prompt"
    expected_summary = "Test summary"

    response_mock = Response()
    response_mock.status_code = 200
    response_mock._content = b'{"choices": [{"text": "Test summary"}]}'

    with patch.object(requests, "post", return_value=response_mock) as mock_post:
        summary = vllm_client.generate_summary(prompt)
        mock_post.assert_called_once_with(
            "https://test-host/v1/completions",
            headers={"Content-Type": "application/json"},
            json={
                "model": "test-model",
                "prompt": prompt,
                "max_tokens": 1024,
                "temperature": 0,
            },
            auth=("test-user", "test-password"),
            timeout=180,
        )
        assert summary == expected_summary


def test_groq_api_client_generate_summary(groq_client):
    prompt = TxtContent("This is a test prompt.")
    expected_summary = "This is a test summary."

    # Mock the Groq client and its response
    with patch.object(
        groq_client.client.chat.completions,
        "create",
        return_value=MagicMock(
            choices=[MagicMock(message=MagicMock(content=expected_summary))]
        ),
    ) as mock_create:
        summary = groq_client.generate_summary(prompt)

        mock_create.assert_called_once_with(
            model=groq_client.model_name,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1024,
            temperature=0,
        )
        assert summary == expected_summary


def test_llm_inference_api_client_generate_summary(llm_inference_client):
    prompt = TxtContent("This is a test prompt.")
    expected_summary = "This is a test summary."

    response_mock = Response()
    response_mock.status_code = 200
    response_mock._content = b'{"generated_texts": ["This is a test summary."]}'

    with patch.object(requests, "post", return_value=response_mock) as mock_post:
        summary = llm_inference_client.generate_summary(prompt)
        mock_post.assert_called_once_with(
            "https://test-inference-api/v1/generate",
            json={"prompts": [prompt]},
            timeout=180,
        )
        assert summary == expected_summary


def test_llm_inference_api_client_generate_summary_failure(llm_inference_client):
    prompt = TxtContent("This is a test prompt.")

    response_mock = Response()
    response_mock.status_code = 500
    response_mock._content = b""

    with patch.object(requests, "post", return_value=response_mock) as mock_post:
        summary = llm_inference_client.generate_summary(prompt)
        mock_post.assert_called_once_with(
            "https://test-inference-api/v1/generate",
            json={"prompts": [prompt]},
            timeout=180,
        )
        assert summary == "Failed to get a response. Status code: 500"
