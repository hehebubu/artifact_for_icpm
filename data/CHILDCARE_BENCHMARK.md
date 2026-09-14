# Childcare Coordination Benchmark v1

This is an AI-assisted synthetic benchmark for conversational workflow elicitation.
It is not a collection of interviews, event logs, observed households or validated
caregiving recommendations. The narrator is a fictional mother; responsibility is
shared with other caregivers and childcare staff. No real child records or company
data were used. It does not measure parenting quality or replace human care.

## Scenarios

| ID | Routine | Main coordination boundary |
|---|---|---|
| C01 | Morning preparation and drop-off | Family preparation to childcare handover |
| C02 | Pickup and caregiver handover | Collector availability and provider acknowledgment |
| C03 | Notices and consent responses | Provider messages to family decision and preparation |
| C04 | Outing preparation and return | Shared plans, physical items and restocking |
| C05 | Weekly shared caregiving schedule | Availability to accepted care assignments |
| C06 | Supply stock and replenishment | Household inventory to parent-confirmed purchase |
| C07 | Evening handover and next-day preparation | Incoming caregiver to next-day owner |
| C08 | Activity enrollment and schedule changes | Family approval to provider confirmation |

## Structure

`scenarios_childcare.json` follows the existing scenario format:

- `initial_description`: short first-person account with omitted details.
- `reference_workflow`: fictional reference actors, systems, inputs, outputs,
  activities, decisions, exceptions, dependencies and support opportunities.
- `intentionally_missing_in_initial_description`: omission categories.
- `omission_grounding`: JSON pointers to reference sections that contain the
  omitted information, enabling structural integrity checks.
- `unknown_information`: details not established by the synthetic case.

Each reference has eight activities, two decisions, four exceptions, four actors,
four systems, four inputs, four outputs and three candidate support opportunities.
This artificial regularity simplifies a pilot but limits realism. Dependencies
describe the nominal sequence; decisions qualify the flow. They are not executable
BPMN graphs and should not be evaluated as formally verified models.

References also include fictional frequency, manual effort, data access and
approval/integration constraints in `operating_context`. These are invented case
facts, not empirical measurements or population norms. Unspecified exact times,
prices, product specifications or policy details remain unknown. The oracle must
not invent them.

The older engineering benchmark often lacks these operating-context values and
includes office coordination cases. It was not rewritten after its results were
observed. Consequently, differences in absolute domain scores are confounded by
reference construction and cannot establish a causal domain effect.

## Taxonomy Design

`domain_taxonomies.json` retains exactly the original twelve prototype categories.
The semiconductor-work and childcare profiles add one contextual explanation per
category. They do not add categories or inject individual scenario answers.
These are operational prompt designs, not independently validated expert taxonomies.

The generic condition has no explicit category list. The common condition includes
the original list. The domain condition appends the relevant contextual profile.
The domain prompts are longer and contain domain vocabulary; this is a limitation
without a length-matched prompt control.

## Experimental Status

The new dataset, profiles, script and endpoint were frozen by SHA-256 in the
experiment manifest before the new API calls. They were designed after prior
engineering results were known, so this is an additional-domain exploratory study,
not an independent held-out confirmation or a representative user evaluation.

All three childcare conditions receive the same reference through the oracle only.
Question generators and reconstructors never receive the reference or omission map.
The record of frequency and effort is available to the oracle but is not directly
scored by the seven-category process endpoint. No downstream automation effectiveness
or clinical/care outcome is measured.
