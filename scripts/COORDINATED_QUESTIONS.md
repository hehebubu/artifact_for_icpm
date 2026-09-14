# Coordinated Question Experiment

From the repository root:

```sh
python3 scripts/run_coordinated_questions.py
```

Uses Python's standard library, the existing `run_question_ablation.py` helpers,
and the saved `data/ablation/generic_questions_v1` experiment. Requires
`ANTHROPIC_API_KEY` in the environment or the untracked project `.env` for live
calls. Never put credentials into a tracked script or command-line argument.

## Three Questioning Roles

1. General-purpose proposer: reuses the six questions generated without an
   explicit taxonomy in the matched baseline experiment.
2. Taxonomy-guided proposer: reuses the six questions generated with the
   prototype's automation-critical gap categories.
3. Coordinator: receives the initial task description and twelve candidate
   question texts, then selects, rephrases or merges candidates into six final
   questions, recording candidate IDs and selection reasons.

The proposers are independent calls to the same model, not actual novice or
expert respondents, and not models trained to represent distinct human expertise.
This is a proposal-and-coordination architecture, not repeated debate. Reusing
the exact baseline proposals allows inspection of what selection changes, with
no resampling or selection of favorable proposal runs.

Candidate source names are hidden from the coordinator; their presentation order
alternates across scenarios. Only question texts and opaque IDs are provided.
The coordinator cannot access reference workflows, scoring functions, previous
scores, or baseline generated answers/workflows. Source attribution is recovered
locally after selection from a saved mapping.

The coordinator prompt considers relevance, uncertainty, expected answer value,
respondent burden and redundancy. It does not instruct the coordinator to avoid
particular categories that performed poorly in the preceding pilot.

The oracle sees the six final question texts but not their provenance or selection
reasons. Oracle and workflow reconstruction use the exact same prompts, model,
temperature and token budgets as the matched pilot. The reference appears only
in the oracle prompt. Each answer has the same 80-word maximum.

## Cost and Outputs

There are 24 fresh calls: coordinator, oracle and reconstruction for each of eight
scenarios. The two proposal calls per scenario are cached. A complete deployment
would therefore require five calls per scenario, versus three for either baseline.
Reported pipeline token counts include cached proposals, not just incremental cost.

Results are written to `data/ablation/coordinated_questions_v1/`:

- `manifest.json`: source response hashes and implementation/settings provenance.
- `runs/S01/` etc.: source mapping, coordinator response, oracle response,
  reconstruction, item-level scores and source-selection counts.
- `scores.csv`: all three conditions with score, answer length and token counts.
- `summary.json`: complete-case means and paired wins/ties/losses.
- `report.md`: comparison tables and interpretation limits.

Successful responses are cached and reused on rerun. API failures and invalid
responses are reported without silently selecting a better generation. A JSON
Markdown fence may be stripped, but malformed/truncated content is not repaired.
Historical source outputs and paper tables are preserved.

```sh
python3 scripts/run_coordinated_questions.py --dry-run
python3 scripts/run_coordinated_questions.py --report-only
python3 -m unittest discover -s scripts -p 'test_*.py' -v
```

## Interpretation

This is an exploratory experiment designed after observing the first comparison
on the same eight scenarios. It is development evidence, not a held-out confirmation
of a new best method. There is one generation per scenario/condition, and no
compute-matched single-agent refinement baseline. Role labels, multiple API calls,
or a higher average alone do not establish novelty or a causal multi-agent benefit.

The automatic score is approximate lexical reference coverage, not semantic
correctness. The structured-only sensitivity score removes `remaining_gaps` but
still uses lexical matching. Questions can differ in breadth and answers in actual
length despite the shared count and upper bound. Inspect oracle inferences and
unsupported workflow statements before making substantive quality claims.
