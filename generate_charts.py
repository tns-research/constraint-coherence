#!/usr/bin/env python3
"""Generate publication-quality figures for the Constraint Coherence Benchmark paper.

Output: 6 PDF figures at 300 DPI with colorblind-friendly palette.
"""
import json
from pathlib import Path
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
import seaborn as sns
from scipy.stats import beta as beta_dist

# ── Paths ──
ROOT = Path(__file__).resolve().parent
OUT = ROOT / "paper" / "figures"
OUT.mkdir(parents=True, exist_ok=True)

# ── Publication-quality global settings ──
plt.rcParams.update({
    "figure.dpi": 300,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.05,
    "font.size": 10,
    "font.family": "serif",
    "font.serif": ["DejaVu Serif", "Times New Roman", "Times"],
    "axes.labelsize": 12,
    "axes.titlesize": 13,
    "axes.titleweight": "bold",
    "xtick.labelsize": 9,
    "ytick.labelsize": 10,
    "legend.fontsize": 9,
    "legend.framealpha": 0.9,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.figsize": (7, 4),
    "axes.grid": False,
})

# Colorblind-friendly palette (IBM Design / Wong 2011)
CB_BLUE = "#0072B2"
CB_ORANGE = "#E69F00"
CB_GREEN = "#009E73"
CB_RED = "#D55E00"
CB_PURPLE = "#CC79A7"
CB_CYAN = "#56B4E9"
CB_YELLOW = "#F0E442"
CB_BLACK = "#000000"

SCAFFOLD_PALETTE = [CB_BLUE, CB_CYAN, CB_GREEN, CB_RED, CB_ORANGE, CB_PURPLE]
MODEL_PALETTE = {"haiku-4.5": CB_BLUE, "sonnet-4.6": CB_ORANGE}

# ── Labels ──
SCAFFOLD_LABELS = {
    "S0": "S0: Control",
    "S1": "S1: Constraints-\nfirst",
    "S2": "S2: Means-end\nanalysis",
    "S3": "S3: Attribute\nsubstitution",
    "S4": "S4: Embodied\nsimulation",
    "S5": "S5: Systems-\ncausal",
}

SCAFFOLD_SHORT = {
    "S0": "S0\nControl",
    "S1": "S1\nConstr.",
    "S2": "S2\nMeans-end",
    "S3": "S3\nAttr.sub.",
    "S4": "S4\nEmbodied",
    "S5": "S5\nSystems",
}

TEST_LABELS = {
    "T1": "T1: Car wash",
    "T2": "T2: Emissions",
    "T3": "T3: Tire refill",
    "T4": "T4: EV charge",
    "T5": "T5: Rental return",
    "T6": "T6: Parking meter",
}

SCAFFOLDS = ["S0", "S1", "S2", "S3", "S4", "S5"]
TESTS = ["T1", "T2", "T3", "T4", "T5", "T6"]

# ── PNG export directory (for github-export and README) ──
PNG_OUT = ROOT / "github-export" / "paper" / "figures"
PNG_OUT.mkdir(parents=True, exist_ok=True)


def save_fig(fig, name):
    """Save figure as PDF (paper/) and PNG (paper/ + github-export/)."""
    fig.savefig(OUT / f"{name}.pdf")
    fig.savefig(OUT / f"{name}.png")
    fig.savefig(PNG_OUT / f"{name}.png")


# ── Helper functions ──
def clopper_pearson(k, n, alpha=0.05):
    """Clopper-Pearson exact binomial confidence interval."""
    if n == 0:
        return 0.0, 1.0
    lo = beta_dist.ppf(alpha / 2, k, n - k + 1) if k > 0 else 0.0
    hi = beta_dist.ppf(1 - alpha / 2, k + 1, n - k) if k < n else 1.0
    return lo, hi


def add_significance_stars(ax, x, y, text, fontsize=8):
    """Add significance annotation above a bar."""
    ax.annotate(text, (x, y), ha="center", va="bottom", fontsize=fontsize,
                fontweight="bold", color=CB_BLACK)


