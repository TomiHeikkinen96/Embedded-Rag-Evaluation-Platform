#!/usr/bin/env python3
"""Send one tiny chat request to the local Ollama server and print metrics."""

from __future__ import annotations

import argparse
import json
import sys
from time import perf_counter
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_MODEL = "rageval-qwen"
DEFAULT_URL = "http://localhost:11434/api/chat"
DEFAULT_PROMPT = "Your goal is to say hello world. Reply with exactly: Hello, world!"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Call a local Ollama model and display its response and usage metrics."
    )
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Ollama model name.")
    parser.add_argument("--url", default=DEFAULT_URL, help="Ollama chat API URL.")
    parser.add_argument("--prompt", default=DEFAULT_PROMPT, help="User prompt.")
    parser.add_argument(
        "--show-json", action="store_true", help="Also print the complete JSON response."
    )
    parser.add_argument(
        "--stream", action="store_true", help="Print response tokens as Ollama generates them."
    )
    return parser.parse_args()


def seconds(nanoseconds: int | None) -> float:
    return (nanoseconds or 0) / 1_000_000_000


def send_chat_request(
    url: str, model: str, prompt: str, stream: bool
) -> tuple[dict, float, float | None]:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": stream,
        "think": False,
    }
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    started_at = perf_counter()
    first_token_seconds = None
    try:
        with urlopen(request, timeout=300) as response:
            if not stream:
                result = json.load(response)
            else:
                result = {}
                complete_content = []
                for raw_line in response:
                    if not raw_line.strip():
                        continue
                    chunk = json.loads(raw_line)
                    content = (chunk.get("message") or {}).get("content", "")
                    if content:
                        if first_token_seconds is None:
                            first_token_seconds = perf_counter() - started_at
                        complete_content.append(content)
                        print(content, end="", flush=True)
                    result = chunk
                print()
                result["message"] = {
                    "role": "assistant",
                    "content": "".join(complete_content),
                }
    except HTTPError as error:
        details = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Ollama returned HTTP {error.code}: {details}") from error
    except URLError as error:
        raise RuntimeError(
            "Could not reach Ollama. Start it with `brew services start ollama` "
            f"and confirm the URL {url}. Original error: {error.reason}"
        ) from error

    return result, perf_counter() - started_at, first_token_seconds


def print_metrics(
    result: dict, wall_seconds: float, first_token_seconds: float | None
) -> None:
    prompt_tokens = int(result.get("prompt_eval_count") or 0)
    output_tokens = int(result.get("eval_count") or 0)
    output_seconds = seconds(result.get("eval_duration"))
    output_tokens_per_second = output_tokens / output_seconds if output_seconds else 0.0

    print("\n[4/4] Usage and timing")
    print(f"  Prompt tokens:       {prompt_tokens}")
    print(f"  Output tokens:       {output_tokens}")
    print(f"  Total tokens:        {prompt_tokens + output_tokens}")
    print(f"  Wall-clock time:     {wall_seconds:.3f} s")
    if first_token_seconds is not None:
        print(f"  Time to first token: {first_token_seconds:.3f} s")
    print(f"  Ollama total time:   {seconds(result.get('total_duration')):.3f} s")
    print(f"  Model load time:     {seconds(result.get('load_duration')):.3f} s")
    print(f"  Prompt eval time:    {seconds(result.get('prompt_eval_duration')):.3f} s")
    print(f"  Generation time:     {output_seconds:.3f} s")
    print(f"  Generation speed:    {output_tokens_per_second:.2f} tokens/s")
    print(f"  Completion reason:   {result.get('done_reason', 'unknown')}")


def main() -> int:
    args = parse_args()

    print("[1/4] Configuration")
    print(f"  API URL: {args.url}")
    print(f"  Model:   {args.model}")
    print(f"  Prompt:  {args.prompt}")

    request_mode = "streaming" if args.stream else "non-streaming"
    print(f"\n[2/4] Sending {request_mode} chat request...")
    if args.stream:
        print("[3/4] Model response")
        print("  ", end="", flush=True)
    try:
        result, wall_seconds, first_token_seconds = send_chat_request(
            args.url, args.model, args.prompt, args.stream
        )
    except RuntimeError as error:
        print(f"\nError: {error}", file=sys.stderr)
        return 1

    message = result.get("message") or {}
    if not args.stream:
        print("[3/4] Model response")
        print(f"  {message.get('content', '').strip()}")
    print_metrics(result, wall_seconds, first_token_seconds)

    if args.show_json:
        print("\nComplete Ollama response")
        print(json.dumps(result, indent=2, ensure_ascii=False))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
