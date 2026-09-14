# Domain Taxonomy Ablation

Primary endpoint: structured seven-category lexical process coverage.

Remaining-gap text and ID-only automation-opportunity matching are excluded; semantic correctness is not established.

## semiconductor_work

Complete scenarios: 8/8

| Scenario | Generic | Common | Domain |
|---|---:|---:|---:|
| S01 | 0.9821 | 0.8929 | 0.8096 |
| S02 | 0.9524 | 0.9167 | 0.9524 |
| S03 | 0.9643 | 0.9286 | 0.9286 |
| S04 | 0.8929 | 0.7107 | 0.7500 |
| S05 | 0.9286 | 0.9643 | 0.8929 |
| S06 | 0.8214 | 0.8214 | 0.6929 |
| S07 | 0.7449 | 0.7449 | 0.9234 |
| S08 | 0.9167 | 0.8453 | 0.8334 |
| Mean | 0.9004 | 0.8531 | 0.8479 |

| Metric | Generic | Common | Domain |
|---|---:|---:|---:|
| legacy_coverage | 0.9207 | 0.8664 | 0.8798 |
| structured_coverage | 0.9076 | 0.8664 | 0.8615 |
| answer_words | 264.5000 | 229.5000 | 228.7500 |
| activities | 0.9486 | 0.9174 | 0.9226 |
| actors | 0.9167 | 0.8855 | 0.8251 |
| systems | 0.9375 | 0.9062 | 1.0000 |
| inputs | 0.9062 | 0.9062 | 0.7812 |
| outputs | 0.9375 | 0.8250 | 0.8438 |
| decisions | 0.8750 | 0.8750 | 0.9375 |
| exceptions | 0.7812 | 0.6562 | 0.6250 |

## childcare

Complete scenarios: 8/8

| Scenario | Generic | Common | Domain |
|---|---:|---:|---:|
| C01 | 0.8571 | 0.8214 | 0.9286 |
| C02 | 0.9286 | 1.0000 | 0.9107 |
| C03 | 0.7143 | 0.8214 | 0.8036 |
| C04 | 0.9643 | 1.0000 | 0.9643 |
| C05 | 0.8393 | 0.7679 | 0.8214 |
| C06 | 0.9286 | 0.7143 | 0.9107 |
| C07 | 0.8393 | 0.8214 | 0.8750 |
| C08 | 0.9464 | 0.9286 | 1.0000 |
| Mean | 0.8772 | 0.8594 | 0.9018 |

| Metric | Generic | Common | Domain |
|---|---:|---:|---:|
| legacy_coverage | 0.8940 | 0.8790 | 0.9201 |
| structured_coverage | 0.8822 | 0.8771 | 0.9143 |
| answer_words | 251.7500 | 243.6250 | 236.2500 |
| activities | 0.9531 | 0.9219 | 0.9375 |
| actors | 0.7188 | 0.8125 | 0.8125 |
| systems | 0.8438 | 0.8750 | 0.9062 |
| inputs | 0.8750 | 0.8438 | 0.8438 |
| outputs | 0.9062 | 0.8438 | 0.9062 |
| decisions | 1.0000 | 0.9375 | 1.0000 |
| exceptions | 0.8438 | 0.7812 | 0.9062 |

## Interpretation Limits

One repeat, eight synthetic cases per domain. Semiconductor-work includes engineering documentation and office coordination, not only verification. Its generic/common outputs are reused exactly from the previous development pilot; domain-conditioned outputs and all childcare outputs are newly generated.

Childcare data and all prompts were frozen before these new API outcomes, but were AI-assisted designs made after inspecting previous experiments. This is not an independent human-authored or population-representative benchmark.

Domain prompts append contextual explanations to the same 12 common categories. They add prompt tokens and domain vocabulary, not category count. There is no length-matched irrelevant-context control.

Childcare references explicitly contain fictional frequency/effort/access constraints; older engineering references often lack them. Structural counts and reference construction also differ. Compare methods within domains; do not interpret cross-domain absolute scores as task difficulty or a causal domain effect.

Primary process coverage excludes remaining_gaps and the legacy automation-opportunity category because that matcher can match an activity ID anywhere in JSON. It still uses a lexical matcher over the retained workflow/opportunity text, can count unsupported facts, and does not measure precision or automation quality. Legacy scores are retained for transparency, not substituted silently into paper tables.

Question count is six and oracle answers are limited to 80 words each in all conditions, but actual information content and question breadth can vary. Oracle factuality and real caregiver experience are not validated.

No manuscript, historical result table, or published anonymous repository was modified.
