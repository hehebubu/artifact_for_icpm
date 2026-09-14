# Item-Level Provenance of Reference Facts

Cached-log analysis of 72 stored arms (56 distinct pipelines; cached arms replay logs owned by another corpus and are pooled only in the per-arm tables). No new model calls.

Every reference item is traced through the initial description, the clarification questions, the simulated expert answers, and the reconstructed workflow. Labels: `carried`/`lost` for items already stated in the initial description; `recovered`/`dropped` for newly answered items that the reconstruction keeps or loses; `unsupported` for items present in the output but in neither the description nor the answers; `missed` for items neither answered nor produced.

Process-category items: 1644. Answer retention 0.9812, description retention 0.9922, unsupported share of newly produced items 0.0859.

## By corpus and arm

| Group | items | carried | lost | recovered | dropped | unsupported | missed | description_retention | answer_retention | unsupported_share_of_new_output |
|---|---|---|---|---|---|---|---|---|---|---|
| generic_questions_v1/generic | 231 | 24 | 0 | 167 | 2 | 19 | 19 | 1.000 | 0.988 | 0.102 |
| generic_questions_v1/gapelicit | 231 | 24 | 0 | 154 | 1 | 20 | 32 | 1.000 | 0.994 | 0.115 |
| coordinated_questions_v1/coordinated | 231 | 24 | 0 | 169 | 3 | 12 | 23 | 1.000 | 0.983 | 0.066 |
| domain_taxonomy_v1/generic | 471 | 35 | 0 | 349 | 6 | 37 | 44 | 1.000 | 0.983 | 0.096 |
| domain_taxonomy_v1/common | 471 | 35 | 0 | 339 | 4 | 31 | 62 | 1.000 | 0.988 | 0.084 |
| domain_taxonomy_v1/domain | 471 | 34 | 1 | 346 | 10 | 33 | 47 | 0.971 | 0.972 | 0.087 |

## By domain

| Group | items | carried | lost | recovered | dropped | unsupported | missed | description_retention | answer_retention | unsupported_share_of_new_output |
|---|---|---|---|---|---|---|---|---|---|---|
| semiconductor_work | 924 | 95 | 1 | 651 | 9 | 64 | 104 | 0.990 | 0.986 | 0.089 |
| childcare | 720 | 33 | 0 | 552 | 14 | 49 | 72 | 1.000 | 0.975 | 0.082 |

## By information category

| Group | items | carried | lost | recovered | dropped | unsupported | missed | description_retention | answer_retention | unsupported_share_of_new_output |
|---|---|---|---|---|---|---|---|---|---|---|
| activities | 424 | 53 | 1 | 332 | 3 | 11 | 24 | 0.982 | 0.991 | 0.032 |
| actors | 220 | 26 | 0 | 160 | 6 | 1 | 27 | 1.000 | 0.964 | 0.006 |
| systems | 216 | 12 | 0 | 170 | 0 | 14 | 20 | 1.000 | 1.000 | 0.076 |
| inputs | 224 | 10 | 0 | 168 | 3 | 17 | 26 | 1.000 | 0.983 | 0.092 |
| outputs | 220 | 20 | 0 | 140 | 6 | 33 | 21 | 1.000 | 0.959 | 0.191 |
| decisions | 116 | 4 | 0 | 98 | 1 | 7 | 6 | 1.000 | 0.990 | 0.067 |
| exceptions | 224 | 3 | 0 | 135 | 4 | 30 | 52 | 1.000 | 0.971 | 0.182 |

## By scenario

| Group | items | carried | lost | recovered | dropped | unsupported | missed | description_retention | answer_retention | unsupported_share_of_new_output |
|---|---|---|---|---|---|---|---|---|---|---|
| semiconductor_work/S01 | 116 | 20 | 0 | 78 | 3 | 7 | 8 | 1.000 | 0.963 | 0.082 |
| semiconductor_work/S02 | 108 | 12 | 0 | 79 | 3 | 10 | 4 | 1.000 | 0.963 | 0.112 |
| semiconductor_work/S03 | 120 | 4 | 0 | 102 | 0 | 9 | 5 | 1.000 | 1.000 | 0.081 |
| semiconductor_work/S04 | 128 | 8 | 0 | 86 | 0 | 10 | 24 | 1.000 | 1.000 | 0.104 |
| semiconductor_work/S05 | 116 | 8 | 0 | 100 | 0 | 0 | 8 | 1.000 | 1.000 | 0.000 |
| semiconductor_work/S06 | 120 | 20 | 0 | 64 | 0 | 16 | 20 | 1.000 | 1.000 | 0.200 |
| semiconductor_work/S07 | 116 | 4 | 0 | 81 | 1 | 6 | 24 | 1.000 | 0.988 | 0.069 |
| semiconductor_work/S08 | 100 | 19 | 1 | 61 | 2 | 6 | 11 | 0.950 | 0.968 | 0.090 |
| childcare/C01 | 90 | 6 | 0 | 67 | 4 | 6 | 7 | 1.000 | 0.944 | 0.082 |
| childcare/C02 | 90 | 3 | 0 | 79 | 2 | 3 | 3 | 1.000 | 0.975 | 0.037 |
| childcare/C03 | 90 | 0 | 0 | 59 | 1 | 12 | 18 | -- | 0.983 | 0.169 |
| childcare/C04 | 90 | 0 | 0 | 84 | 0 | 4 | 2 | -- | 1.000 | 0.045 |
| childcare/C05 | 90 | 0 | 0 | 64 | 2 | 9 | 15 | -- | 0.970 | 0.123 |
| childcare/C06 | 90 | 3 | 0 | 65 | 0 | 9 | 13 | 1.000 | 1.000 | 0.122 |
| childcare/C07 | 90 | 9 | 0 | 64 | 4 | 2 | 11 | 1.000 | 0.941 | 0.030 |
| childcare/C08 | 90 | 12 | 0 | 70 | 1 | 4 | 3 | 1.000 | 0.986 | 0.054 |

