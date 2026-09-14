# Two-Domain Taxonomy Ablation

From the parent workspace:

```sh
python3 scripts/run_domain_ablation.py
```

Requires Python's standard library, the existing `run_question_ablation.py` and
`score_runs.py`, and `ANTHROPIC_API_KEY` in the environment or untracked project
`.env`. Paths resolve relative to the script. No web UI or server is required.

## Matrix

| Dataset | Generic questions | Common taxonomy | Contextualized taxonomy |
|---|---|---|---|
| Original engineering/office scenarios S01-S08 | Cached original | Cached original | New semiconductor-work profile |
| New childcare scenarios C01-C08 | New | New | New childcare profile |

Sixteen scenarios, three arms, one generation per arm. Each condition generates
six questions, obtains six oracle answers capped at 80 words each, and reconstructs
a workflow. All use the matched pilot's model and settings: Sonnet 4.6, temperature
0, maximum 4,000 output tokens per call. Exactly the same oracle and reconstruction
prompts are used. Domain explanations are appended only to question generation.

The 48 existing baseline responses are reused after request/configuration/hash
checks; 96 new responses are required, excluding transient API retries. All
conditions therefore represent 144 responses and 48 final workflows in total.
Four scenarios run concurrently; condition order rotates across scenarios.

## Frozen Endpoint

Primary descriptive endpoint: the mean of seven legacy category scores after
removing `remaining_gaps` from the output and excluding the automation-opportunity
category. The latter uses reference activity IDs as targets and can otherwise
match those IDs anywhere in output, producing misleadingly high opportunity scores.

This remains approximate lexical reference coverage. The retained text includes
the workflow and automation-opportunity descriptions, so a fact can still match
in a proposed opportunity rather than the correct workflow location. It does not
verify semantic correctness, false additions, actual ownership/control flow or
automation feasibility. It is not a new validated evaluation metric.

The existing eight-category whole-JSON score is also saved as `legacy_coverage`;
the eight-category version without gaps is `structured_coverage`. These sensitivity
outputs preserve comparison transparency. None replaces paper tables automatically.
Report methods within each domain rather than ranking domain difficulty by score.

## Files and Resuming

Under `data/ablation/domain_taxonomy_v1/`:

- `manifest.json`: freeze timestamp, hashes, settings and primary endpoint.
- `runs/<domain>/<scenario>/<arm>/evaluation.json`: category/item-level results,
  answer length, token counts and source-log paths.
- New runs also contain exact requests and raw responses for all three stages.
- `scores.csv`, `summary.json`, `report.md`: separate domain summaries and contrasts.

Successful responses are cached. Running the same command resumes remaining stages.
Invalid/truncated responses are retained and reported, not silently regenerated or
scored. Failed connection attempts may leave `failure.json`; a successful evaluation
supersedes that record. A change to frozen experimental inputs requires a new output
directory. The baseline outputs, paper and public artifact are preserved.

```sh
python3 scripts/run_domain_ablation.py --dry-run
python3 scripts/run_domain_ablation.py --report-only
```

No incompatible-domain taxonomy, three-agent condition, real participant study,
independent factual correctness annotation, or repeated-generation evaluation is
included in this experiment. These should not be implied when reporting results.
