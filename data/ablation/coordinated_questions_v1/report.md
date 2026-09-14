# Coordinated Question Pilot

Complete scenarios: 8/8

| Scenario | Generic | Taxonomy | Coordinated |
|---|---:|---:|---:|
| S01 | 0.984 | 0.906 | 0.938 |
| S02 | 1.000 | 0.927 | 0.909 |
| S03 | 0.969 | 0.938 | 1.000 |
| S04 | 0.938 | 0.747 | 0.922 |
| S05 | 0.938 | 0.969 | 0.938 |
| S06 | 0.875 | 0.844 | 0.865 |
| S07 | 0.735 | 0.735 | 0.704 |
| S08 | 0.927 | 0.865 | 0.896 |
| Mean | 0.921 | 0.866 | 0.896 |

| Metric | Generic | Taxonomy | Coordinated |
|---|---:|---:|---:|
| structured_only_score | 0.908 | 0.866 | 0.889 |
| answer_words | 264.500 | 229.500 | 254.750 |
| pipeline_calls | 3.000 | 3.000 | 5.000 |
| input_tokens | 2907.750 | 2898.625 | 4371.000 |
| output_tokens | 4032.000 | 4315.250 | 6438.250 |
| activities | 0.949 | 0.917 | 0.931 |
| actors | 0.958 | 0.885 | 0.917 |
| systems | 0.938 | 0.906 | 0.906 |
| inputs | 0.906 | 0.906 | 0.938 |
| outputs | 0.938 | 0.825 | 0.906 |
| decisions | 0.875 | 0.875 | 0.938 |
| exceptions | 0.844 | 0.656 | 0.719 |
| automation_opportunities | 0.958 | 0.958 | 0.917 |

## Protocol and Limits

Two independent, cached proposal agents (generic and taxonomy-guided) provide six candidates each. A third coordinator selects/refines six final questions; there is no iterative debate. All roles use the same LLM. They do not represent actual laypeople and experts.

The coordinator receives only initial description and candidate texts. It has no reference, score, baseline outcome, or candidate source labels. Provenance is reconstructed after selection.

Answer and reconstruction prompts/settings are unchanged from the matched pilot. Question budgets match, but coordination uses three question-generation calls instead of one. Pipeline token counts include both cached proposal calls: five calls versus three per baseline. This execution adds only three fresh calls per scenario because proposals are reused.

This is an adaptive exploratory experiment on the same eight scenarios after observing baseline results. There is no held-out test, repeated-generation estimate, human correctness evaluation, or compute-matched single-agent refinement control. A higher mean cannot establish general superiority or unique multi-agent value.

Legacy coverage is lexical and may count unknown facts in remaining_gaps. Structured-only excludes that field but still does not establish semantic correctness or automation feasibility. Oracle answers may overinfer facts.

Coordinator candidate-source counts: {
  "generic_only": 21,
  "gapelicit_only": 9,
  "mixed": 18
}

No historical paper tables or manuscript text were changed.
