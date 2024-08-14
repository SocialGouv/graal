from abc import ABC, abstractmethod

import requests
from pydantic_core import Url

from amendements_intelligents.types import TxtContent


class LLMApiClient(ABC):
    @abstractmethod
    def generate_summary(self, prompt):
        pass


class VLLMApiClient(LLMApiClient):
    def __init__(self, model_name: str, vllm_endpoint: Url, user: str, password: str):
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
            "max_tokens": 1000,
            "temperature": 0,
        }

        response = requests.post(url, headers=headers, json=data, auth=auth)
        summary = response.json()["choices"][0]["text"].strip()
        return summary
