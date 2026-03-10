#!/usr/bin/env python3
"""Constraint Coherence Benchmark

Each test prompt runs 6 times:
  S0        bare prompt (temoin / control)
  S1..S5    prompt + reasoning scaffold

Default provider: OpenRouter (set OPENROUTER_API_KEY env var).

Usage:
    OPENROUTER_API_KEY=sk-... python3 run_benchmark.py --model meta-llama/llama-3.3-70b-instruct:free

Private local provider (not in repo):
    python3 run_benchmark.py --provider zo --model claude-haiku-4-5-20251001
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent


# ---------------------------------------------------------------------------
# OpenRouter (public default)
# ---------------------------------------------------------------------------

def call_openrouter(prompt: str, model: str, temperature: float, max_tokens: Optional[int]):
    key = os.environ.get("OPENROUTER_API_KEY", "")
    if not key:
        raise SystemExit("Error: set OPENROUTER_API_KEY environment variable")

    payload: dict = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
    }
    if max_tokens is not None:
        payload["max_tokens"] = max_tokens

    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "X-Title": "constraint-coherence-benchmark",
        },
        method="POST",
    )

    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            body = json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        err = exc.read().decode("utf-8", "replace")
        raise RuntimeError(f"OpenRouter HTTP {exc.code}: {err}") from exc

    ms = int((time.time() - t0) * 1000)

    text = ""
    choices = body.get("choices", [])
    if choices:
        content = choices[0].get("message", {}).get("content", "")
        if isinstance(content, str):
            text = content
        elif isinstance(content, list):
            text = "".join(b.get("text", "") for b in content if isinstance(b, dict))

    return text, ms, body


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="Constraint Coherence Benchmark")
    ap.add_argument("--model", required=True,
                    help="Model ID (e.g. meta-llama/llama-3.3-70b-instruct:free)")
    ap.add_argument("--provider", default="openrouter", choices=["openrouter", "zo"],
                    help="Provider (default: openrouter)")
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--max-tokens", type=int, default=None)
    ap.add_argument("--output", default="runs/results.csv",
                    help="Output CSV path (JSONL written alongside)")
    args = ap.parse_args()

    tests = json.loads((ROOT / "data/tests.json").read_text())
    scaffolds = json.loads((ROOT / "data/scaffolds.json").read_text())

    # Resolve provider
    if args.provider == "zo":
        try:
            from zo_adapter import call_zo
        except ImportError:
            raise SystemExit(
                "Error: zo_adapter.py not found. "
                "This is a private adapter not included in the repo."
            )
        call = call_zo
    else:
        call = call_openrouter

    # Output files
    out_csv = ROOT / args.output
    out_jsonl = out_csv.with_suffix(".jsonl")
    out_csv.parent.mkdir(parents=True, exist_ok=True)

    total = len(tests) * (1 + len(scaffolds))
    done = 0

    headers = [
        "run_id", "date_utc", "provider", "model",
        "test_id", "scaffold_id", "prompt", "response", "latency_ms",
    ]

    csv_new = not out_csv.exists()
    csv_f = out_csv.open("a", newline="", encoding="utf-8")
    jsonl_f = out_jsonl.open("a", encoding="utf-8")
    writer = csv.DictWriter(csv_f, fieldnames=headers)
    if csv_new:
        writer.writeheader()

    print(f"Model: {args.model}  Provider: {args.provider}  "
          f"Tests: {len(tests)}  Runs per test: {1 + len(scaffolds)}  "
          f"Total calls: {total}\n")

    try:
        for test in tests:
            # 6 calls per test: S0 (temoin) + S1..S5
            runs = [("S0", None)] + [(s["id"], s["text"]) for s in scaffolds]

            for scaffold_id, scaffold_text in runs:
                if scaffold_text:
                    prompt = f"{test['text']}\n\n{scaffold_text}"
                else:
                    prompt = test["text"]

                done += 1
                label = f"[{done}/{total}] {test['id']} x {scaffold_id}"
                print(f"  {label} ...", end=" ", flush=True)

                text, ms, raw = call(prompt, args.model, args.temperature, args.max_tokens)

                now = datetime.now(timezone.utc).isoformat()
                run_id = f"{now}_{test['id']}_{scaffold_id}".replace(":", "-")

                row = {
                    "run_id": run_id,
                    "date_utc": now,
                    "provider": args.provider,
                    "model": args.model,
                    "test_id": test["id"],
                    "scaffold_id": scaffold_id,
                    "prompt": prompt,
                    "response": text,
                    "latency_ms": ms,
                }

                writer.writerow(row)
                csv_f.flush()

                jsonl_f.write(json.dumps(
                    {**row, "raw_response": raw}, ensure_ascii=False
                ) + "\n")
                jsonl_f.flush()

                # Truncate response for console
                preview = text[:80].replace("\n", " ")
                print(f"{ms}ms  \"{preview}...\"")

    finally:
        csv_f.close()
        jsonl_f.close()

    print(f"\nDone: {done} calls")
    print(f"CSV:   {out_csv}")
    print(f"JSONL: {out_jsonl}")


if __name__ == "__main__":
    main()
