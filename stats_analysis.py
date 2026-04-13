#!/usr/bin/env python3
"""Statistical analysis for Constraint Coherence Benchmark.

Calculates correct-answer rates (recommendation-based) with 95% Wilson
confidence intervals per scaffold per model, separated by T1-T5 and T6.
Fisher's exact tests for all scaffolds vs S0.

Primary metric: recommendation rate (drive for T1-T5, walk for T6).
Strict pass is a secondary validation metric only.
"""
import json
import csv
import os
import math
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parent

def wilson_ci(successes, n, z=1.96):
    """Wilson score interval for a binomial proportion."""
    if n == 0:
        return 0.0, 0.0, 0.0
    p = successes / n
    denom = 1 + z**2 / n
    center = (p + z**2 / (2*n)) / denom
    spread = z * math.sqrt(p*(1-p)/n + z**2/(4*n**2)) / denom
    return p, max(0, center - spread), min(1, center + spread)


def fisher_exact_2x2(table):
    """Two-sided Fisher's exact test for a 2x2 contingency table."""
    a, b = table[0]
    c, d = table[1]

    def log_fac(x):
        return sum(math.log(i) for i in range(1, x+1))

    def hyper_lp(a, b, c, d):
        n = a + b + c + d
        return (log_fac(a+b) + log_fac(c+d) + log_fac(a+c) + log_fac(b+d)
                - log_fac(n) - log_fac(a) - log_fac(b) - log_fac(c) - log_fac(d))

    obs_lp = hyper_lp(a, b, c, d)
    row1, col1 = a + b, a + c
    row2 = c + d
    p_val = 0.0
    for i in range(min(row1, col1) + 1):
        j, k, l = row1 - i, col1 - i, row2 - (col1 - i)
        if j < 0 or k < 0 or l < 0:
            continue
        lp = hyper_lp(i, j, k, l)
        if lp <= obs_lp + 1e-10:
            p_val += math.exp(lp)

    odds = (a*d) / (b*c) if b*c > 0 else (float('inf') if a*d > 0 else 0.0)
    return odds, min(1.0, p_val)