# ── Load data ──
with open(ROOT / "runs" / "scored_combined_all_models.json") as f:
    all_results = json.load(f)

haiku_results = [r for r in all_results if r["model"] == "haiku-4.5"]
sonnet_results = [r for r in all_results if r["model"] == "sonnet-4.6"]

stats_df = pd.read_csv(ROOT / "analysis" / "scaffold_stats.csv")

with open(ROOT / "analysis" / "fisher_test_results.json") as f:
    fisher = json.load(f)


# ════════════════════════════════════════════════════════════════
# FIGURE 1: Scaffold Pass Rates with CIs (grouped bar, both models)
# ════════════════════════════════════════════════════════════════
def fig1_scaffold_pass_rate():
    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    x = np.arange(len(SCAFFOLDS))
    width = 0.35

    haiku_df = stats_df[stats_df["model"] == "haiku"]
    sonnet_df = stats_df[stats_df["model"] == "sonnet"]

    haiku_rates = [haiku_df[haiku_df["scaffold"] == s]["correct_rate"].values[0] * 100 for s in SCAFFOLDS]
    sonnet_rates = [sonnet_df[sonnet_df["scaffold"] == s]["correct_rate"].values[0] * 100 for s in SCAFFOLDS]

    haiku_ci_lo = [haiku_df[haiku_df["scaffold"] == s]["ci_lower"].values[0] * 100 for s in SCAFFOLDS]
    haiku_ci_hi = [haiku_df[haiku_df["scaffold"] == s]["ci_upper"].values[0] * 100 for s in SCAFFOLDS]
    sonnet_ci_lo = [sonnet_df[sonnet_df["scaffold"] == s]["ci_lower"].values[0] * 100 for s in SCAFFOLDS]
    sonnet_ci_hi = [sonnet_df[sonnet_df["scaffold"] == s]["ci_upper"].values[0] * 100 for s in SCAFFOLDS]

    haiku_err = [[r - lo for r, lo in zip(haiku_rates, haiku_ci_lo)],
                 [hi - r for r, hi in zip(haiku_rates, haiku_ci_hi)]]
    sonnet_err = [[r - lo for r, lo in zip(sonnet_rates, sonnet_ci_lo)],
                  [hi - r for r, hi in zip(sonnet_rates, sonnet_ci_hi)]]

    bars_h = ax.bar(x - width / 2, haiku_rates, width, yerr=haiku_err,
                    color=CB_BLUE, edgecolor="white", linewidth=0.5,
                    capsize=3, error_kw={"linewidth": 1},
                    label=f"Haiku 4.5 (n={int(haiku_df['n'].iloc[0])})", zorder=3)
    bars_s = ax.bar(x + width / 2, sonnet_rates, width, yerr=sonnet_err,
                    color=CB_ORANGE, edgecolor="white", linewidth=0.5,
                    capsize=3, error_kw={"linewidth": 1},
                    label=f"Sonnet 4.6 (n={int(sonnet_df['n'].iloc[0])})", zorder=3)

    # Rate labels on bars
    for bar, rate in zip(bars_h, haiku_rates):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + haiku_err[1][bars_h.patches.index(bar)] + 2,
                f"{rate:.0f}%", ha="center", va="bottom", fontsize=7.5, fontweight="bold", color=CB_BLUE)
    for bar, rate in zip(bars_s, sonnet_rates):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + sonnet_err[1][list(bars_s.patches).index(bar)] + 2,
                f"{rate:.0f}%", ha="center", va="bottom", fontsize=7.5, fontweight="bold", color=CB_ORANGE)

    ax.set_xticks(x)
    ax.set_xticklabels([SCAFFOLD_SHORT[s] for s in SCAFFOLDS])
    ax.set_ylabel("Pass Rate (%)")
    ax.set_ylim(0, 118)
    ax.set_title("Scaffold Pass Rates with 95% Confidence Intervals")
    ax.legend(loc="upper left", frameon=True)
    ax.axhline(y=50, color="gray", linestyle=":", alpha=0.3, linewidth=0.8)

    save_fig(fig, "scaffold_pass_rate")
    plt.close(fig)
    print("  [1/6] scaffold_pass_rate.pdf + .png")


