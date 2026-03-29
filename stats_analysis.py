#!/usr/bin/env python3
"""Statistical analysis for Constraint Coherence Benchmark.

Calculates:
1. Pass rates with 95% binomial confidence intervals per scaffold per model
2. Fisher's exact test (S2 vs S0) for each model
3. Exports results to CSV and JSON
"""
import json
import csv
import os
from pathlib import Path
from scipy import stats
from collections import defaultdict

ROOT = Path(__file__).resolve().parent

def binomial_ci(successes, n, alpha=0.05):
    """Clopper-Pearson exact binomial confidence interval."""
    if n == 0:
        return 0.0, 0.0, 0.0
    p_hat = successes / n
    ci_lower = stats.beta.ppf(alpha / 2, successes, n - successes + 1) if successes > 0 else 0.0
    ci_upper = stats.beta.ppf(1 - alpha / 2, successes + 1, n - successes) if successes < n else 1.0
    return p_hat, ci_lower, ci_upper


def main():
    with open(ROOT / "runs/scored_combined_all_models.json") as f:
        all_results = json.load(f)

    print(f"Loaded {len(all_results)} results")

    # Map model names
    model_map = {
        "haiku-4.5": "haiku",
        "sonnet-4.5": "sonnet",
    }

    # Group by model and scaffold
    grouped = defaultdict(lambda: defaultdict(list))
    for r in all_results:
        model = model_map.get(r.get("model", "haiku-4.5"), "haiku")
        scaffold = r["scaffold_id"]
        grouped[model][scaffold].append(r)

    # Calculate stats
    rows = []
    scaffold_order = ["S0", "S1", "S2", "S3", "S4", "S5"]

    print("\n" + "=" * 70)
    print("PASS RATES WITH 95% CONFIDENCE INTERVALS")
    print("=" * 70)

    for model in ["haiku", "sonnet"]:
        print(f"\n--- {model.upper()} ---")
        print(f"{'Scaffold':<10} {'n':>4} {'Pass':>5} {'Rate':>8} {'95% CI':>20}")
        print("-" * 55)

        for scaffold in scaffold_order:
            items = grouped[model][scaffold]
            n = len(items)
            passes = sum(1 for r in items if r["strict_pass"])
            p_hat, ci_lower, ci_upper = binomial_ci(passes, n)

            print(f"{scaffold:<10} {n:>4} {passes:>5} {p_hat:>7.1%} [{ci_lower:.3f}, {ci_upper:.3f}]")

            rows.append({
                "model": model,
                "scaffold": scaffold,
                "n": n,
                "passes": passes,
                "pass_rate": round(p_hat, 4),
                "ci_lower": round(ci_lower, 4),
                "ci_upper": round(ci_upper, 4),
            })

    # Write CSV
    os.makedirs(ROOT / "analysis", exist_ok=True)
    csv_path = ROOT / "analysis/scaffold_stats.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["model", "scaffold", "n", "passes", "pass_rate", "ci_lower", "ci_upper"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nCSV written to {csv_path}")

    # Fisher's exact test: S2 vs S0
    print("\n" + "=" * 70)
    print("FISHER'S EXACT TEST: S2 vs S0")
    print("=" * 70)

    fisher_results = {}

    for model in ["haiku", "sonnet"]:
        s2_items = grouped[model]["S2"]
        s0_items = grouped[model]["S0"]

        s2_pass = sum(1 for r in s2_items if r["strict_pass"])
        s2_fail = len(s2_items) - s2_pass
        s0_pass = sum(1 for r in s0_items if r["strict_pass"])
        s0_fail = len(s0_items) - s0_pass

        contingency = [[s2_pass, s2_fail], [s0_pass, s0_fail]]
        odds_ratio, p_value = stats.fisher_exact(contingency)

        print(f"\n--- {model.upper()} ---")
        print(f"S2: {s2_pass}/{len(s2_items)} = {s2_pass/len(s2_items):.1%}")
        print(f"S0: {s0_pass}/{len(s0_items)} = {s0_pass/len(s0_items):.1%}")
        print(f"Contingency table: {contingency}")
        print(f"Odds ratio: {odds_ratio:.4f}")
        print(f"p-value: {p_value:.6f}")
        print(f"Significant (p < 0.05): {'YES' if p_value < 0.05 else 'NO'}")
        print(f"Significant (p < 0.01): {'YES' if p_value < 0.01 else 'NO'}")
        print(f"Significant (p < 0.001): {'YES' if p_value < 0.001 else 'NO'}")

        fisher_results[f"s2_vs_s0_{model}"] = {
            "model": model,
            "contingency_table": contingency,
            "s2_pass_rate": s2_pass / len(s2_items),
            "s0_pass_rate": s0_pass / len(s0_items),
            "odds_ratio": float(odds_ratio) if odds_ratio != float('inf') else "Infinity",
            "p_value": p_value,
            "significant_005": p_value < 0.05,
            "significant_001": p_value < 0.01,
            "significant_0001": p_value < 0.001,
        }

    # Additional pairwise comparisons (all scaffolds vs S0, per model)
    print("\n" + "=" * 70)
    print("ALL PAIRWISE COMPARISONS vs S0 (Fisher's exact)")
    print("=" * 70)

    for model in ["haiku", "sonnet"]:
        print(f"\n--- {model.upper()} ---")
        print(f"{'Comparison':<12} {'OR':>10} {'p-value':>12} {'Sig':>5}")
        print("-" * 42)

        s0_items = grouped[model]["S0"]
        s0_pass = sum(1 for r in s0_items if r["strict_pass"])
        s0_fail = len(s0_items) - s0_pass

        for scaffold in ["S1", "S2", "S3", "S4", "S5"]:
            sx_items = grouped[model][scaffold]
            sx_pass = sum(1 for r in sx_items if r["strict_pass"])
            sx_fail = len(sx_items) - sx_pass

            contingency = [[sx_pass, sx_fail], [s0_pass, s0_fail]]
            odds_ratio, p_value = stats.fisher_exact(contingency)

            sig = "***" if p_value < 0.001 else "**" if p_value < 0.01 else "*" if p_value < 0.05 else "ns"
            or_str = f"{odds_ratio:.2f}" if odds_ratio != float('inf') else "Inf"
            print(f"{scaffold} vs S0   {or_str:>10} {p_value:>12.6f} {sig:>5}")

            fisher_results[f"{scaffold.lower()}_vs_s0_{model}"] = {
                "model": model,
                "comparison": f"{scaffold} vs S0",
                "contingency_table": contingency,
                "odds_ratio": float(odds_ratio) if odds_ratio != float('inf') else "Infinity",
                "p_value": p_value,
                "significant_005": p_value < 0.05,
            }

    # Save Fisher results
    fisher_path = ROOT / "analysis/fisher_test_results.json"
    # Convert numpy types to native Python types
    def convert_types(obj):
        if isinstance(obj, dict):
            return {k: convert_types(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_types(v) for v in obj]
        elif isinstance(obj, (bool,)):
            return obj
        elif hasattr(obj, 'item'):
            return obj.item()
        return obj

    with open(fisher_path, "w") as f:
        json.dump(convert_types(fisher_results), f, indent=2)
    print(f"\nFisher results written to {fisher_path}")

    # Cross-model comparison (Haiku vs Sonnet overall)
    print("\n" + "=" * 70)
    print("CROSS-MODEL COMPARISON (Haiku vs Sonnet)")
    print("=" * 70)

    for scaffold in scaffold_order:
        h_items = grouped["haiku"][scaffold]
        s_items = grouped["sonnet"][scaffold]
        h_pass = sum(1 for r in h_items if r["strict_pass"])
        s_pass = sum(1 for r in s_items if r["strict_pass"])
        h_rate = h_pass / len(h_items) if h_items else 0
        s_rate = s_pass / len(s_items) if s_items else 0
        diff = s_rate - h_rate
        print(f"{scaffold}: Haiku={h_rate:.0%} ({h_pass}/{len(h_items)}), Sonnet={s_rate:.0%} ({s_pass}/{len(s_items)}), diff={diff:+.0%}")

    print("\nPhase 4 analysis complete.")


if __name__ == "__main__":
    main()
