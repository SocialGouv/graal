import json
import logging
import random
from abc import ABC, abstractmethod
from typing import Optional, Tuple

import httpx
import requests
from groq import Groq
from openai import OpenAI
from pydantic_core import Url

from amendements_intelligents.types import (
    APIKey,
    CredentialsPassword,
    CredentialsUsername,
    TxtContent,
)


class LLMAPIClient(ABC):
    def __init__(self, prefix: str = ""):
        self.name = f"{prefix}_" + "".join(
            random.choices("abcdefghijklmnopqrstuvwxyz", k=5)
        )

    @abstractmethod
    def generate_summary(self, prompt):
        pass


class OllamaAPIClient(LLMAPIClient):
    def __init__(self, model_name: str, endpoint: Url, user: str, password: str):
        super().__init__(prefix="ollama")
        self.model_name = model_name
        self.endpoint = endpoint
        self.user = user
        self.password = password

    def generate_summary(self, prompt: TxtContent) -> str:
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

        response = requests.post(url, json=data, headers=headers, auth=auth, timeout=3)
        if response.status_code == 200:
            return json.loads(response.text)["response"].strip()
        else:
            return f"Failed to get a response. Status code: {response.status_code}"


class VllmAPIClient(LLMAPIClient):
    def __init__(self, model_name: str, vllm_endpoint: Url, user: str, password: str):
        super().__init__(prefix="vllm")
        self.model_name = model_name
        self.vllm_endpoint = vllm_endpoint
        self.user = user
        self.password = password

    def generate_summary(self, prompt: TxtContent) -> str:
        url = self.vllm_endpoint
        headers = {"Content-Type": "application/json"}
        auth = (self.user, self.password)

        data = {
            "model": self.model_name,
            "prompt": prompt,
            "max_tokens": 1024,
            "temperature": 0,
        }

        response = requests.post(url, headers=headers, json=data, auth=auth, timeout=3)
        summary = response.json()["choices"][0]["text"].strip()
        return summary


class GroqAPIClient(LLMAPIClient):
    def __init__(self, model_name: str = "llama-3.1-70b-versatile") -> None:
        super().__init__(prefix="groq")
        self.client = Groq()
        self.model_name = model_name

    def generate_summary(self, prompt: TxtContent) -> str:
        completion = self.client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1024,
            temperature=0,
        )

        content = completion.choices[0].message.content
        return content.strip() if content else ""


class LLMInferenceAPIClient(LLMAPIClient):
    """
    This is a client that can talk to our own LLM inference API.
    See https://github.com/SocialGouv/llm-inference-server to set it up.
    """

    def __init__(
        self,
        url: str,
        auth: Optional[Tuple[CredentialsUsername, CredentialsPassword]] = None,
    ):
        super().__init__(prefix="llm_inference")
        self.url = url
        self.auth = auth

    def generate_summary(self, prompt: TxtContent) -> str:
        headers = {"Content-Type": "application/json"}

        # Create the payload for the request
        payload = {"prompts": [prompt]}

        response = requests.post(
            self.url, json=payload, headers=headers, auth=self.auth, timeout=3
        )

        # Check if the request was successful
        if response.status_code == 200:
            # Extract and return the generated text
            generated_texts = response.json().get("generated_texts", [])
            return generated_texts[0]
        else:
            return f"Failed to get a response. Status code: {response.status_code}"


class FakeLLMAPIClient(LLMAPIClient):
    def __init__(self):
        super().__init__(prefix="fake")

    def generate_summary(self, _prompt: TxtContent) -> str:
        # Generate a random summary
        summary = random.choice(
            [
                "Lorem ipsum dolor sit amet",
                "Consectetur adipiscing elit",
                "Sed do eiusmod tempor incididunt",
            ]
        )
        return summary


class AlbertAPIClient(LLMAPIClient):
    def __init__(self, model_name: str, base_url: httpx.URL, api_key: APIKey):
        super().__init__(prefix="albert")
        self.model_name = model_name
        self.client = OpenAI(base_url=base_url, api_key=api_key)

    def generate_summary(self, prompt: TxtContent) -> str:
        logging.info(f"{self.name} is generating a summary")

        data = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": f"{prompt}"}],
            "stream": False,
            "temperature": 0,
            "n": 1,
        }

        response = self.client.chat.completions.create(**data)
        return response.choices[0].message.content
