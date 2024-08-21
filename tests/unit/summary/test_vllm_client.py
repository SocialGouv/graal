from unittest.mock import patch

import pytest
import requests
from requests.models import Response

from amendements_intelligents.summary.vllm_client import VLLMApiClient


@pytest.fixture
def vllm_client():
    return VLLMApiClient(
        model_name="test-model",
        vllm_endpoint="https://test-host/v1/completions",
        user="test-user",
        password="test-password",
    )


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
                "max_tokens": 1000,
                "temperature": 0,
            },
            auth=("test-user", "test-password"),
        )
        assert summary == expected_summary
