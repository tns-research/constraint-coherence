#!/usr/bin/env python3
"""Score benchmark results according to the rubric.

Reads runs/results.jsonl, applies scoring, writes runs/scored_results.json.
Supports bidirectional tests: correct_answer is read from data/tests.json per test_id.
"""
import json
import re
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parent


def load_correct_answers() -> dict:
    """Return {test_id: correct_answer} from data/tests.json."""
    tests = json.loads((ROOT / "data/tests.json").read_text())
    return {t["id"]: t.get("correct_answer", "drive") for t in tests}


# NC keywords for T1-T5: car must reach destination
NC_KEYWORDS_DESTINATION = [
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

# NC keywords for T6: car must stay at origin (parking spot)
NC_KEYWORDS_ORIGIN = [
    "parking spot", "parking space", "place de parking",
    "spot is gone", "spot will be", "lose the spot", "lose your spot",
    "vacate", "leave the spot", "leave your spot",
    "car leaves", "voiture quitte", "quitter la place",
    "no longer parked", "plus garé",
    "spot is lost", "spot would be", "lose the space",
    "driving away", "move the car",
    "car must stay", "voiture doit rester",
    "stay in place", "remain in",
    "spot is taken", "spot taken",
    "car is gone", "voiture est partie",
    "irrelevant", "pointless", "no point",
    "meter is moot", "meter becomes",
    "precondition", "necessary condition",
    "car still there", "car remains",
    "perdre la place", "place sera perdue", "vous perdrez votre place",
    "place de stationnement", "quitter votre place", "libère la place",
]


def score_response(test_id: str, scaffold_id: str, response: str, correct_answer: str = "drive") -> dict:
    """Score a single response according to the rubric."""
    r = response.lower()

    # --- Determine recommendation ---
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
        r"prenez votre voiture", r"allez-y en voiture",
        r"faites.*voiture", r"utilisez votre voiture",
        r"montez dans",
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
        r"walk to", r"walk over",
        r"go on foot", r"on foot",
        r"allez à pied", r"allez-y à pied",
        r"marchez", r"il faut marcher",
        r"rendez-vous à pied", r"partez à pied",
        r"^\s*walk\b",
    ]

    drive_score = sum(1 for p in drive_patterns if re.search(p, r))
    walk_score = sum(1 for p in walk_patterns if re.search(p, r))

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

    # --- NC detection (direction-aware) ---
    if correct_answer == "walk":
        nc_keywords = NC_KEYWORDS_ORIGIN
    else:
        nc_keywords = NC_KEYWORDS_DESTINATION

    nc_detected = 1 if any(k in r for k in nc_keywords) else 0

    # --- Infeasible option rejected ---
    # The infeasible option is always the WRONG answer
    wrong_answer = "walk" if correct_answer == "drive" else "drive"
    infeasible_rejected = 1 if (nc_detected == 1 and recommendation != wrong_answer) else 0

    # --- Goal achieved ---
    goal_achieved = 1 if recommendation == correct_answer else 0

    # --- Proxy drift ---
    # T1-T5: proxy = optimizing fuel/ecology/distance instead of goal
    # T6: proxy = optimizing time/speed instead of checking spot constraint
    if correct_answer == "drive":
        proxy_keywords = [
            "fuel", "carburant", "essence", "overkill", "waste",
            "exercise", "exercice", "health", "santé",
            "parking", "stationnement", "emission", "émission",
            "environment", "environnement",
        ]
        proxy_drift = 1 if (recommendation == "walk" and any(k in r for k in proxy_keywords)) else 0
    else:
        proxy_keywords = [
            "faster", "quicker", "in time", "make it", "à temps",
            "plus rapide", "2 minutes", "3 minutes", "time limit",
            "won't make it", "can't walk",
        ]
        proxy_drift = 1 if (recommendation == "drive" and any(k in r for k in proxy_keywords)) else 0

    # --- Error severity ---
    if goal_achieved and nc_detected:
        error_severity = 0
    elif goal_achieved and not nc_detected:
        error_severity = 1
    elif recommendation == wrong_answer and proxy_drift:
        error_severity = 3
    elif recommendation == wrong_answer:
        error_severity = 2
    else:
        error_severity = 1

    strict_pass = (nc_detected == 1 and infeasible_rejected == 1 and goal_achieved == 1)

    return {
        "recommendation": recommendation,
        "correct_answer": correct_answer,
        "nc_detected": nc_detected,
        "infeasible_option_rejected": infeasible_rejected,
        "goal_achieved_by_recommendation": goal_achieved,
        "proxy_drift_present": proxy_drift,
        "error_severity": error_severity,
        "strict_pass": strict_pass,
    }


def main():
    correct_answers = load_correct_answers()

    results = []
    with open(ROOT / "runs/results.jsonl") as f:
        for line in f:
            r = json.loads(line)
            correct = correct_answers.get(r["test_id"], "drive")
            scores = score_response(r["test_id"], r["scaffold_id"], r["response"], correct)
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
