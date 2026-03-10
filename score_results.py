#!/usr/bin/env python3
"""Score benchmark results according to the rubric.

Reads runs/results.jsonl, applies scoring, writes runs/scored_results.json.
"""
import json
import re
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parent


def score_response(test_id: str, scaffold_id: str, response: str) -> dict:
    """Score a single response according to the rubric."""
    r = response.lower()
    
    # --- Determine recommendation ---
    # Check conclusion/verdict area (last 400 chars) more heavily
    tail = r[-400:]
    
    drive_patterns = [
        r"you should \*?\*?drive",
        r"drive there", r"driving is the only",
        r"answer:?\s*drive", r"verdict:?\s*.*driv",
        r"\*\*drive\*\*", r"\*\*driving\*\*",
        r"conduis", r"conduire", r"en voiture",
        r"tu dois.*condui",
        r"infeasible.*walk", r"walking.*infeasible",
        r"infaisable.*march", r"march.*infaisable",
        r"walking.*breaks", r"walking.*severs",
        r"drive\.\s*$", r"drive\.\*\*",
        r"driving,\s*obviously",
        r"recommendation:?\s*\*?\*?\s*drive",
        r"decision:?\s*\*?\*?\s*drive",
        r"you must drive",
        r"need to drive", r"should drive",
    ]
    
    walk_patterns = [
        r"you should \*?\*?walk",
        r"walking is the better", r"walking is clearly",
        r"answer:?\s*walk", r"verdict:?\s*.*walk",
        r"\*\*walk\.?\*\*", r"\*\*walking\*\*",
        r"va à pied", r"marche à pied", r"à pied",
        r"walk\.\s*$",
        r"decision:?\s*\*?\*?\s*walk",
        r"recommendation:?\s*\*?\*?\s*walk",
        r"tu devrais.*march", r"tu dois.*march",
    ]
    
    drive_score = sum(1 for p in drive_patterns if re.search(p, r))
    walk_score = sum(1 for p in walk_patterns if re.search(p, r))
    
    # Tail gets extra weight for final verdict
    drive_tail = sum(1 for p in drive_patterns if re.search(p, tail))
    walk_tail = sum(1 for p in walk_patterns if re.search(p, tail))
    drive_score += drive_tail * 2
    walk_score += walk_tail * 2
    
    if drive_score > walk_score:
        recommendation = "drive"
    elif walk_score > drive_score:
        recommendation = "walk"
    else:
        recommendation = "ambiguous"
    
    # --- NC detection ---
    nc_keywords = [
        "car must be", "car needs to be", "voiture doit être",
        "vehicle must be", "car at the", "voiture au",
        "car is not at", "voiture n'est pas",
        "required object", "objet requis",
        "car left behind", "car (left behind",
        "car stays", "voiture reste",
        "car won't be there", "missing",
        "physically present", "physiquement présent",
        "bring the car", "amener la voiture",
        "car ready to", "prior state",
        "dependency chain", "chaîne de dépendance",
        "car to be at", "car present",
        "co-location", "colocation",
        "car never reaches", "car won't be",
        "car isn't there", "car must physically",
        "vehicle at the", "car there",
        "deliver the vehicle", "return the car",
        "rendre la voiture",
        "causal chain", "breaks.*chain",
        "drive it there", "need to drive it",
        "you'd need to drive",
    ]
    nc_detected = 1 if any(k in r for k in nc_keywords) else 0
    
    # Infeasible option rejected
    infeasible_rejected = 1 if (nc_detected == 1 and recommendation == "drive") else 0
    
    # Goal achieved
    goal_achieved = 1 if recommendation == "drive" else 0
    
    # Proxy drift
    proxy_keywords = [
        "fuel", "carburant", "essence", "overkill", "waste",
        "exercise", "exercice", "health", "santé",
        "parking", "stationnement", "emission", "émission",
        "environment", "environnement",
    ]
    proxy_drift = 1 if (recommendation == "walk" and any(k in r for k in proxy_keywords)) else 0
    
    # Error severity
    if goal_achieved and nc_detected:
        error_severity = 0
    elif goal_achieved and not nc_detected:
        error_severity = 1
    elif recommendation == "walk" and proxy_drift:
        error_severity = 3
    elif recommendation == "walk":
        error_severity = 2
    else:
        error_severity = 1
    
    strict_pass = (nc_detected == 1 and infeasible_rejected == 1 and goal_achieved == 1)
    
    return {
        "recommendation": recommendation,
        "nc_detected": nc_detected,
        "infeasible_option_rejected": infeasible_rejected,
        "goal_achieved_by_recommendation": goal_achieved,
        "proxy_drift_present": proxy_drift,
        "error_severity": error_severity,
        "strict_pass": strict_pass,
    }


def main():
    results = []
    with open(ROOT / "runs/results.jsonl") as f:
        for line in f:
            r = json.loads(line)
            scores = score_response(r["test_id"], r["scaffold_id"], r["response"])
            results.append({
                "test_id": r["test_id"],
                "scaffold_id": r["scaffold_id"],
                "latency_ms": r["latency_ms"],
                "response_preview": r["response"][:300],
                **scores,
            })

    out = ROOT / "runs/scored_results.json"
    with open(out, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"{'Test':>4} {'Scaffold':>8} {'Rec':>8} {'NC':>3} {'Rej':>3} {'Goal':>4} {'Proxy':>5} {'Err':>3} {'Pass':>4}")
    print("-" * 55)
    for r in results:
        p = "PASS" if r["strict_pass"] else "FAIL"
        print(f"{r['test_id']:>4} {r['scaffold_id']:>8} {r['recommendation']:>8} {r['nc_detected']:>3} "
              f"{r['infeasible_option_rejected']:>3} {r['goal_achieved_by_recommendation']:>4} "
              f"{r['proxy_drift_present']:>5} {r['error_severity']:>3} {p:>4}")

    total = len(results)
    passes = sum(1 for r in results if r["strict_pass"])
    print(f"\nTotal: {total}  Passes: {passes}  Rate: {passes/total*100:.1f}%")

    print("\nBy scaffold:")
    by_scaffold = defaultdict(list)
    for r in results:
        by_scaffold[r["scaffold_id"]].append(r)
    for sid in sorted(by_scaffold):
        items = by_scaffold[sid]
        sp = sum(1 for i in items if i["strict_pass"])
        print(f"  {sid}: {sp}/{len(items)} pass ({sp/len(items)*100:.0f}%)")

    print("\nBy test:")
    by_test = defaultdict(list)
    for r in results:
        by_test[r["test_id"]].append(r)
    for tid in sorted(by_test):
        items = by_test[tid]
        sp = sum(1 for i in items if i["strict_pass"])
        print(f"  {tid}: {sp}/{len(items)} pass ({sp/len(items)*100:.0f}%)")


if __name__ == "__main__":
    main()
