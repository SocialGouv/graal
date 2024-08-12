import requests


class VLLMClient:
    def __init__(self, model_name, host, user, password):
        self.model_name = model_name
        self.host = host
        self.user = user
        self.password = password

    def generate_summary(self, prompt):
        url = f"https://{self.host}/v1/completions"
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
