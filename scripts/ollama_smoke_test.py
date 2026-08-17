#!/usr/bin/env python3
"""Send one tiny chat request to the local Ollama server and print metrics."""

from __future__ import annotations

import argparse
import json
import sys

from generation.ollama_provider import DEFAULT_OLLAMA_CHAT_URL, OllamaProvider


DEFAULT_MODEL = "rageval-qwen"
DEFAULT_URL = DEFAULT_OLLAMA_CHAT_URL
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


def print_metrics(result) -> None:
    usage = result.usage
    print("\n[4/4] Usage and timing")
    print(f"  Prompt tokens:       {usage.prompt_tokens}")
    print(f"  Output tokens:       {usage.output_tokens}")
    print(f"  Total tokens:        {usage.total_tokens}")
    print(f"  Wall-clock time:     {result.wall_seconds:.3f} s")
    if result.first_token_seconds is not None:
        print(f"  Time to first token: {result.first_token_seconds:.3f} s")
    print(f"  Ollama total time:   {usage.total_duration_seconds:.3f} s")
    print(f"  Model load time:     {usage.load_duration_seconds:.3f} s")
    print(f"  Prompt eval time:    {usage.prompt_eval_duration_seconds:.3f} s")
    print(f"  Generation time:     {usage.generation_duration_seconds:.3f} s")
    print(f"  Generation speed:    {usage.output_tokens_per_second:.2f} tokens/s")
    print(f"  Completion reason:   {result.done_reason}")


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
        result = OllamaProvider(args.model, url=args.url).chat(
            [{"role": "user", "content": args.prompt}],
            stream=args.stream,
            on_token=lambda token: print(token, end="", flush=True),
        )
    except RuntimeError as error:
        print(f"\nError: {error}", file=sys.stderr)
        return 1

    if args.stream:
        print()
    if not args.stream:
        print("[3/4] Model response")
        print(f"  {result.content}")
    print_metrics(result)

    if args.show_json:
        print("\nComplete Ollama response")
        print(json.dumps(result.raw_response, indent=2, ensure_ascii=False))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