# ════════════════════════════════════════════════════════════════
# FIGURE 2: Test × Scaffold Heatmap (both models side-by-side)
# ════════════════════════════════════════════════════════════════
def fig2_heatmap():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 5), sharey=True)

    for ax, model_data, model_name, title in [
        (ax1, haiku_results, "haiku-4.5", "Haiku 4.5"),
        (ax2, sonnet_results, "sonnet-4.6", "Sonnet 4.6"),
    ]:
        matrix = np.zeros((len(TESTS), len(SCAFFOLDS)))
        counts = np.zeros((len(TESTS), len(SCAFFOLDS)))
        for r in model_data:
            if r["test_id"] not in TESTS:
                continue
            ti = TESTS.index(r["test_id"])
            si = SCAFFOLDS.index(r["scaffold_id"])
            counts[ti][si] += 1
            if r["strict_pass"]:
                matrix[ti][si] += 1
        matrix = np.divide(matrix, counts, where=counts > 0, out=matrix)

        # Colorblind-friendly diverging colormap
        cmap = sns.color_palette("YlGnBu", as_cmap=True)
        im = ax.imshow(matrix, cmap=cmap, aspect="auto", vmin=0, vmax=1)

        ax.set_xticks(range(len(SCAFFOLDS)))
        ax.set_xticklabels([s for s in SCAFFOLDS], fontsize=9)
        ax.set_yticks(range(len(TESTS)))
        if ax == ax1:
            ax.set_yticklabels([TEST_LABELS[t] for t in TESTS], fontsize=9)
        ax.set_title(title, fontsize=11, fontweight="bold")

        for i in range(len(TESTS)):
            for j in range(len(SCAFFOLDS)):
                val = matrix[i][j]
                color = "white" if val < 0.5 else "black"
                ax.text(j, i, f"{val:.0%}", ha="center", va="center",
                        fontsize=9, fontweight="bold", color=color)

    fig.suptitle("Pass Rate by Test Variant and Scaffold", fontsize=13, fontweight="bold", y=1.02)
    cbar = fig.colorbar(im, ax=[ax1, ax2], shrink=0.8, pad=0.02)
    cbar.set_label("Pass Rate", fontsize=10)

    save_fig(fig, "heatmap")
    plt.close(fig)
    print("  [2/6] heatmap.pdf + .png")


# ════════════════════════════════════════════════════════════════
# FIGURE 3: Run-over-Run Consistency (line plot per scaffold)
# ════════════════════════════════════════════════════════════════
def fig3_run_consistency():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 4.5), sharey=True,
                                    gridspec_kw={"width_ratios": [5, 1]})

    # Derive run lists from data
    haiku_runs = sorted(set(r["run"] for r in haiku_results), key=lambda x: int(x) if isinstance(x, int) or (isinstance(x, str) and x.isdigit()) else x)
    sonnet_runs = sorted(set(r["run"] for r in sonnet_results), key=lambda x: x)

    for ax, model_data, model_name, runs_list, title in [
        (ax1, haiku_results, "haiku-4.5", haiku_runs, f"Haiku 4.5 ({len(haiku_runs)} runs)"),
        (ax2, sonnet_results, "sonnet-4.6", sonnet_runs, f"Sonnet 4.6 ({len(sonnet_runs)} runs)"),
    ]:
        for si, scaffold in enumerate(SCAFFOLDS):
            rates = []
            for run_id in runs_list:
                run_items = [r for r in model_data if r["scaffold_id"] == scaffold and r["run"] == run_id]
                if run_items:
                    rate = sum(1 for r in run_items if r["strict_pass"]) / len(run_items) * 100
                    rates.append(rate)
                else:
                    rates.append(np.nan)
            ms = 4 if len(runs_list) > 10 else 5
            ax.plot(range(len(rates)), rates, "o-", color=SCAFFOLD_PALETTE[si],
                    label=scaffold, linewidth=1.2, markersize=ms, zorder=3)

        ax.set_xticks(range(len(runs_list)))
        run_labels = [str(i+1) for i in range(len(runs_list))]
        ax.set_xticklabels(run_labels, fontsize=7 if len(runs_list) > 10 else 9)
        ax.set_xlabel("Run")
        ax.set_ylabel("Pass Rate (%)" if ax == ax1 else "")
        ax.set_ylim(-5, 115)
        ax.set_title(title, fontsize=11, fontweight="bold")
        ax.axhline(y=50, color="gray", linestyle=":", alpha=0.3, linewidth=0.8)

    # Single legend
    handles, labels = ax1.get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=6, frameon=True,
               bbox_to_anchor=(0.5, -0.05), fontsize=8)
    fig.suptitle("Run-over-Run Consistency", fontsize=13, fontweight="bold", y=1.02)

    save_fig(fig, "run_consistency")
    plt.close(fig)
    print("  [3/6] run_consistency.pdf + .png")


