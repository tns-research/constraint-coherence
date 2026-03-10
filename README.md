# Constraint Coherence Benchmark

A benchmark for evaluating LLM reasoning failures on implicit physical constraints, with six cognitive scaffolds designed to recover correct reasoning.

## Paper

**Title:** Reasoning Architecture for Implicit Constraint Inference: A Multi-Scaffold Study  
**Authors:** Theo Nicolas Sitjar

## Overview

Large language models frequently fail on problems requiring implicit physical constraint inference — situations where the correct answer depends on an unstated physical necessity (e.g., a car must be physically present at a car wash to be washed). This benchmark measures how different reasoning scaffolds affect LLM performance on such tasks.

**Key finding:** Means-end analysis (backward goal chaining) achieves 96% accuracy on Haiku and 93% on Sonnet, compared to 24% and 7% for unscaffolded control — a statistically significant improvement (Fisher's exact test, p < 0.001 for both models).

## Dataset

| Component | Details |
|-----------|---------|
| **Tests** | 5 variants of vehicle-at-destination constraint |
| **Scaffolds** | 6 reasoning frameworks (S0–S5) |
| **Models** | Claude Haiku 4.5, Claude Sonnet 4.5 |
| **Runs** | 5 (Haiku), 3 (Sonnet) |
| **Total** | 240 scored responses |
| **Validation** | Manual annotation (n=30), Cohen's κ = 0.786 |

### Test Suite

| ID | Scenario | Distance |
|----|----------|----------|
| T1 | Car wash | 100m |
| T2 | Drive-through emissions test | 180m |
| T3 | Tire air pump refill | 120m |
| T4 | Electric car charging bay | 140m |
| T5 | Rental car return lane | 250m |

### Reasoning Scaffolds

| ID | Name | Strategy |
|----|------|----------|
| S0 | Control | No scaffold (bare prompt) |
| S1 | Constraints-first | List hard constraints before optimizing |
| S2 | Means-end analysis | Backward chaining from goal state |
| S3 | Attribute substitution check | Test for proxy metric substitution |
| S4 | Embodied simulation | Mental simulation of physical actions |
| S5 | Systems causal map | Causal system with entity interactions |

## Results

### Pass Rates by Scaffold

![Pass rates by scaffold with 95% confidence intervals](paper/figures/scaffold_pass_rate.png)

| Scaffold | Haiku 4.5 (n=25) | 95% CI | Sonnet 4.5 (n=15) | 95% CI |
|----------|-------------------|--------|---------------------|--------|
| S0 (Control) | 24% | [0.09, 0.45] | 7% | [0.00, 0.32] |
| S1 (Constraints-first) | 44% | [0.24, 0.65] | 53% | [0.27, 0.79] |
| **S2 (Means-end)** | **96%** | [0.80, 1.00] | **93%** | [0.68, 1.00] |
| S3 (Attribute sub.) | 32% | [0.15, 0.54] | 80% | [0.52, 0.96] |
| S4 (Embodied sim.) | 80% | [0.59, 0.93] | 67% | [0.38, 0.88] |
| S5 (Systems causal) | 88% | [0.69, 0.97] | 73% | [0.45, 0.92] |

### Statistical Significance (Fisher's Exact Test, S2 vs S0)

| Model | Odds Ratio | p-value | Significant |
|-------|-----------|---------|-------------|
| Haiku 4.5 | 76.0 | < 0.001 | *** |
| Sonnet 4.5 | 196.0 | < 0.001 | *** |

95% confidence intervals: Clopper-Pearson exact binomial method.

### Cross-Model Heatmap

![Test × Scaffold pass rate heatmap](paper/figures/heatmap.png)

### Run-to-Run Consistency

![Pass rates across independent runs](paper/figures/run_consistency.png)

## Repository Structure

```
├── data/
│   ├── tests.json              # 5 test prompts
│   └── scaffolds.json          # 5 reasoning scaffolds (S1–S5)
├── runs/
│   └── scored_combined_all_models.json  # 240 scored results
├── analysis/
│   ├── scaffold_stats.csv      # Pass rates + CIs per scaffold per model
│   └── fisher_test_results.json # Fisher's exact test results
├── validation/
│   ├── ANNOTATION_GUIDE.md     # Manual annotation rubric
│   ├── validation_sample.jsonl # 30-item stratified sample
│   ├── manual_annotations.jsonl # Human annotations
│   ├── agreement_results.json  # Inter-rater agreement (κ = 0.786)
│   └── calculate_agreement.py  # Agreement calculation script
├── paper/
│   ├── tables/                 # LaTeX tables
│   └── figures/                # Charts (PNG)
├── run_benchmark.py             # Benchmark runner (OpenRouter / custom provider)
├── score_results.py            # Automated scoring script
├── stats_analysis.py           # Statistical analysis (CIs + Fisher)
├── generate_charts.py          # Figure generation
├── generate_results_table.py   # LaTeX table generation
├── requirements.txt
└── LICENSE
```

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Reproduce statistical analysis
python3 stats_analysis.py

# Regenerate LaTeX tables
python3 generate_results_table.py

# Regenerate figures
python3 generate_charts.py
```

### Running the benchmark

```bash
# Using OpenRouter (default provider)
OPENROUTER_API_KEY=sk-... python3 run_benchmark.py --model meta-llama/llama-3.3-70b-instruct:free

# Using a custom provider (e.g. Zo API)
python3 run_benchmark.py --provider zo --model haiku
```

The benchmark runner supports OpenRouter out of the box. For custom providers, create an adapter module (see `run_benchmark.py` for the interface).

## Scoring Rubric

Each response is scored on five binary metrics:

1. **nc_detected** — Did the model identify the implicit necessary condition (vehicle must be at destination)?
2. **infeasible_option_rejected** — Did it explicitly reject the infeasible option (walking)?
3. **goal_achieved_by_recommendation** — Does the final recommendation achieve the goal (drive)?
4. **proxy_drift_present** — Did the model optimize a proxy metric instead of the actual goal?
5. **error_severity** (0–3) — 0 = correct, 1 = ambiguous, 2 = clear miss, 3 = confidently wrong

**Strict pass** requires: `nc_detected=1 AND infeasible_option_rejected=1 AND goal_achieved=1`

## Paper Preview

**Reasoning Architecture for Implicit Constraint Inference: A Multi-Scaffold Study**

Large language models consistently fail on tasks requiring implicit physical constraint inference — recognizing that a car must be physically present at a car wash to be washed, even when the car wash is only 100 meters away. We introduce the Constraint Coherence Benchmark: 5 structurally isomorphic test scenarios evaluated under 6 reasoning scaffolds drawn from cognitive science.

Our central finding is that **means-end analysis** (backward chaining from the goal state to its physical preconditions) nearly eliminates the failure, achieving 96% on Claude Haiku 4.5 and 93% on Claude Sonnet 4.5 — compared to 24% and 7% under unscaffolded control. This converges with independent findings by Jo (2026), who showed that STAR's Task step — which implements the same backward-chaining mechanism through a different formalism — achieves 85% on Sonnet.

We also document that **not all scaffolds help**: attribute-substitution checking (S3) fails to improve Haiku performance (32% vs 24% control, p = 0.754), suggesting that metacognitive prompts can reinforce rather than correct proxy-metric reasoning in smaller models.

Full paper available upon request.

## Citation

```bibtex
@misc{constraintcoherence2026,
  title={Reasoning Architecture for Implicit Constraint Inference: A Multi-Scaffold Study},
  author={Sitjar, Theo Nicolas},
  year={2026},
  note={Preprint}
}
```

## License

MIT License. See [LICENSE](LICENSE) for details.