def main():
    with open(ROOT / "runs/scored_combined_all_models.json") as f:
        all_results = json.load(f)

    print(f"Loaded {len(all_results)} results")

    model_map = {"haiku-4.5": "haiku", "sonnet-4.5": "sonnet"}
    scaffold_order = ["S0", "S1", "S2", "S3", "S4", "S5"]

    grouped = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    for r in all_results:
        model = model_map.get(r.get("model", "haiku-4.5"), "haiku")
        scaffold = r["scaffold_id"]
        test_group = "T6" if r["test_id"] == "T6" else "T1-T5"
        grouped[model][test_group][scaffold].append(r)

    os.makedirs(ROOT / "analysis", exist_ok=True)

    # ---- T1-T5: correct = recommendation == "drive" ----
    print("\n" + "=" * 70)
    print("T1-T5 CORRECT-ANSWER RATES (% recommending drive)")
    print("=" * 70)

    rows = []
    for model in ["haiku", "sonnet"]:
        print(f"\n--- {model.upper()} ---")
        for scaffold in scaffold_order:
            items = grouped[model]["T1-T5"][scaffold]
            n = len(items)
            correct = sum(1 for r in items if r.get("recommendation") == "drive")
            rate, ci_lo, ci_hi = wilson_ci(correct, n)
            print(f"  {scaffold}: {correct}/{n} = {rate:.0%}  [{ci_lo:.3f}, {ci_hi:.3f}]")
            rows.append({"model": model, "scaffold": scaffold, "n": n, "correct": correct,
                          "correct_rate": round(rate, 4), "ci_lower": round(ci_lo, 4), "ci_upper": round(ci_hi, 4)})

    with open(ROOT / "analysis/scaffold_stats.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["model","scaffold","n","correct","correct_rate","ci_lower","ci_upper"])
        w.writeheader()
        w.writerows(rows)
    print(f"\nCSV: analysis/scaffold_stats.csv")

    # ---- T6: walk / drive / ambiguous ----
    print("\n" + "=" * 70)
    print("T6 RESPONSE DISTRIBUTION (walk = correct)")
    print("=" * 70)

    rows_t6 = []
    for model in ["haiku", "sonnet"]:
        print(f"\n--- {model.upper()} ---")
        for scaffold in scaffold_order:
            items = grouped[model]["T6"][scaffold]
            n = len(items)
            walk = sum(1 for r in items if r.get("recommendation") == "walk")
            drive = sum(1 for r in items if r.get("recommendation") == "drive")
            ambig = n - walk - drive
            rate, ci_lo, ci_hi = wilson_ci(walk, n)
            print(f"  {scaffold}: walk={walk} drive={drive} ambig={ambig}  walk%={rate:.0%}")
            rows_t6.append({"model": model, "scaffold": scaffold, "n": n,
                            "walk": walk, "drive": drive, "ambiguous": ambig,
                            "walk_rate": round(rate, 4), "ci_lower": round(ci_lo, 4), "ci_upper": round(ci_hi, 4)})

    with open(ROOT / "analysis/scaffold_stats_t6.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["model","scaffold","n","walk","drive","ambiguous","walk_rate","ci_lower","ci_upper"])
        w.writeheader()
        w.writerows(rows_t6)
    print(f"\nCSV: analysis/scaffold_stats_t6.csv")

    # ---- Fisher's exact: each scaffold vs S0 (T1-T5) ----
    print("\n" + "=" * 70)
    print("FISHER'S EXACT: each scaffold vs S0 (T1-T5)")
    print("=" * 70)

    fisher = {}
    for model in ["haiku", "sonnet"]:
        print(f"\n--- {model.upper()} ---")
        s0 = grouped[model]["T1-T5"]["S0"]
        s0_c = sum(1 for r in s0 if r.get("recommendation") == "drive")
        s0_w = len(s0) - s0_c
        for scaffold in ["S1","S2","S3","S4","S5"]:
            sx = grouped[model]["T1-T5"][scaffold]
            sx_c = sum(1 for r in sx if r.get("recommendation") == "drive")
            sx_w = len(sx) - sx_c
            table = [[sx_c, sx_w], [s0_c, s0_w]]
            odds, p = fisher_exact_2x2(table)
            sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "ns"
            print(f"  {scaffold} vs S0: p={p:.4f} {sig}")
            fisher[f"{scaffold.lower()}_vs_s0_{model}"] = {
                "model": model, "comparison": f"{scaffold} vs S0",
                "contingency_table": table,
                "sx_rate": round(sx_c/len(sx), 4), "s0_rate": round(s0_c/len(s0), 4),
                "odds_ratio": float(odds) if odds != float('inf') else "Infinity",
                "p_value": round(p, 6), "significant_005": p < 0.05}

    with open(ROOT / "analysis/fisher_test_results.json", "w") as f:
        json.dump(fisher, f, indent=2)
    print(f"\nJSON: analysis/fisher_test_results.json")

    # ---- Fisher's exact: T6 scaffolds vs S0 + T1-T5 vs T6 within scaffold ----
    print("\n" + "=" * 70)
    print("FISHER'S EXACT: T6 scaffold vs S0 + T1-T5 vs T6 within scaffold")
    print("=" * 70)

    fisher_t6 = {}
    for model in ["haiku", "sonnet"]:
        print(f"\n--- {model.upper()} ---")
        s0 = grouped[model]["T6"]["S0"]
        s0_walk = sum(1 for r in s0 if r.get("recommendation") == "walk")
        s0_other = len(s0) - s0_walk
        for scaffold in ["S1","S2","S3","S4","S5"]:
            sx = grouped[model]["T6"][scaffold]
            sx_walk = sum(1 for r in sx if r.get("recommendation") == "walk")
            sx_other = len(sx) - sx_walk
            table = [[sx_walk, sx_other], [s0_walk, s0_other]]
            odds, p = fisher_exact_2x2(table)
            sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "ns"
            print(f"  T6 {scaffold} vs S0: p={p:.4f} {sig}")
            fisher_t6[f"{scaffold.lower()}_vs_s0_{model}"] = {
                "model": model, "comparison": f"{scaffold} vs S0",
                "contingency_table": table,
                "sx_walk_rate": round(sx_walk/len(sx), 4),
                "s0_walk_rate": round(s0_walk/len(s0), 4),
                "odds_ratio": float(odds) if odds != float('inf') else "Infinity",
                "p_value": round(p, 6), "significant_005": p < 0.05}

        for scaffold in scaffold_order:
            t15 = grouped[model]["T1-T5"][scaffold]
            t6 = grouped[model]["T6"][scaffold]
            t15_c = sum(1 for r in t15 if r.get("recommendation") == "drive")
            t6_c = sum(1 for r in t6 if r.get("recommendation") == "walk")
            table = [[t15_c, len(t15)-t15_c], [t6_c, len(t6)-t6_c]]
            odds, p = fisher_exact_2x2(table)
            sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "ns"
            print(f"  T1-T5 vs T6 ({scaffold}): p={p:.4f} {sig}")
            fisher_t6[f"t15_vs_t6_{scaffold.lower()}_{model}"] = {
                "model": model, "comparison": f"T1-T5 vs T6 ({scaffold})",
                "contingency_table": table,
                "t15_correct_rate": round(t15_c/len(t15), 4),
                "t6_correct_rate": round(t6_c/len(t6), 4),
                "odds_ratio": float(odds) if odds != float('inf') else "Infinity",
                "p_value": round(p, 6), "significant_005": p < 0.05}

    with open(ROOT / "analysis/fisher_test_results_t6.json", "w") as f:
        json.dump(fisher_t6, f, indent=2)
    print(f"\nJSON: analysis/fisher_test_results_t6.json")

    print("\nAnalysis complete.")


if __name__ == "__main__":
    main()