# ════════════════════════════════════════════════════════════════
# FIGURE 4: NC Detection vs Proxy Drift (scatter plot)
# ════════════════════════════════════════════════════════════════
def fig4_nc_vs_proxy():
    fig, ax = plt.subplots(figsize=(6, 5))

    for mi, (model_data, model_name, marker) in enumerate([
        (haiku_results, "Haiku 4.5", "o"),
        (sonnet_results, "Sonnet 4.6", "s"),
    ]):
        by_scaffold = defaultdict(list)
        for r in model_data:
            by_scaffold[r["scaffold_id"]].append(r)

        for si, scaffold in enumerate(SCAFFOLDS):
            items = by_scaffold[scaffold]
            nc_rate = sum(1 for r in items if r["nc_detected"]) / len(items) * 100
            proxy_rate = sum(1 for r in items if r["proxy_drift_present"]) / len(items) * 100

            ax.scatter(nc_rate, proxy_rate, c=SCAFFOLD_PALETTE[si], marker=marker,
                       s=120, edgecolors="black", linewidth=0.5, zorder=3,
                       label=f"{scaffold} ({model_name})" if mi == 0 else None)

            # Label points
            offset_x = 3
            offset_y = 3 if proxy_rate < 90 else -8
            if mi == 0:
                ax.annotate(scaffold, (nc_rate, proxy_rate),
                            textcoords="offset points", xytext=(offset_x, offset_y),
                            fontsize=7, color=SCAFFOLD_PALETTE[si], fontweight="bold")

    # Add trend arrow
    ax.annotate("", xy=(95, 5), xytext=(10, 90),
                arrowprops=dict(arrowstyle="->", color="gray", lw=1.5, ls="--"))
    ax.text(55, 55, "Better →", fontsize=8, color="gray", rotation=-42,
            ha="center", va="center", style="italic")

    ax.set_xlabel("NC Detection Rate (%)")
    ax.set_ylabel("Proxy Drift Rate (%)")
    ax.set_title("Necessary Condition Detection vs. Proxy Drift")
    ax.set_xlim(-5, 110)
    ax.set_ylim(-5, 110)

    # Custom legend for markers
    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], marker="o", color="w", markerfacecolor="gray",
               markersize=8, label="Haiku 4.5"),
        Line2D([0], [0], marker="s", color="w", markerfacecolor="gray",
               markersize=8, label="Sonnet 4.6"),
    ]
    for si, s in enumerate(SCAFFOLDS):
        legend_elements.append(
            Line2D([0], [0], marker="o", color="w", markerfacecolor=SCAFFOLD_PALETTE[si],
                   markersize=8, label=SCAFFOLD_LABELS[s].replace("\n", " "))
        )
    ax.legend(handles=legend_elements, loc="upper right", fontsize=7, frameon=True)

    save_fig(fig, "nc_vs_proxy")
    plt.close(fig)
    print("  [4/6] nc_vs_proxy.pdf + .png")


