# Artifact for Gap-Driven Process Elicitation with LLMs

This repository contains the anonymized research artifact for a paper submitted
to ICPM 2027. The artifact supports a small benchmark study on LLM-assisted
process elicitation from underspecified workflow descriptions.

The repository intentionally contains only synthetic workflow scenarios,
prototype code, prompts embedded in the prototype, saved model outputs, and the
scoring script used to generate the reported aggregate results. It does not
contain confidential company data, internal system names, product identifiers,
equipment identifiers, personal information, API keys, or author-identifying
paper files.

## Contents

- `data/scenarios.json`: eight synthetic workflow scenarios. Each scenario
  contains an underspecified initial description, a reference workflow, and the
  information intentionally omitted from the initial description.
- `data/runs/`: saved LLM outputs for the experimental conditions.
- `data/evaluation/`: generated per-run and aggregate coverage scores.
- `scripts/score_runs.py`: scoring script for reference-coverage metrics.
- `tables/`, `figures/`: generated LaTeX tables and TikZ figure snippets from
  the scoring script.
- `public/`, `server.js`: local web prototype for running one-shot, checklist,
  and active clarification conditions.
- `.env.example`: example environment file for local API configuration.

### Question-policy ablation (RQ2)

- `data/scenarios_childcare.json`: eight childcare coordination scenarios in the
  same schema, used as the second domain.
- `data/domain_taxonomies.json`: the common and domain-contextualized gap
  taxonomies compared in the ablation.
- `data/ablation/generic_questions_v1/`, `coordinated_questions_v1/`,
  `domain_taxonomy_v1/`: run logs, frozen manifests with input hashes, scores
  and reports for the question-policy conditions.
- `scripts/run_question_ablation.py`, `run_domain_ablation.py`,
  `run_coordinated_questions.py`: the corresponding experiment runners.

### Provenance and answer-quality analysis (RQ3)

- `data/ablation/provenance_v1/`: item-level provenance of every reference item
  across all stored pipelines. `items.csv` records, for each item, whether it
  appears in the initial description, the questions, the answers, the output and
  the declared gaps, under three match criteria, together with its provenance
  label.
- `data/ablation/criterion_sensitivity/`: every stored workflow re-scored under
  the document, within-field and exact criteria.
- `data/ablation/answer_ladder_v1/`: 200 pipelines over five answer-quality
  levels with five repeats, including the bootstrap comparison to the
  full-answer anchor.
- `scripts/run_provenance.py`, `rescore_criteria.py`, `run_answer_ladder.py`,
  `make_new_tables.py`: the analysis scripts. The provenance and
  criterion-sensitivity analyses re-read stored logs and issue no API calls, so
  they reproduce offline:

```sh
python3 scripts/run_provenance.py
python3 scripts/rescore_criteria.py
```

- `scripts/test_*.py`: unit tests for the runners and the analysis scripts.

## Experimental Conditions

The prototype supports three workflow-producing conditions:

1. `one_shot`: generate a workflow directly from the initial description.
2. `checklist`: generate a workflow using a fixed completeness checklist.
3. `update`: ask clarification questions, collect answers, and revise the
   workflow representation.

The intermediate `questions` and `oracle_answers` logs are included to document
the active clarification process.

## Reproducing the Scores

Run the scoring script from the repository root:

```sh
python3 scripts/score_runs.py
```

The script writes:

- `data/evaluation/scores.csv`
- `data/evaluation/summary.json`

By default, the script scores only workflow-producing stages:
`one_shot`, `checklist`, and `update`.

To include intermediate non-workflow logs for inspection:

```sh
python3 scripts/score_runs.py --include-non-workflow
```

## Running the Prototype

Create a local `.env` file:

```sh
cp .env.example .env
```

Then set a local Anthropic API key and model:

```sh
ANTHROPIC_API_KEY=sk-ant-REPLACE_WITH_YOUR_KEY
ANTHROPIC_MODEL=claude-sonnet-4-6
PORT=8787
```

Install dependencies if needed and start the local server:

```sh
npm install
npm start
```

Open `http://localhost:8787` in a browser.

## Data and Anonymization Notes

The scenarios are synthetic and written in generic terms. They are inspired by
common operational knowledge-work patterns such as verification reporting,
sample logistics, document review, issue triage, meeting follow-up, and meeting
room reservation. They should not be interpreted as descriptions of any
specific organization, product, equipment, or internal procedure.

Before making this repository public, check that:

- `.env` is not present.
- no API key appears in any file.
- no author names, affiliations, or email addresses appear in any file.
- no private notes or manuscript files are included.
