"""DeepSeek API wrapper with streaming support."""

import json
from collections.abc import AsyncGenerator

import httpx

from app.config import settings


class LLMService:
    def __init__(self):
        self.api_key = settings.deepseek_api_key
        self.base_url = settings.deepseek_base_url
        self.model = settings.deepseek_model
        self.client = httpx.AsyncClient(timeout=60.0)

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def chat_stream(self, messages: list[dict], temperature: float = 0.7, max_tokens: int = 4096) -> AsyncGenerator[dict, None]:
        """Stream chat completion from DeepSeek."""
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }

        async with self.client.stream("POST", f"{self.base_url}/chat/completions", json=payload, headers=self._headers()) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data_str = line[6:]
                if data_str.strip() == "[DONE]":
                    yield {"type": "done"}
                    return
                try:
                    chunk = json.loads(data_str)
                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                    finish_reason = chunk.get("choices", [{}])[0].get("finish_reason")
                    yield {
                        "type": "token",
                        "token": delta.get("content", ""),
                        "finish_reason": finish_reason,
                    }
                    if finish_reason:
                        yield {"type": "done"}
                        return
                except json.JSONDecodeError:
                    continue

    async def chat(self, messages: list[dict], temperature: float = 0.7, max_tokens: int = 4096) -> str:
        """Non-streaming chat completion."""
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }

        response = await self.client.post(f"{self.base_url}/chat/completions", json=payload, headers=self._headers())
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

    async def close(self):
        await self.client.aclose()


llm_service = LLMService()