# ════════════════════════════════════════════════════════════════
# FIGURE 5: Error Severity Distribution (stacked bar, both models)
# ════════════════════════════════════════════════════════════════
def fig5_error_severity():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4), sharey=True)

    sev_colors = [CB_GREEN, CB_YELLOW, CB_ORANGE, CB_RED]
    sev_labels = ["0: Correct", "1: Ambiguous", "2: Clear miss", "3: Confidently wrong"]

    for ax, model_data, title in [
        (ax1, haiku_results, "Haiku 4.5"),
        (ax2, sonnet_results, "Sonnet 4.6"),
    ]:
        by_scaffold = defaultdict(list)
        for r in model_data:
            by_scaffold[r["scaffold_id"]].append(r)

        bottom = np.zeros(len(SCAFFOLDS))
        for sev in range(4):
            counts = []
            for s in SCAFFOLDS:
                c = sum(1 for x in by_scaffold[s] if x["error_severity"] == sev)
                counts.append(c)
            ax.bar([SCAFFOLD_SHORT[s] for s in SCAFFOLDS], counts, bottom=bottom,
                   color=sev_colors[sev], label=sev_labels[sev] if ax == ax1 else None,
                   edgecolor="white", linewidth=0.5, zorder=3)
            bottom += np.array(counts)

        n_per = len(by_scaffold["S0"])
        ax.set_ylabel(f"Count (n={n_per})" if ax == ax1 else "")
        ax.set_title(title, fontsize=11, fontweight="bold")

    fig.suptitle("Error Severity Distribution by Scaffold", fontsize=13, fontweight="bold", y=1.02)
    fig.legend(*ax1.get_legend_handles_labels(), loc="lower center", ncol=4,
               frameon=True, bbox_to_anchor=(0.5, -0.05), fontsize=8)

    save_fig(fig, "error_severity")
    plt.close(fig)
    print("  [5/6] error_severity.pdf + .png")


# ════════════════════════════════════════════════════════════════
# FIGURE 6: Response Latency by Scaffold (box + strip)
# ════════════════════════════════════════════════════════════════
def fig6_latency():
    fig, ax = plt.subplots(figsize=(7.5, 4.5))

    # Build a dataframe for seaborn
    rows = []
    for r in all_results:
        rows.append({
            "Scaffold": r["scaffold_id"],
            "Model": "Haiku" if r["model"] == "haiku-4.5" else "Sonnet",
            "Latency (s)": r["latency_ms"] / 1000,
        })
    df = pd.DataFrame(rows)

    sns.boxplot(data=df, x="Scaffold", y="Latency (s)", hue="Model",
                order=SCAFFOLDS, palette={"Haiku": CB_BLUE, "Sonnet": CB_ORANGE},
                width=0.6, linewidth=0.8, fliersize=3, ax=ax, zorder=3)

    ax.set_title("Response Latency by Scaffold and Model")
    ax.set_xlabel("")
    ax.set_xticks(range(len(SCAFFOLDS)))
    ax.set_xticklabels([SCAFFOLD_SHORT[s] for s in SCAFFOLDS])
    ax.legend(title="Model", frameon=True, fontsize=8, title_fontsize=9)

    save_fig(fig, "latency")
    plt.close(fig)
    print("  [6/6] latency.pdf + .png")


# ── Main ──
if __name__ == "__main__":
    print(f"Generating publication-quality figures (300 DPI, PDF)...")
    print(f"Data: {len(all_results)} results ({len(haiku_results)} Haiku, {len(sonnet_results)} Sonnet)")
    print(f"Output: {OUT}/\n")

    fig1_scaffold_pass_rate()
    fig2_heatmap()
    fig3_run_consistency()
    fig4_nc_vs_proxy()
    fig5_error_severity()
    fig6_latency()

    print(f"\nAll figures saved to {OUT}/")
    for f in sorted(OUT.glob("*.pdf")):
        print(f"  {f.name} ({f.stat().st_size / 1024:.1f} KB)")
