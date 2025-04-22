import json
import logging
import random
from abc import ABC, abstractmethod
from typing import Optional

import httpx
import requests
from openai import OpenAI
from pydantic_core import Url

from graal.custom_types import (
    APIKey,
    LLMType,
    TxtContent,
)


class LLMAPIClient(ABC):
    def __init__(self, type: LLMType, name: Optional[str] = None):
        self.type = type
        self.name = f"{name or type}_" + "".join(
            random.choices("abcdefghijklmnopqrstuvwxyz", k=5)  # nosec
        )

    @abstractmethod
    def generate_text(self, prompt):
        pass


class OllamaAPIClient(LLMAPIClient):
    def __init__(
        self,
        model_name: str,
        endpoint: Url,
        user: str,
        password: str,
        timeout: int = 10,
        name: Optional[str] = None,
    ):
        super().__init__(type="ollama", name=name)
        self.model_name = model_name
        self.endpoint = endpoint
        self.user = user
        self.password = password
        self.timeout = timeout

    def generate_text(self, prompt: TxtContent) -> str:
        logging.info(f"{self.name} is generating a summary")
        url = self.endpoint

        headers = {"Content-Type": "application/json"}
        auth = (self.user, self.password)

        data = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0,
            },
        }

        response = requests.post(
            url, json=data, headers=headers, auth=auth, timeout=self.timeout
        )
        if response.status_code == 200:
            return json.loads(response.text)["response"].strip()
        else:
            return f"Failed to get a response. Status code: {response.status_code}"


class OpenAIAPIClient(LLMAPIClient):
    def __init__(
        self,
        model_name: str,
        api_key: APIKey,
        base_url: httpx.URL,
        timeout: int = 10,
        name: Optional[str] = None,
    ):
        super().__init__(type="openai", name=name)
        self.model_name = model_name
        self.client = OpenAI(
            base_url=base_url,
            api_key=api_key,
        )
        self.timeout = timeout

    def generate_text(self, prompt: TxtContent) -> str:
        logging.info(f"{self.name} is generating a summary")

        data = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": f"{prompt}"}],
            "stream": False,
            "temperature": 0,
            "n": 1,
            "timeout": self.timeout,
        }

        response = self.client.chat.completions.create(**data)
        return response.choices[0].message.content or ""


class VllmAPIClient(LLMAPIClient):
    def __init__(
        self,
        model_name: str,
        vllm_endpoint: Url,
        user: str,
        password: str,
        name: Optional[str] = None,
    ):
        super().__init__(type="vllm", name=name)
        self.model_name = model_name
        self.vllm_endpoint = vllm_endpoint
        self.user = user
        self.password = password

    def generate_text(self, prompt: TxtContent) -> str:
        url = self.vllm_endpoint
        headers = {"Content-Type": "application/json"}
        auth = (self.user, self.password)

        data = {
            "model": self.model_name,
            "prompt": prompt,
            "max_tokens": 1024,
            "temperature": 0,
        }

        response = requests.post(url, headers=headers, json=data, auth=auth, timeout=10)
        summary = response.json()["choices"][0]["text"].strip()
        return summary


class FakeLLMAPIClient(LLMAPIClient):
    def __init__(
        self,
        name: Optional[str] = None,
    ):
        super().__init__(type="fake", name=name)

    def generate_text(self, _prompt: TxtContent) -> str:
        # Generate a random summary
        summary = random.choice(  # nosec
            [
                "Lorem ipsum dolor sit amet",
                "Consectetur adipiscing elit",
                "Sed do eiusmod tempor incididunt",
            ]
        )
        return summary
