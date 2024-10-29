import logging
import queue
from concurrent.futures import ThreadPoolExecutor
from typing import List

from amendements_intelligents.summary.llm_clients import LLMAPIClient


class SummaryGenerationLoadBalancer:
    def __init__(self, clients: List[LLMAPIClient], max_retries: int = 3):
        self.client_pool: queue.Queue[LLMAPIClient] = queue.Queue()
        for client in clients:
            self.client_pool.put(client)
        self.max_retries = max_retries
        self.summary_count = 0  # Initialize summary count

    def _obtain_client(self) -> LLMAPIClient:
        return self.client_pool.get()

    def _put_client_back(self, client: LLMAPIClient):
        self.client_pool.put(client)

    def generate_summary(self, prompt: str) -> str:
        retries = 0
        while retries < self.max_retries:
            client = self._obtain_client()
            try:
                result = client.generate_summary(prompt)
                self._put_client_back(client)
                self.summary_count += 1  # Increment summary count
                if self.summary_count % 10 == 0:
                    print(f"Summaries generated: {self.summary_count}")
                return result
            except Exception as e:
                logging.error(f"Error with client {client.name}: {e}")
                retries += 1
                if retries < self.max_retries:
                    self._put_client_back(client)
                else:
                    logging.warning(
                        f"Removing client {client} from pool after {self.max_retries} retries."
                    )
                    retries = 0
        return "All clients failed after retries."

    def generate_summaries_concurrent(self, prompts: List[str]) -> List[str]:
        with ThreadPoolExecutor(max_workers=len(prompts)) as executor:
            futures = [
                executor.submit(self.generate_summary, prompt) for prompt in prompts
            ]
            results = [future.result() for future in futures]
        return results
