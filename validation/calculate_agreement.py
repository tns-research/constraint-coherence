#!/usr/bin/env python3
"""Calculate inter-rater agreement between auto and manual annotations.

Run after manual_annotations.jsonl is created.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

try:
    from sklearn.metrics import cohen_kappa_score
except ImportError:
    import subprocess
    subprocess.run(["pip", "install", "scikit-learn"], check=True)
    from sklearn.metrics import cohen_kappa_score


def main():
    # Load auto scores
    with open(ROOT / "validation/validation_sample.jsonl") as f:
        auto_items = [json.loads(line) for line in f]

    # Load manual annotations
    manual_path = ROOT / "validation/manual_annotations.jsonl"
    if not manual_path.exists():
        print("ERROR: manual_annotations.jsonl not found.")
        print("Please complete manual annotation first.")
        return

    with open(manual_path) as f:
        manual_items = [json.loads(line) for line in f]

    # Align by sample_id
    auto_by_id = {item["sample_id"]: item for item in auto_items}
    manual_by_id = {item["sample_id"]: item for item in manual_items}

    common_ids = sorted(set(auto_by_id.keys()) & set(manual_by_id.keys()))
    print(f"Matched samples: {len(common_ids)}")

    metrics = [
        "nc_detected",
        "infeasible_option_rejected",
        "goal_achieved_by_recommendation",
        "proxy_drift_present",
        "error_severity",
    ]

    results = {}
    print(f"\n{'Metric':<40} {'Kappa':>8} {'Agreement':>10}")
    print("-" * 60)

    for metric in metrics:
        auto_vals = []
        manual_vals = []
        for sid in common_ids:
            auto_val = auto_by_id[sid]["auto_scores"][metric]
            manual_val = manual_by_id[sid][metric]
            auto_vals.append(auto_val)
            manual_vals.append(manual_val)

        agree = sum(1 for a, m in zip(auto_vals, manual_vals) if a == m)
        agree_pct = agree / len(common_ids) * 100

        try:
            kappa = cohen_kappa_score(auto_vals, manual_vals)
        except Exception:
            kappa = float("nan")

        results[metric] = {"kappa": round(kappa, 3), "agreement_pct": round(agree_pct, 1)}
        print(f"  {metric:<38} {kappa:>8.3f} {agree_pct:>9.1f}%")

    # Strict pass
    auto_pass = []
    manual_pass = []
    for sid in common_ids:
        a = auto_by_id[sid]["auto_scores"]
        auto_pass.append(a["strict_pass"])
        m = manual_by_id[sid]
        mp = (m["nc_detected"] == 1 and m["infeasible_option_rejected"] == 1
              and m["goal_achieved_by_recommendation"] == 1)
        manual_pass.append(mp)

    agree = sum(1 for a, m in zip(auto_pass, manual_pass) if a == m)
    agree_pct = agree / len(common_ids) * 100
    try:
        kappa = cohen_kappa_score(auto_pass, manual_pass)
    except Exception:
        kappa = float("nan")

    results["strict_pass"] = {"kappa": round(kappa, 3), "agreement_pct": round(agree_pct, 1)}
    print(f"  {'strict_pass':<38} {kappa:>8.3f} {agree_pct:>9.1f}%")

    # Save results
    output = {
        "n_samples": len(common_ids),
        "per_metric": results,
        "overall_kappa": round(
            sum(r["kappa"] for r in results.values() if not str(r["kappa"]).startswith("n"))
            / len(results), 3
        ),
    }

    with open(ROOT / "validation/agreement_results.json", "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nOverall average kappa: {output['overall_kappa']:.3f}")
    print(f"Results saved to validation/agreement_results.json")

    if output["overall_kappa"] >= 0.8:
        print("\n✅ VALIDATION PASSED (kappa >= 0.8)")
    else:
        print("\n⚠️ VALIDATION BELOW THRESHOLD (kappa < 0.8)")
        print("Review disagreements and consider refining the scorer.")


if __name__ == "__main__":
    main()
