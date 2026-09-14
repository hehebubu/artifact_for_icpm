# Matched Question Ablation

Complete pairs: 8/8.

| Scenario | Repeat | Generic | GapElicit | Difference |
|---|---:|---:|---:|---:|
| S01 | 1 | 0.984 | 0.906 | -0.078 |
| S02 | 1 | 1.000 | 0.927 | -0.073 |
| S03 | 1 | 0.969 | 0.938 | -0.031 |
| S04 | 1 | 0.938 | 0.747 | -0.191 |
| S05 | 1 | 0.938 | 0.969 | +0.031 |
| S06 | 1 | 0.875 | 0.844 | -0.031 |
| S07 | 1 | 0.735 | 0.735 | +0.000 |
| S08 | 1 | 0.927 | 0.865 | -0.062 |
| Mean | | 0.921 | 0.866 | -0.054 |

| Category | Generic | GapElicit |
|---|---:|---:|
| activities | 0.949 | 0.917 |
| actors | 0.958 | 0.885 |
| systems | 0.938 | 0.906 |
| inputs | 0.906 | 0.906 |
| outputs | 0.938 | 0.825 |
| decisions | 0.875 | 0.875 |
| exceptions | 0.844 | 0.656 |
| automation_opportunities | 0.958 | 0.958 |
| structured_only_score | 0.908 | 0.866 |
| answer_words | 264.500 | 229.500 |

## Interpretation Limits

This pilot controls model, question count, answer instructions and workflow reconstruction. The sole arm-specific prompt text is the taxonomy guidance. Generic questioning still uses the same process/automation objective and structured question output; it is not an unstructured chat baseline.

Oracle answers can differ in length/content because questions differ. Equal question counts do not guarantee equal information or expert effort. Inspect questions for bundled requests and answers for leakage.

The legacy lexical coverage score searches the entire generated JSON and does not establish correctness. The structured-only sensitivity score excludes remaining_gaps, but is still lexical. There is no human validation, hallucination penalty, or verified automation feasibility in this score.

Historical 0.725/0.753/0.925 results are context, not matched controls: the new protocol fixes temperature, uses concise oracle answers, and standardizes downstream inputs. Do not replace the old results table by mixing these runs into it.

One repeat per scenario is exploratory. Repeated generations do not increase the number of independent scenarios.

Failures: 0. Means include complete pairs only; inspect summary.json for details.
