# Output-side provenance (output-side-v1)

2671 output item-run pairs over 56 distinct pipelines. One row is a distinct normalized string within a run and a category. The forward analysis counts reference item-run pairs, so the two totals are not comparable item for item.

| Criterion | In reference | Grounded outside | Abstention | Restated artifact | Untraceable | Per run |
|---|---:|---:|---:|---:|---:|---:|
| document | 1972 | 333 | 63 | 74 | **229** | 4.09 |
| field | 1437 | 653 | 68 | 116 | **397** | 7.09 |
| exact | 578 | 63 | 80 | 428 | **1522** | 27.18 |

## Untraceable elements by category (within-field)

| Category | Untraceable |
|---|---:|
| activities | 38 |
| actors | 10 |
| systems | 10 |
| inputs | 132 |
| outputs | 124 |
| decisions | 29 |
| exceptions | 54 |

Of those, 121 fall in the structural categories (activities, decisions, exceptions). 15 of the untraceable exceptions state in so many words that the process defines no path for the case they raise, which is the model reporting a gap rather than inventing a step.

## Placeholders counted as abstentions

`unknown` (42), `unspecified` (12), `none` (7), `none specified` (5), `unclear` (1), `na` (1)

## Sample of untraceable elements (within-field)

- [inputs] Validity Assessment
- [outputs] Review Outcome (Accepted or Clarification Requested)
- [inputs] selected equipment
- [outputs] selected equipment (A, B, or C)
- [outputs] exception record
- [inputs] Transferred sample
- [inputs] Disposal eligibility determination
- [inputs] Retention determination
- [outputs] Updated storage location record
- [outputs] Team notifications
- [exceptions] Repeated failure to support root-cause hypothesis after multiple experiment cycles may require escalation or external expert involvement, but no formal exception path is defined in the reference workflow.
- [inputs] Confirmed revised specification document
- [outputs] Meeting invitation with agenda distributed to participants
- [decisions] Are all action items sufficiently progressed or resolved?
- [exceptions] Vendor representative unavailable to attend scheduled meeting — rescheduling process not defined
- [exceptions] Action-item owner unresponsive or unable to complete assigned item — escalation path not defined
- [exceptions] Meeting notes not captured or incomplete — no validation step identified
- [activities] Check Clarity of Action Items
- [exceptions] Meeting notes or transcript are unavailable or incomplete after the meeting concludes, preventing the workflow from starting.
- [exceptions] Decision owner is unresponsive when contacted to clarify action items.

Lexical absence is not semantic absence: these are elements no lexical test traces to the reference, the description or the answers, not confirmed fabrications. A human check of a sample is the only way to size that gap.
