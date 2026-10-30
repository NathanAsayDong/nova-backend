"""Compare Claude latency across models and reasoning efforts for one message.

Every combination gets the same text message, a fresh single-turn request (so
no cache or history effects), and N repeats. Reports time to first stream
event, time to first text, and total time.

Usage:
  uv run python scripts/effort_latency_bench.py "what's a good name for a cat?"
  uv run python scripts/effort_latency_bench.py "hello" --models claude-sonnet-5-5 \
      --efforts low medium high --runs 5 --tools
"""
import argparse
import os
import statistics
import time

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

DUMMY_TOOL = {
    "name": "noop",
    "description": "Does nothing. Present only to mimic tool-definition overhead.",
    "input_schema": {"type": "object", "properties": {}},
}


def one_call(client, model, effort, message, max_tokens, n_tools, opts):
    params = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": message}],
    }
    if effort != "none":
        params["output_config"] = {"effort": effort}
    if n_tools:
        params["tools"] = [
            {**DUMMY_TOOL, "name": f"noop_{i}"} for i in range(n_tools)
        ]

    if opts.cache_control:
        params["cache_control"] = {"type": "ephemeral"}
    if opts.web_search:
        params.setdefault("tools", []).append(
            {"type": "web_search_20250305", "name": "web_search", "max_uses": 5}
        )
    if opts.system_tokens:
        # Roughly 1 token per word; stable text so the cache can serve it.
        filler = ("You are Nova, a witty and capable personal assistant. " * 2000)
        words = filler.split()[: opts.system_tokens]
        params["system"] = [{
            "type": "text",
            "text": " ".join(words),
            "cache_control": {"type": "ephemeral"},
        }]
    api = client.messages
    if opts.mcp_url:
        server = {"type": "url", "name": "bench", "url": opts.mcp_url}
        if opts.mcp_token:
            server["authorization_token"] = opts.mcp_token
        params["mcp_servers"] = [server]
        params.setdefault("tools", []).append(
            {"type": "mcp_toolset", "mcp_server_name": "bench"}
        )
        params["betas"] = ["mcp-client-2025-11-20"]
        api = client.beta.messages

    start = time.perf_counter()
    first_event = first_text = None
    out_tokens = 0
    with api.stream(**params) as stream:
        for event in stream:
            now = time.perf_counter() - start
            if first_event is None:
                first_event = now
            if first_text is None and event.type == "content_block_delta":
                if getattr(event.delta, "type", "") == "text_delta":
                    first_text = now
        final = stream.get_final_message()
        out_tokens = final.usage.output_tokens
    total = time.perf_counter() - start
    return first_event, first_text or total, total, out_tokens


def main():
    p = argparse.ArgumentParser()
    p.add_argument("message")
    p.add_argument("--models", nargs="+", default=["claude-sonnet-5-5"])
    p.add_argument("--efforts", nargs="+", default=["low", "medium", "high"],
                   help="low/medium/high/xhigh/max, or 'none' to omit the parameter")
    p.add_argument("--runs", type=int, default=3)
    p.add_argument("--max-tokens", type=int, default=8192)
    p.add_argument("--tools", type=int, nargs="?", const=69, default=0,
                   help="attach N dummy tools (default 69 if flag given)")
    p.add_argument("--cache-control", action="store_true",
                   help="top-level cache_control, like Nova sends")
    p.add_argument("--web-search", action="store_true",
                   help="attach the server-side web_search tool, like Nova")
    p.add_argument("--system-tokens", type=int, default=0,
                   help="add a cached system prompt of about N tokens")
    p.add_argument("--mcp-url", default=None, help="attach one MCP server by URL")
    p.add_argument("--mcp-token", default=os.getenv("BENCH_MCP_TOKEN"))
    args = p.parse_args()

    client = Anthropic(api_key=os.getenv("CLAUDE_API_KEY"))
    print(f"message: {args.message!r}  runs={args.runs}  tools={args.tools}  "
          f"cache_control={args.cache_control}  web_search={args.web_search}  "
          f"system_tokens={args.system_tokens}  mcp={bool(args.mcp_url)}\n")
    header = f"{'model':<22}{'effort':<8}{'1st event':>10}{'1st text':>10}{'total':>9}{'out tok':>9}"
    print(header)
    print("-" * len(header))
    for model in args.models:
        for effort in args.efforts:
            rows = []
            for _ in range(args.runs):
                try:
                    rows.append(one_call(client, model, effort, args.message,
                                         args.max_tokens, args.tools, args))
                except Exception as e:
                    print(f"{model:<22}{effort:<8} ERROR: {str(e)[:90]}")
                    break
            if not rows:
                continue
            med = lambda i: statistics.median(r[i] for r in rows)
            print(f"{model:<22}{effort:<8}{med(0):>9.2f}s{med(1):>9.2f}s"
                  f"{med(2):>8.2f}s{med(3):>9.0f}")


if __name__ == "__main__":
    main()
