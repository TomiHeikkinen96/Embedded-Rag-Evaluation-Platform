from __future__ import annotations

import json
from dataclasses import dataclass
from time import perf_counter
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_OLLAMA_CHAT_URL = "http://localhost:11434/api/chat"


@dataclass(frozen=True)
class OllamaUsage:
    prompt_tokens: int
    output_tokens: int
    total_duration_seconds: float
    load_duration_seconds: float
    prompt_eval_duration_seconds: float
    generation_duration_seconds: float

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.output_tokens

    @property
    def output_tokens_per_second(self) -> float:
        if not self.generation_duration_seconds:
            return 0.0
        return self.output_tokens / self.generation_duration_seconds


@dataclass(frozen=True)
class OllamaChatResult:
    content: str
    usage: OllamaUsage
    wall_seconds: float
    first_token_seconds: float | None
    done_reason: str
    raw_response: dict


def _seconds(nanoseconds: int | None) -> float:
    return (nanoseconds or 0) / 1_000_000_000


class OllamaProvider:
    def __init__(
        self,
        model: str,
        *,
        url: str = DEFAULT_OLLAMA_CHAT_URL,
        timeout_seconds: int = 300,
    ) -> None:
        self.model = model
        self.url = url
        self.timeout_seconds = timeout_seconds

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        stream: bool = False,
        on_token: Callable[[str], None] | None = None,
    ) -> OllamaChatResult:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": stream,
            "think": False,
        }
        request = Request(
            self.url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        started_at = perf_counter()
        first_token_seconds = None
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                if stream:
                    raw_response, content, first_token_seconds = self._read_stream(
                        response, started_at, on_token
                    )
                else:
                    raw_response = json.load(response)
                    content = (raw_response.get("message") or {}).get("content", "")
        except HTTPError as error:
            details = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"Ollama returned HTTP {error.code}: {details}"
            ) from error
        except URLError as error:
            raise RuntimeError(
                "Could not reach Ollama. Start it with `brew services start ollama` "
                f"and confirm the URL {self.url}. Original error: {error.reason}"
            ) from error

        wall_seconds = perf_counter() - started_at
        usage = OllamaUsage(
            prompt_tokens=int(raw_response.get("prompt_eval_count") or 0),
            output_tokens=int(raw_response.get("eval_count") or 0),
            total_duration_seconds=_seconds(raw_response.get("total_duration")),
            load_duration_seconds=_seconds(raw_response.get("load_duration")),
            prompt_eval_duration_seconds=_seconds(
                raw_response.get("prompt_eval_duration")
            ),
            generation_duration_seconds=_seconds(raw_response.get("eval_duration")),
        )
        return OllamaChatResult(
            content=content.strip(),
            usage=usage,
            wall_seconds=wall_seconds,
            first_token_seconds=first_token_seconds,
            done_reason=raw_response.get("done_reason", "unknown"),
            raw_response=raw_response,
        )

    @staticmethod
    def _read_stream(
        response,
        started_at: float,
        on_token: Callable[[str], None] | None,
    ) -> tuple[dict, str, float | None]:
        raw_response: dict = {}
        content_parts: list[str] = []
        first_token_seconds = None

        for raw_line in response:
            if not raw_line.strip():
                continue
            chunk = json.loads(raw_line)
            content = (chunk.get("message") or {}).get("content", "")
            if content:
                if first_token_seconds is None:
                    first_token_seconds = perf_counter() - started_at
                content_parts.append(content)
                if on_token is not None:
                    on_token(content)
            raw_response = chunk

        complete_content = "".join(content_parts)
        raw_response["message"] = {
            "role": "assistant",
            "content": complete_content,
        }
        return raw_response, complete_content, first_token_seconds
