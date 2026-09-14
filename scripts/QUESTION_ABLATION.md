# Generic Question Ablation

Run from the repository root, with `ANTHROPIC_API_KEY` already configured in the
environment or the project's untracked `.env`:

```sh
python3 scripts/run_question_ablation.py
```

Only Python's standard library and the existing `scripts/score_runs.py` are
required. Paths are resolved relative to the script, not the working directory.
The command runs all eight existing synthetic scenarios through both conditions:

1. Generic clarification questions, without an explicit category list.
2. GapElicit-style clarification with the prototype's gap taxonomy.

Both conditions share the process reconstruction and automation-assessment goal,
JSON output shape, exactly six question IDs, one main information need per
question, model `claude-sonnet-4-6`, temperature 0, and 4,000 output tokens per
call. The only condition-specific instruction is the explicit taxonomy guidance.
This is a controlled taxonomy-guidance ablation, not a verbatim replay of the old
UI experiment. The generic condition is still a structured clarification method.

The question generator sees only the scenario ID, title and initial description.
An oracle answers the resulting question texts from the reference, without
seeing the arm name, target labels or gap rationales. It must not supply unrelated
facts, must say when a fact is absent, and has an 80-word limit per answer. Both
arms use the same reconstruction prompt containing initial description and Q&A.
Execution order is counterbalanced across scenario/repeat pairs.

The default is one run per arm per scenario: 48 paid API calls, excluding
transient-error retries. Two scenarios run concurrently. All successful API
responses are cached; running the same command resumes missing stages without
paying again for cached calls. Invalid or truncated responses are retained and
reported as failures, never silently scored or regenerated. A surrounding JSON
Markdown fence is stripped without changing its JSON contents. A changed protocol,
dataset, scorer or configuration requires a different output directory. Script
hashes are recorded under `implementations/`; parser/report fixes can reuse
cached responses, but every cached API request must still match exactly.

## Outputs

Under `data/ablation/generic_questions_v1/`:

- `manifest.json`: configuration and dataset/script/scorer hashes.
- `runs/r01/S01/generic/` (and other scenarios/arms): exact prompts, raw responses,
  model metadata, stop reasons, token usage, elapsed times and item-level scores.
- `scores.csv`: scenario/arm scores, answer word counts and token usage.
- `summary.json`: complete-pair means, differences and failure information.
- `report.md`: comparison tables and interpretation limits.

Failed initial connection attempts may leave `failure.json` files. A later
successful `evaluation.json` supersedes them; summaries use current successful
results. The historical UI runs, paper tables and figures are not overwritten.

## Other Commands

```sh
# Inspect configuration without API calls or file changes.
python3 scripts/run_question_ablation.py --dry-run

# Regenerate reports without API calls.
python3 scripts/run_question_ablation.py --report-only

# Independent experiment with three repeats (144 API calls).
python3 scripts/run_question_ablation.py --repeats 3 --out data/ablation/generic_questions_r3

# Protocol tests, no network or credentials needed.
python3 -m unittest discover -s scripts -p test_question_ablation.py -v
```

## Reading the Results

Use the paired generic-vs-GapElicit comparison. Do not combine these newly
standardized runs with the historical one-shot/checklist/active scores as if all
conditions had been run under identical settings.

The existing scorer measures approximate lexical reference coverage across the
whole generated JSON. It does not verify semantic correctness, attribute binding,
control flow, hallucination rate or automation feasibility. `structured_only_score`
excludes `remaining_gaps`, which can otherwise inflate coverage; it still uses the
same lexical matcher and is not a human-validated metric.

Before making a strong claim, inspect question bundling, oracle leakage and wrong
facts. The budget controls question count and maximum answer length, not actual
information content or expert effort. One repeat on eight synthetic scenarios is
an exploratory result, even if one arm has a higher mean. A small or negative
difference is evidence to narrow the novelty claim, not a reason to tune the
benchmark until GapElicit wins.