## Most frequently dropped answered items

- 3x `outputs` checked bag
- 2x `actors` equipment owner
- 2x `actors` facility system
- 2x `exceptions` conflicting task information
- 1x `decisions` Does the meeting require task tracking?
- 1x `exceptions` missing setup information
- 1x `activities` Check equipment availability and reserve slot
- 1x `actors` mother
- 1x `activities` Save provider confirmation before marking enrollment complete
- 1x `outputs` change acknowledgment
- 1x `inputs` authorized pickup names
- 1x `outputs` provider acknowledgment

## Most frequent unsupported output items

- 4x `inputs` target location
- 3x `exceptions` equipment unavailable
- 3x `exceptions` wafer information mismatch
- 3x `systems` calendar system
- 3x `outputs` updated improvement proposal
- 3x `inputs` meeting agenda
- 3x `exceptions` missing transcript
- 3x `outputs` calendar entry
- 3x `outputs` weekly care plan
- 3x `outputs` verified inventory
- 2x `decisions` Is the sample available and correctly identified?
- 2x `systems` experiment log

## Sensitivity to the lexical match criterion

The stored scorer tokenizes the whole serialized output, including its JSON keys, and counts an item as covered when its informative tokens each occur anywhere in that document, so tokens scattered across unrelated fields satisfy it. Two stricter criteria repeat the same accounting: `within-field` requires the same token test to pass inside a single field value, and `exact` requires the full normalized phrase inside a single field value. The within-field criterion is the one worth adopting; the exact criterion is a lower bound that any rewording defeats.

Of the items the stored criterion counts as covered, 0.8352 survive the within-field test and 0.4952 match exactly. Recovered items fall from 1203 to 1013 to 556, and missed items rise from 176 to 286 to 895, across the three criteria.

### Overall

| Criterion | items | carried | lost | recovered | dropped | unsupported | missed | description_retention | answer_retention | unsupported_share_of_new_output |
|---|---|---|---|---|---|---|---|---|---|---|
| stored document criterion | 1644 | 128 | 1 | 1203 | 23 | 113 | 176 | 0.992 | 0.981 | 0.086 |
| within-field criterion | 1644 | 118 | 11 | 1013 | 141 | 75 | 286 | 0.915 | 0.878 | 0.069 |
| exact phrase criterion | 1644 | 4 | 0 | 556 | 34 | 155 | 895 | 1.000 | 0.942 | 0.218 |

### Findings that hold under both the stored and the within-field criterion

- recovered: 1013
- dropped: 14, of which 14 leave no trace of the item anywhere in the output
- unsupported: 55
- missed: 176

A further 127 answered items are counted as dropped only by the within-field criterion: their words do occur in the output but never inside one field value, which is what a reworded activity name looks like as well as what a real omission looks like. That gap is the part only human reading can settle.

### By arm, within-field criterion

| Group | items | carried | lost | recovered | dropped | unsupported | missed | description_retention | answer_retention | unsupported_share_of_new_output |
|---|---|---|---|---|---|---|---|---|---|---|
| generic_questions_v1/generic | 231 | 21 | 3 | 150 | 12 | 9 | 36 | 0.875 | 0.926 | 0.057 |
| generic_questions_v1/gapelicit | 231 | 21 | 3 | 135 | 16 | 8 | 48 | 0.875 | 0.894 | 0.056 |
| coordinated_questions_v1/coordinated | 231 | 22 | 2 | 153 | 13 | 3 | 38 | 0.917 | 0.922 | 0.019 |
| domain_taxonomy_v1/generic | 471 | 32 | 3 | 297 | 38 | 24 | 77 | 0.914 | 0.887 | 0.075 |
| domain_taxonomy_v1/common | 471 | 31 | 4 | 279 | 47 | 19 | 91 | 0.886 | 0.856 | 0.064 |
| domain_taxonomy_v1/domain | 471 | 33 | 2 | 284 | 43 | 29 | 80 | 0.943 | 0.869 | 0.093 |

