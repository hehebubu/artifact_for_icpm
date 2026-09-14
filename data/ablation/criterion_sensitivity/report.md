# Coverage Under Three Lexical Match Criteria

Every stored workflow is re-scored without new model calls. `document` reproduces the stored scorer, which accepts an item when its informative tokens occur anywhere in the serialized output, including in its JSON keys. `field` applies the same token test inside a single field value. `exact` requires the full normalized phrase inside a single field value.

Reported metric: mean coverage per arm.

## Legacy eight-category mean, including ID-matched automation targets

### runs/semiconductor_work

| Arm | document | field | exact |
|---|---|---|---|
| one_shot | 0.7251 | 0.4544 | 0.2229 |
| checklist | 0.7529 | 0.4967 | 0.2400 |
| update | 0.9250 | 0.8385 | 0.5613 |

Ranking is identical under all three criteria: document: update > checklist > one_shot; field: update > checklist > one_shot; exact: update > checklist > one_shot

Per-scenario win-tie-loss, update vs one_shot: document 8-0-0 (mean +0.1999); field 8-0-0 (mean +0.3841); exact 8-0-0 (mean +0.3384)

Per-scenario win-tie-loss, update vs checklist: document 8-0-0 (mean +0.1721); field 8-0-0 (mean +0.3418); exact 8-0-0 (mean +0.3213)

### generic_questions_v1/semiconductor_work

| Arm | document | field | exact |
|---|---|---|---|
| generic | 0.9076 | 0.7972 | 0.5789 |
| gapelicit | 0.8662 | 0.7379 | 0.5246 |

Ranking is identical under all three criteria: document: generic > gapelicit; field: generic > gapelicit; exact: generic > gapelicit

Per-scenario win-tie-loss, generic vs gapelicit: document 5-2-1 (mean +0.0414); field 6-1-1 (mean +0.0593); exact 5-0-3 (mean +0.0544)

### coordinated_questions_v1/semiconductor_work

| Arm | document | field | exact |
|---|---|---|---|
| coordinated | 0.8885 | 0.7764 | 0.5894 |

Ranking is identical under all three criteria: document: coordinated; field: coordinated; exact: coordinated

### domain_taxonomy_v1/childcare

| Arm | document | field | exact |
|---|---|---|---|
| generic | 0.8822 | 0.7572 | 0.4564 |
| common | 0.8770 | 0.7363 | 0.4375 |
| domain | 0.9141 | 0.7871 | 0.4844 |

Ranking is identical under all three criteria: document: domain > generic > common; field: domain > generic > common; exact: domain > generic > common

Per-scenario win-tie-loss, domain vs generic: document 4-1-3 (mean +0.0319); field 5-0-3 (mean +0.0299); exact 4-1-3 (mean +0.0280)

Per-scenario win-tie-loss, domain vs common: document 5-0-3 (mean +0.0371); field 5-0-3 (mean +0.0508); exact 7-1-0 (mean +0.0469)

### domain_taxonomy_v1/semiconductor_work

| Arm | document | field | exact |
|---|---|---|---|
| domain | 0.8617 | 0.7571 | 0.5481 |

Ranking is identical under all three criteria: document: domain; field: domain; exact: domain

### matched_pilot/semiconductor_work

| Arm | document | field | exact |
|---|---|---|---|
| generic | 0.9076 | 0.7972 | 0.5789 |
| gapelicit | 0.8662 | 0.7379 | 0.5246 |
| coordinated | 0.8885 | 0.7764 | 0.5894 |

Ranking changes: document: generic > coordinated > gapelicit; field: generic > coordinated > gapelicit; exact: coordinated > generic > gapelicit

Per-scenario win-tie-loss, generic vs gapelicit: document 5-2-1 (mean +0.0414); field 6-1-1 (mean +0.0593); exact 5-0-3 (mean +0.0544)

Per-scenario win-tie-loss, generic vs coordinated: document 6-1-1 (mean +0.0192); field 6-0-2 (mean +0.0208); exact 3-1-4 (mean -0.0104)

## Seven process categories

### runs/semiconductor_work

| Arm | document | field | exact |
|---|---|---|---|
| one_shot | 0.6858 | 0.3764 | 0.1119 |
| checklist | 0.7176 | 0.4248 | 0.1314 |
| update | 0.9143 | 0.8154 | 0.4986 |

Ranking is identical under all three criteria: document: update > checklist > one_shot; field: update > checklist > one_shot; exact: update > checklist > one_shot

Per-scenario win-tie-loss, update vs one_shot: document 8-0-0 (mean +0.2284); field 8-0-0 (mean +0.4390); exact 8-0-0 (mean +0.3867)

Per-scenario win-tie-loss, update vs checklist: document 8-0-0 (mean +0.1967); field 8-0-0 (mean +0.3906); exact 8-0-0 (mean +0.3672)

### generic_questions_v1/semiconductor_work

| Arm | document | field | exact |
|---|---|---|---|
| generic | 0.9004 | 0.7742 | 0.5247 |
| gapelicit | 0.8531 | 0.7064 | 0.4626 |

Ranking is identical under all three criteria: document: generic > gapelicit; field: generic > gapelicit; exact: generic > gapelicit

Per-scenario win-tie-loss, generic vs gapelicit: document 5-2-1 (mean +0.0473); field 6-1-1 (mean +0.0678); exact 5-0-3 (mean +0.0621)

### coordinated_questions_v1/semiconductor_work

| Arm | document | field | exact |
|---|---|---|---|
| coordinated | 0.8845 | 0.7564 | 0.5426 |

Ranking is identical under all three criteria: document: coordinated; field: coordinated; exact: coordinated

### domain_taxonomy_v1/childcare

| Arm | document | field | exact |
|---|---|---|---|
| generic | 0.8772 | 0.7344 | 0.3906 |
| common | 0.8594 | 0.6987 | 0.3571 |
| domain | 0.9018 | 0.7567 | 0.4107 |

Ranking is identical under all three criteria: document: domain > generic > common; field: domain > generic > common; exact: domain > generic > common

Per-scenario win-tie-loss, domain vs generic: document 4-1-3 (mean +0.0246); field 5-0-3 (mean +0.0223); exact 4-1-3 (mean +0.0201)

Per-scenario win-tie-loss, domain vs common: document 5-0-3 (mean +0.0424); field 5-0-3 (mean +0.0580); exact 7-1-0 (mean +0.0536)

### domain_taxonomy_v1/semiconductor_work

| Arm | document | field | exact |
|---|---|---|---|
| domain | 0.8479 | 0.7284 | 0.4895 |

Ranking is identical under all three criteria: document: domain; field: domain; exact: domain

### matched_pilot/semiconductor_work

| Arm | document | field | exact |
|---|---|---|---|
| generic | 0.9004 | 0.7742 | 0.5247 |
| gapelicit | 0.8531 | 0.7064 | 0.4626 |
| coordinated | 0.8845 | 0.7564 | 0.5426 |

Ranking changes: document: generic > coordinated > gapelicit; field: generic > coordinated > gapelicit; exact: coordinated > generic > gapelicit

Per-scenario win-tie-loss, generic vs gapelicit: document 5-2-1 (mean +0.0473); field 6-1-1 (mean +0.0678); exact 5-0-3 (mean +0.0621)

Per-scenario win-tie-loss, generic vs coordinated: document 5-1-2 (mean +0.0159); field 5-0-3 (mean +0.0178); exact 2-1-5 (mean -0.0179)

