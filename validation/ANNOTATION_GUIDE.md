# Manual Annotation Guide

## Overview

This guide is for manually validating the automated scoring of 30 LLM responses from the Constraint Coherence Benchmark. Your annotations will be compared to the automated scores to calculate inter-rater agreement (Cohen's kappa).

**Time estimate:** 20-30 minutes

## Context

Each response comes from a model (Haiku 4.5 or Sonnet 4.5) answering a variant of the "car wash problem":
- The user needs to get their car washed/inspected/charged at a location ~100-250m away
- The correct answer is **drive** (because the car must physically be at the destination)
- Walking is **wrong** because it leaves the car behind — the service requires the vehicle

## Files

- **Input:** `validation/validation_sample.jsonl` — 30 responses to annotate
- **Readable version:** `validation/validation_sample_readable.md` — same data formatted for easier reading
- **Output:** `validation/manual_annotations.jsonl` — your annotations (create this file)

## Metrics to Score

For each response, score these 5 metrics:

### 1. `nc_detected` (0 or 1)
**Did the model notice that the car must be at the destination?**

- **1** = The response explicitly mentions that the car needs to be present at the destination (e.g., "the car must be at the car wash", "you need to bring the car", "walking leaves the car behind")
- **0** = The response does NOT mention this constraint

Examples:
- "You need to drive because the car has to be at the car wash" → **1**
- "Walk, it's only 100 meters" → **0**
- "The vehicle needs to be physically present for the service" → **1**

### 2. `infeasible_option_rejected` (0 or 1)
**Did the model explicitly reject walking as infeasible?**

- **1** = The response explains why walking won't work (because it fails to deliver the car)
- **0** = Walking is not rejected, or is recommended

Note: This should only be 1 if `nc_detected` is also 1 AND the recommendation is "drive."

### 3. `goal_achieved_by_recommendation` (0 or 1)
**Does the final recommendation achieve the goal (getting the car serviced)?**

- **1** = Recommends driving (car arrives at destination)
- **0** = Recommends walking (car stays home) or is ambiguous

If the response recommends both but leans toward walk → **0**
If the response recommends both but leans toward drive → **1**
If genuinely ambiguous → **0**

### 4. `proxy_drift_present` (0 or 1)
**Did the model optimize a proxy metric (distance, fuel, exercise) instead of the actual goal?**

- **1** = The response focuses on distance being short, fuel savings, health benefits, environmental impact — WITHOUT considering whether the goal is actually achievable
- **0** = No proxy optimization, or the model correctly identifies the real goal

Note: Proxy drift should only be scored 1 if the recommendation is "walk." If the model mentions fuel/distance but still recommends driving, that's NOT proxy drift.

### 5. `error_severity` (0, 1, 2, or 3)
**How severe is the error?**

- **0** = Correct answer with correct reasoning (recommends drive, explains why car must be there)
- **1** = Correct answer but unclear/incomplete reasoning, OR ambiguous recommendation
- **2** = Wrong answer (walk) but shows some awareness of the constraint
- **3** = Confidently wrong — recommends walking with proxy reasoning (distance, fuel, eco) and no awareness of the constraint

## Output Format

Create `validation/manual_annotations.jsonl` with one JSON object per line:

```json
{"sample_id": 1, "test_id": "T1", "scaffold_id": "S0", "model": "haiku-4.5", "run": 1, "nc_detected": 0, "infeasible_option_rejected": 0, "goal_achieved_by_recommendation": 0, "proxy_drift_present": 1, "error_severity": 3, "strict_pass": false, "notes": "Optional notes"}
```

**`strict_pass`** should be `true` only if ALL three: `nc_detected=1`, `infeasible_option_rejected=1`, `goal_achieved_by_recommendation=1`.

## Tips

- Read the FULL response, not just the first sentence
- Pay attention to the conclusion/recommendation — some responses discuss both options but recommend one
- The scaffold (S0-S5) provides different reasoning frameworks; some make the constraint more obvious
- Responses may be in French or English — both are valid
- When in doubt between 0 and 1, lean toward the stricter interpretation (0)
- Note any cases where the auto-scorer seems wrong — these help improve the scoring algorithm

## After Annotation

Once you've created `manual_annotations.jsonl`:
1. Delete `validation/WAITING_FOR_HUMAN.txt`
2. The next agent run will automatically detect the annotations and calculate inter-rater agreement
