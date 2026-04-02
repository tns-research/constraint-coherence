#!/usr/bin/env python3
"""Score all T6 runs and compute scaffold stats + Fisher tests.

Reads t6_haiku_run{1-25}.jsonl and t6_sonnet_run{1-15}.jsonl,
scores with direction-aware scorer, writes:
  - runs/t6_scored_full.json
  - analysis/scaffold_stats_t6_full.csv
  - analysis/fisher_test_results_t6_full.json
"""
import json
import csv
import math
from pathlib import Path
from collections import defaultdict
from score_results import score_response
from scipy.stats import fisher_exact

ROOT = Path(__file__).resolve().parent
RUNS_DIR = ROOT / "runs"
ANALYSIS_DIR = ROOT / "analysis"

CORRECT_ANSWER = "walk"  # T6 inverse

HAIKU_FILES = [f"t6_haiku_run{i}.jsonl" for i in range(1, 26)]
SONNET_FILES = [f"t6_sonnet_run{i}.jsonl" for i in range(1, 16)]


def wilson_ci(k, n, z=1.96):
    if n == 0:
        return 0.0, 0.0
    p = k / n
    denom = 1 + z**2 / n
    center = (p + z**2 / (2 * n)) / denom
    spread = z * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denom
    return max(0.0, center - spread), min(1.0, center + spread)


def score_all():
    results = []

    for model, files in [("haiku", HAIKU_FILES), ("sonnet", SONNET_FILES)]:
        for fname in files:
            path = RUNS_DIR / fname
            if not path.exists():
                continue
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    r = json.loads(line)
                    if r.get("test_id") != "T6":
                        continue
                    scores = score_response(r["test_id"], r["scaffold_id"], r["response"], CORRECT_ANSWER)
                    results.append({
                        "model": model,
                        "run_file": fname,
                        "test_id": r["test_id"],
                        "scaffold_id": r["scaffold_id"],
                        "latency_ms": r["latency_ms"],
                        "response": r["response"],
                        **scores,
                    })

    return results


def scaffold_stats(results):
    by = defaultdict(lambda: {"n": 0, "passes": 0})
    for r in results:
        key = (r["model"], r["scaffold_id"])
        by[key]["n"] += 1
        if r["strict_pass"]:
            by[key]["passes"] += 1

    rows = []
    for (model, scaffold), d in sorted(by.items()):
        n, k = d["n"], d["passes"]
        rate = k / n if n > 0 else 0.0
        lo, hi = wilson_ci(k, n)
        rows.append({
            "model": model, "scaffold": scaffold,
            "n": n, "passes": k, "pass_rate": rate,
            "ci_lower": lo, "ci_upper": hi,
        })
    return rows


def fisher_tests(results):
    """Fisher exact test: each scaffold vs S0 per model."""
    tests_out = []
    for model in ["haiku", "sonnet"]:
        model_results = [r for r in results if r["model"] == model]
        s0 = [r for r in model_results if r["scaffold_id"] == "S0"]
        s0_pass = sum(1 for r in s0 if r["strict_pass"])
        s0_fail = len(s0) - s0_pass

        for sid in ["S1", "S2", "S3", "S4", "S5"]:
            sx = [r for r in model_results if r["scaffold_id"] == sid]
            sx_pass = sum(1 for r in sx if r["strict_pass"])
            sx_fail = len(sx) - sx_pass
            table = [[s0_pass, s0_fail], [sx_pass, sx_fail]]
            _, p = fisher_exact(table, alternative="two-sided")
            tests_out.append({
                "model": model, "scaffold": sid,
                "s0_pass": s0_pass, "s0_n": len(s0),
                "sx_pass": sx_pass, "sx_n": len(sx),
                "p_value": float(p),
                "significant": bool(p < 0.05),
            })
    return tests_out


def recommendation_counts(results):
    """Walk/drive/ambiguous counts per model × scaffold."""
    by = defaultdict(lambda: defaultdict(int))
    for r in results:
        key = (r["model"], r["scaffold_id"])
        by[key][r["recommendation"]] += 1
        by[key]["total"] += 1
    return by


def main():
    ANALYSIS_DIR.mkdir(exist_ok=True)

    print("Scoring all T6 runs...")
    results = score_all()
    print(f"Total scored: {len(results)}")

    # Save full scored JSON
    out_json = RUNS_DIR / "t6_scored_full.json"
    with open(out_json, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"Saved: {out_json}")

    # Scaffold stats
    stats = scaffold_stats(results)
    out_csv = ANALYSIS_DIR / "scaffold_stats_t6_full.csv"
    with open(out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["model","scaffold","n","passes","pass_rate","ci_lower","ci_upper"])
        w.writeheader()
        w.writerows(stats)
    print(f"Saved: {out_csv}")

    # Print stats table
    print(f"\n{'model':8} {'scaffold':8} {'n':4} {'passes':7} {'rate':6} {'CI':20}")
    print("-" * 60)
    for s in stats:
        print(f"{s['model']:8} {s['scaffold']:8} {s['n']:4} {s['passes']:7} "
              f"{s['pass_rate']:6.1%} [{s['ci_lower']:.2f}, {s['ci_upper']:.2f}]")

    # Recommendation breakdown
    rec = recommendation_counts(results)
    print(f"\n{'model':8} {'scaffold':8} {'walk':5} {'drive':6} {'ambig':6} {'total':6}")
    print("-" * 50)
    for (model, scaffold) in sorted(rec.keys()):
        d = rec[(model, scaffold)]
        print(f"{model:8} {scaffold:8} {d.get('walk',0):5} {d.get('drive',0):6} "
              f"{d.get('ambiguous',0):6} {d['total']:6}")

    # Fisher tests
    fisher = fisher_tests(results)
    out_fisher = ANALYSIS_DIR / "fisher_test_results_t6_full.json"
    with open(out_fisher, "w") as f:
        json.dump(fisher, f, indent=2)
    print(f"\nSaved: {out_fisher}")

    print("\nFisher tests (scaffold vs S0):")
    for t in fisher:
        sig = "* " if t["significant"] else "  "
        print(f"  {sig}{t['model']:8} {t['scaffold']}: "
              f"S0={t['s0_pass']}/{t['s0_n']}  {t['scaffold']}={t['sx_pass']}/{t['sx_n']}  p={t['p_value']:.3f}")


if __name__ == "__main__":
    main()
