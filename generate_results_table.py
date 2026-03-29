#!/usr/bin/env python3
"""Generate LaTeX tables from statistical analysis results."""
import csv
import os
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent


def format_scaffold_name(scaffold_id):
    names = {
        "S0": "S0 (Control)",
        "S1": "S1 (Constraints-first)",
        "S2": "S2 (Means-end)",
        "S3": "S3 (Attribute sub.)",
        "S4": "S4 (Embodied sim.)",
        "S5": "S5 (Systems causal)",
    }
    return names.get(scaffold_id, scaffold_id)


def generate_single_model_table(rows, model_label, caption_suffix):
    lines = []
    lines.append("\\begin{table}[h]")
    lines.append("\\centering")
    lines.append("\\begin{tabular}{lccc}")
    lines.append("\\toprule")
    lines.append("Scaffold & Pass Rate & 95\\% CI & $n$ \\\\")
    lines.append("\\midrule")

    for row in rows:
        name = format_scaffold_name(row["scaffold"])
        rate = float(row["pass_rate"])
        ci_lo = float(row["ci_lower"])
        ci_hi = float(row["ci_upper"])
        n = int(row["n"])

        bold = rate >= 0.9
        rate_str = f"{rate:.0%}"
        if bold:
            rate_str = f"\\textbf{{{rate_str}}}"

        ci_str = f"[{ci_lo:.2f}, {ci_hi:.2f}]"
        lines.append(f"  {name} & {rate_str} & {ci_str} & {n} \\\\")

    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    lines.append(f"\\caption{{Pass rates by scaffold ({caption_suffix}). 95\\% Clopper-Pearson confidence intervals.}}")
    lines.append(f"\\label{{tab:results_{model_label.lower()}}}")
    lines.append("\\end{table}")
    return "\n".join(lines)


def generate_combined_table(haiku_rows, sonnet_rows):
    haiku_n = int(haiku_rows[0]["n"]) if haiku_rows else "?"
    sonnet_n = int(sonnet_rows[0]["n"]) if sonnet_rows else "?"
    lines = []
    lines.append("\\begin{table}[t]")
    lines.append("\\centering")
    lines.append("\\begin{tabular}{lcccc}")
    lines.append("\\toprule")
    lines.append(f"Scaffold & \\multicolumn{{2}}{{c}}{{Haiku 4.5 ($n$={haiku_n})}} & \\multicolumn{{2}}{{c}}{{Sonnet 4.5 ($n$={sonnet_n})}} \\\\")
    lines.append("\\cmidrule(lr){2-3} \\cmidrule(lr){4-5}")
    lines.append(" & Pass Rate & 95\\% CI & Pass Rate & 95\\% CI \\\\")
    lines.append("\\midrule")

    for h_row, s_row in zip(haiku_rows, sonnet_rows):
        name = format_scaffold_name(h_row["scaffold"])

        h_rate = float(h_row["pass_rate"])
        h_ci = f"[{float(h_row['ci_lower']):.2f}, {float(h_row['ci_upper']):.2f}]"
        h_str = f"{h_rate:.0%}"
        if h_rate >= 0.9:
            h_str = f"\\textbf{{{h_str}}}"

        s_rate = float(s_row["pass_rate"])
        s_ci = f"[{float(s_row['ci_lower']):.2f}, {float(s_row['ci_upper']):.2f}]"
        s_str = f"{s_rate:.0%}"
        if s_rate >= 0.9:
            s_str = f"\\textbf{{{s_str}}}"

        lines.append(f"  {name} & {h_str} & {h_ci} & {s_str} & {s_ci} \\\\")

    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    lines.append("\\caption{Pass rates by scaffold across two Claude models. Bold indicates $\\geq$90\\%. Confidence intervals are Clopper-Pearson exact binomial.}")
    lines.append("\\label{tab:results_combined}")
    lines.append("\\end{table}")
    return "\n".join(lines)


def generate_fisher_table():
    with open(ROOT / "analysis/fisher_test_results.json") as f:
        fisher = json.load(f)

    lines = []
    lines.append("\\begin{table}[h]")
    lines.append("\\centering")
    lines.append("\\begin{tabular}{llccc}")
    lines.append("\\toprule")
    lines.append("Comparison & Model & Odds Ratio & $p$-value & Sig. \\\\")
    lines.append("\\midrule")

    for key in sorted(fisher.keys()):
        entry = fisher[key]
        if "comparison" not in entry:
            comp = "S2 vs S0"
        else:
            comp = entry["comparison"]

        model = entry["model"].capitalize()
        odds = entry["odds_ratio"]
        if odds == "Infinity":
            or_str = "$\\infty$"
        else:
            or_str = f"{odds:.1f}"

        p = entry["p_value"]
        if p < 0.001:
            p_str = "$<$0.001"
            sig = "***"
        elif p < 0.01:
            p_str = f"{p:.4f}"
            sig = "**"
        elif p < 0.05:
            p_str = f"{p:.4f}"
            sig = "*"
        else:
            p_str = f"{p:.3f}"
            sig = "ns"

        lines.append(f"  {comp} & {model} & {or_str} & {p_str} & {sig} \\\\")

    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    lines.append("\\caption{Fisher's exact test results for all pairwise comparisons against S0 (Control). Significance: *** $p<0.001$, ** $p<0.01$, * $p<0.05$.}")
    lines.append("\\label{tab:fisher}")
    lines.append("\\end{table}")
    return "\n".join(lines)


def main():
    os.makedirs(ROOT / "paper/tables", exist_ok=True)

    # Read CSV
    with open(ROOT / "analysis/scaffold_stats.csv") as f:
        reader = list(csv.DictReader(f))

    haiku_rows = [r for r in reader if r["model"] == "haiku"]
    sonnet_rows = [r for r in reader if r["model"] == "sonnet"]

    # Derive run counts from the combined data file
    with open(ROOT / "runs/scored_combined_all_models.json") as f:
        all_data = json.load(f)
    haiku_run_count = len(set(r["run"] for r in all_data if r["model"] == "haiku-4.5"))
    sonnet_run_count = len(set(r["run"] for r in all_data if r["model"] == "sonnet-4.5"))

    # Individual model tables
    haiku_table = generate_single_model_table(haiku_rows, "Haiku", f"Claude Haiku 4.5, {haiku_run_count} runs")
    with open(ROOT / "paper/tables/haiku_results.tex", "w") as f:
        f.write(haiku_table)
    print(f"Written: paper/tables/haiku_results.tex")

    sonnet_table = generate_single_model_table(sonnet_rows, "Sonnet", f"Claude Sonnet 4.5, {sonnet_run_count} runs")
    with open(ROOT / "paper/tables/sonnet_results.tex", "w") as f:
        f.write(sonnet_table)
    print(f"Written: paper/tables/sonnet_results.tex")

    # Combined table
    combined_table = generate_combined_table(haiku_rows, sonnet_rows)
    with open(ROOT / "paper/tables/combined_results.tex", "w") as f:
        f.write(combined_table)
    print(f"Written: paper/tables/combined_results.tex")

    # Fisher table
    fisher_table = generate_fisher_table()
    with open(ROOT / "paper/tables/fisher_results.tex", "w") as f:
        f.write(fisher_table)
    print(f"Written: paper/tables/fisher_results.tex")

    print("\nAll LaTeX tables generated.")


if __name__ == "__main__":
    main()