### By arm, exact phrase criterion

| Group | items | carried | lost | recovered | dropped | unsupported | missed | description_retention | answer_retention | unsupported_share_of_new_output |
|---|---|---|---|---|---|---|---|---|---|---|
| generic_questions_v1/generic | 231 | 1 | 0 | 88 | 5 | 34 | 103 | 1.000 | 0.946 | 0.279 |
| generic_questions_v1/gapelicit | 231 | 1 | 0 | 84 | 3 | 18 | 125 | 1.000 | 0.966 | 0.176 |
| coordinated_questions_v1/coordinated | 231 | 1 | 0 | 91 | 5 | 29 | 105 | 1.000 | 0.948 | 0.242 |
| domain_taxonomy_v1/generic | 471 | 1 | 0 | 156 | 15 | 51 | 248 | 1.000 | 0.912 | 0.246 |
| domain_taxonomy_v1/common | 471 | 1 | 0 | 148 | 6 | 34 | 282 | 1.000 | 0.961 | 0.187 |
| domain_taxonomy_v1/domain | 471 | 1 | 0 | 161 | 8 | 41 | 260 | 1.000 | 0.953 | 0.203 |

### By category, within-field criterion

| Group | items | carried | lost | recovered | dropped | unsupported | missed | description_retention | answer_retention | unsupported_share_of_new_output |
|---|---|---|---|---|---|---|---|---|---|---|
| activities | 424 | 51 | 3 | 233 | 76 | 3 | 58 | 0.944 | 0.754 | 0.013 |
| actors | 220 | 19 | 7 | 154 | 6 | 4 | 30 | 0.731 | 0.963 | 0.025 |
| systems | 216 | 12 | 0 | 166 | 2 | 10 | 26 | 1.000 | 0.988 | 0.057 |
| inputs | 224 | 10 | 0 | 151 | 9 | 14 | 40 | 1.000 | 0.944 | 0.085 |
| outputs | 220 | 19 | 1 | 122 | 14 | 25 | 39 | 0.950 | 0.897 | 0.170 |
| decisions | 116 | 4 | 0 | 71 | 18 | 3 | 20 | 1.000 | 0.798 | 0.041 |
| exceptions | 224 | 3 | 0 | 116 | 16 | 16 | 73 | 1.000 | 0.879 | 0.121 |

### By category, exact phrase criterion

| Group | items | carried | lost | recovered | dropped | unsupported | missed | description_retention | answer_retention | unsupported_share_of_new_output |
|---|---|---|---|---|---|---|---|---|---|---|
| activities | 424 | 0 | 0 | 3 | 8 | 62 | 351 | -- | 0.273 | 0.954 |
| actors | 220 | 0 | 0 | 163 | 6 | 2 | 49 | -- | 0.965 | 0.012 |
| systems | 216 | 0 | 0 | 164 | 2 | 8 | 42 | -- | 0.988 | 0.046 |
| inputs | 224 | 4 | 0 | 111 | 5 | 30 | 74 | 1.000 | 0.957 | 0.213 |
| outputs | 220 | 0 | 0 | 73 | 9 | 28 | 110 | -- | 0.890 | 0.277 |
| decisions | 116 | 0 | 0 | 2 | 0 | 17 | 97 | -- | 1.000 | 0.895 |
| exceptions | 224 | 0 | 0 | 40 | 4 | 8 | 172 | -- | 0.909 | 0.167 |

### Items counted as covered only by tokens scattered across fields

- 4x `decisions` Which equipment is required for the requested measurement?
- 4x `exceptions` recipe not approved
- 4x `activities` Move sample to target location
- 4x `activities` Revise document based on comments
- 4x `exceptions` agenda not prepared
- 4x `actors` meeting participants
- 3x `exceptions` wafer information mismatch
- 3x `activities` Submit disposal request for completed sample
- 3x `inputs` target location
- 3x `outputs` transfer approval
- 3x `activities` Review experiment result and select improvement action
- 3x `outputs` updated improvement proposal

## Automation-opportunity targets

The stored scorer matches automation targets by activity ID, which the reconstruction generates independently, so that legacy category is near-saturated and uninformative. The row below instead matches the referenced activity name inside the produced automation section.

| Group | items | carried | lost | recovered | dropped | unsupported | missed | description_retention | answer_retention | unsupported_share_of_new_output |
|---|---|---|---|---|---|---|---|---|---|---|
| automation targets | 168 | 18 | 1 | 125 | 11 | 1 | 12 | 0.947 | 0.919 | 0.008 |

## Limits

Membership is lexical, so `unsupported` can include paraphrase of an answer and `recovered` does not establish that an item is placed correctly in the reconstructed process; only human reading of `items.csv` can settle either. Items already present in the initial description are identified lexically, because the dataset omission annotations are category-level. Counts pool one generation per pipeline and carry no repeated-sampling variance estimate.

