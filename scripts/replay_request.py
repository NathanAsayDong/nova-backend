"""Replay a real Nova request (dumped via NOVA_DUMP_REQUEST) and ablate it.

Each variant starts from the exact dumped request and removes one thing, so
the variant that gets faster than 'full' names the cost. Every variant gets one
warmup call (so the prompt cache is populated, as in real Nova turns) and then
N timed runs. Reports median time to first stream event / first text / total.

Usage:
  NOVA_DUMP_REQUEST=/tmp/nova_req.json  (set on the tower, copy the file here)
  uv run python scripts/replay_request.py /tmp/nova_req.json --runs 4
  uv run python scripts/replay_request.py /tmp/nova_req.json --only full no_tools
If the dump has MCP servers, set REPLAY_MCP_TOKEN or use the no_mcp variants.
"""
import argparse
import copy
import json
import os
import statistics
import time

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()
MCP_BETA = "mcp-client-2025-11-20"


def variants(base):
    def drop_tools(p, keep=lambda t: False):
        p["tools"] = [t for t in p.get("tools", []) if keep(t)]
        if not p["tools"]:
            del p["tools"]

    out = {"full": lambda p: None}
    out["no_mcp"] = lambda p: (
        p.pop("mcp_servers", None),
        drop_tools(p, lambda t: t.get("type") != "mcp_toolset"),
    )
    out["no_websearch"] = lambda p: drop_tools(
        p, lambda t: not str(t.get("type", "")).startswith("web_search")
    )
    out["no_tools"] = lambda p: (p.pop("mcp_servers", None), drop_tools(p))
    out["no_system"] = lambda p: p.pop("system", None)
    out["no_history"] = lambda p: p.update(messages=p["messages"][-1:])
    out["no_cache_control"] = lambda p: p.pop("cache_control", None)
    out["low_effort"] = lambda p: p.update(output_config={"effort": "low"})
    out["no_effort"] = lambda p: p.pop("output_config", None)
    out["bare"] = lambda p: (
        p.pop("mcp_servers", None), p.pop("system", None), p.pop("cache_control", None),
        p.pop("output_config", None), drop_tools(p),
        p.update(messages=p["messages"][-1:]),
    )
    return out


def one_call(client, params):
    use_beta = bool(params.get("mcp_servers"))
    api = client.beta.messages if use_beta else client.messages
    kw = {"betas": [MCP_BETA]} if use_beta else {}
    t0 = time.monotonic()
    first_event = first_text = None
    usage = None
    with api.stream(**kw, **params) as stream:
        for ev in stream:
            now = time.monotonic() - t0
            if first_event is None:
                first_event = now
            if first_text is None and ev.type == "text":
                first_text = now
        usage = stream.get_final_message().usage
    return first_event, first_text, time.monotonic() - t0, usage


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dump")
    ap.add_argument("--runs", type=int, default=4)
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--max-tokens", type=int, default=300,
                    help="cap output so totals compare; first-event is unaffected")
    a = ap.parse_args()
    dump = json.load(open(a.dump))
    base = dump["params"]
    token = os.getenv("REPLAY_MCP_TOKEN")
    client = Anthropic()
    for name, mutate in variants(base).items():
        if a.only and name not in a.only:
            continue
        p = copy.deepcopy(base)
        mutate(p)
        p["max_tokens"] = a.max_tokens
        for s in p.get("mcp_servers") or []:
            if token:
                s["authorization_token"] = token
            else:
                s.pop("authorization_token", None)
        try:
            one_call(client, p)  # warmup
            rows = [one_call(client, p) for _ in range(a.runs)]
        except Exception as e:
            print(f"{name:18s} ERROR {type(e).__name__}: {str(e)[:120]}")
            continue
        fe = statistics.median(r[0] for r in rows)
        ft = statistics.median(r[1] or r[2] for r in rows)
        tot = statistics.median(r[2] for r in rows)
        u = rows[-1][3]
        print(f"{name:18s} first_event={fe:.2f}s first_text={ft:.2f}s total={tot:.2f}s "
              f"in={u.input_tokens} cache_read={u.cache_read_input_tokens} "
              f"cache_write={u.cache_creation_input_tokens}")


if __name__ == "__main__":
    main()
