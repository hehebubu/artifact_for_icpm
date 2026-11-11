#!/usr/bin/env python3
"""Output-side provenance: where does each element the reconstruction states come from?

run_provenance.py walks the reference and asks, of each reference item, whether the
answers and the output contain it. That direction cannot see an element the output
states outside the reference. This script walks the other way: it enumerates the
elements the reconstruction states and tests each against the reference, then against
the description and the answers.

No API calls; it re-reads the stored logs, like run_provenance.py, so it reproduces
offline.

Unit of analysis
----------------
One row is a (run, category, distinct normalized string). Within a run and a category
the same string is counted once, however many activities carry it; across categories
and across runs it is counted separately. The forward direction's unit is a reference
item-run pair, so the two totals are not comparable item for item.

Extraction rule
---------------
The reconstruction is a JSON workflow. Activities carry a name, an actor, a system and
lists of inputs and outputs; decisions carry a condition; exceptions carry a
description. The seven categories are read off exactly those fields, so that they match
the seven categories the reference is scored on. Nothing is read from
automation_opportunities or remaining_gaps.

Classification, in order (first match wins)
-------------------------------------------
in_reference       the string matches the serialized reference workflow
grounded           not in the reference, but matches the description or the answers
abstention         a placeholder standing in for a value the model declined to give
restated_artifact  an inputs/outputs string that the same run also states in the
                   complementary role, i.e. the output consumes something it produced
untraceable        none of the above: stated, outside the reference, and with no lexical
                   trace in anything the run was given

Each row is classified three times, once per membership criterion (document,
within-field, exact), with the same accept sets run_provenance.py uses.
"""
import argparse
import collections
import csv
import hashlib
from pathlib import Path

import run_provenance as rp
import run_question_ablation as ab

ROOT = rp.ROOT
PROTOCOL = "output-side-v1"
CATEGORIES = ("activities", "actors", "systems", "inputs", "outputs", "decisions", "exceptions")
CRITERIA = {"document": ("scatter", "field", "exact"),
            "field": ("field", "exact"),
            "exact": ("exact",)}
LABELS = ("in_reference", "grounded", "abstention", "restated_artifact", "untraceable")
# Placeholders the model uses instead of naming a value. Derived from the data: every
# short untraceable string was listed, and these are the ones that name no element of
# the process. A string counts as an abstention when its normalized form begins with one
# of them, because the model often hedges rather than leaving the field bare -- "unknown
# (likely a calendar tool)" declines to name a system exactly as "unknown" does. The list
# is closed and the rule is a prefix test, so every decision can be checked by hand.
ABSTENTIONS = (
    "unknown", "unspecified", "none specified", "not specified", "not applicable",
    "none", "n/a", "na", "tbd", "undefined", "unclear", "not stated",
)
STRUCTURAL = ("activities", "decisions", "exceptions")


def output_items(workflow):
    """The elements the reconstruction states, by category, as distinct strings."""
    flow = workflow.get("workflow", {}) or {}
    activities = [a for a in flow.get("activities", []) if isinstance(a, dict)]
    raw = {
        "activities": [a.get("name", "") for a in activities],
        "actors": [a.get("actor", "") for a in activities],
        "systems": [a.get("system", "") for a in activities],
        "inputs": [i for a in activities for i in (a.get("inputs") or []) if isinstance(i, str)],
        "outputs": [o for a in activities for o in (a.get("outputs") or []) if isinstance(o, str)],
        "decisions": [d.get("condition", "") for d in flow.get("decisions", []) if isinstance(d, dict)],
        "exceptions": [(e.get("description", "") if isinstance(e, dict) else str(e))
                       for e in flow.get("exceptions", [])],
    }
    items = {}
    for category in CATEGORIES:
        seen, kept = set(), []
        for value in raw[category]:
            if not isinstance(value, str) or not value.strip():
                continue
            key = rp.sr.normalize(value)
            if key and key not in seen:
                seen.add(key)
                kept.append(value.strip())
        items[category] = kept
    return items


def label_for(category, item, levels, accepted, restated):
    if levels["reference"] in accepted:
        return "in_reference"
    if levels["answer"] in accepted or levels["desc"] in accepted:
        return "grounded"
    if rp.sr.normalize(item).startswith(ABSTENTIONS):
        return "abstention"
    if category in ("inputs", "outputs") and rp.sr.normalize(item) in restated:
        return "restated_artifact"
    return "untraceable"


def rows_for(run, scenario):
    records = {stage: ab.read(path) for stage, path in run["paths"].items()}
    questions, answers, workflow = (rp.payload(records[stage]) for stage in rp.STAGES)
    field = rp.texts(scenario, questions, answers, workflow)
    reference = rp.source(rp.reference_items(scenario))
    items = output_items(workflow)
    restated = ({rp.sr.normalize(v) for v in items["inputs"]}
                & {rp.sr.normalize(v) for v in items["outputs"]})
    identity = {key: run[key] for key in ("corpus", "domain", "scenario_id", "arm")}
    rows = []
    for category in CATEGORIES:
        for item in items[category]:
            levels = {"reference": rp.match_level(reference, item),
                      "desc": rp.match_level(field["desc"], item),
                      "answer": rp.match_level(field["answer"], item)}
            row = {**identity, "category": category, "item": item,
                   **{f"{key}_match": value for key, value in levels.items()}}
            for name, accepted in CRITERIA.items():
                row[f"label_{name}"] = label_for(category, item, levels, accepted, restated)
            rows.append(row)
    return rows


def summarize(rows, pipelines):
    summary = {"protocol": PROTOCOL, "distinct_pipelines": pipelines, "items": len(rows)}
    for name in CRITERIA:
        key = f"label_{name}"
        counts = collections.Counter(row[key] for row in rows)
        block = {label: counts.get(label, 0) for label in LABELS}
        block["untraceable_per_run"] = round(block["untraceable"] / pipelines, 2)
        block["untraceable_share"] = round(block["untraceable"] / len(rows), 4)
        block["untraceable_structural"] = sum(
            1 for row in rows if row[key] == "untraceable" and row["category"] in STRUCTURAL)
        block["by_category"] = {
            category: collections.Counter(
                row[key] for row in rows if row["category"] == category)
            for category in CATEGORIES}
        block["by_category"] = {c: dict(v) for c, v in block["by_category"].items()}
        summary[name] = block
    def placeholder(value):
        normalized = rp.sr.normalize(value)
        return next(p for p in ABSTENTIONS if normalized.startswith(p))
    summary["abstentions_observed"] = dict(collections.Counter(
        placeholder(row["item"]) for row in rows if row["label_field"] == "abstention"))
    summary["exceptions_declaring_an_undefined_path"] = sum(
        1 for row in rows if row["label_field"] == "untraceable" and row["category"] == "exceptions"
        and any(k in row["item"].lower()
                for k in ("not defined", "no formal", "undefined", "not specified", "not covered")))
    return summary


def report(summary, rows, out):
    lines = [f"# Output-side provenance ({PROTOCOL})", "",
             f"{summary['items']} output item-run pairs over {summary['distinct_pipelines']} "
             "distinct pipelines. One row is a distinct normalized string within a run and a "
             "category. The forward analysis counts reference item-run pairs, so the two totals "
             "are not comparable item for item.", "",
             "| Criterion | In reference | Grounded outside | Abstention | Restated artifact | "
             "Untraceable | Per run |", "|---|---:|---:|---:|---:|---:|---:|"]
    for name in ("document", "field", "exact"):
        b = summary[name]
        lines.append(f"| {name} | {b['in_reference']} | {b['grounded']} | {b['abstention']} | "
                     f"{b['restated_artifact']} | **{b['untraceable']}** | {b['untraceable_per_run']} |")
    b = summary["field"]
    lines += ["", "## Untraceable elements by category (within-field)", "",
              "| Category | Untraceable |", "|---|---:|"]
    for category in CATEGORIES:
        lines.append(f"| {category} | {b['by_category'][category].get('untraceable', 0)} |")
    lines += ["", f"Of those, {b['untraceable_structural']} fall in the structural categories "
              f"({', '.join(STRUCTURAL)}). "
              f"{summary['exceptions_declaring_an_undefined_path']} of the untraceable exceptions "
              "state in so many words that the process defines no path for the case they raise, "
              "which is the model reporting a gap rather than inventing a step.", "",
              "## Placeholders counted as abstentions", "",
              ", ".join(f"`{k}` ({v})" for k, v in
                        sorted(summary["abstentions_observed"].items(), key=lambda kv: -kv[1])) or "none",
              "", "## Sample of untraceable elements (within-field)", ""]
    sample = [r for r in rows if r["label_field"] == "untraceable"][:20]
    lines += [f"- [{r['category']}] {r['item']}" for r in sample]
    lines += ["", "Lexical absence is not semantic absence: these are elements no lexical test "
              "traces to the reference, the description or the answers, not confirmed "
              "fabrications. A human check of a sample is the only way to size that gap."]
    (out / "report.md").write_text("\n".join(lines) + "\n", encoding="utf8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ablation", type=Path, default=ROOT / "data/ablation")
    parser.add_argument("--out", type=Path, default=ROOT / "data/ablation/output_side_v1")
    args = parser.parse_args()

    scenarios = {domain: ab.load_scenarios(ROOT / path) for domain, path in rp.DATASETS.items()}
    rows, skipped, seen = [], [], set()
    for run in rp.discover(args.ablation):
        identity = {key: run[key] for key in ("corpus", "domain", "scenario_id", "arm")}
        scenario = scenarios.get(run["domain"], {}).get(run["scenario_id"])
        if not scenario:
            skipped.append({**identity, "error": "unknown scenario"})
            continue
        fingerprint = tuple(str(run["paths"][stage]) for stage in rp.STAGES)
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        try:
            rows += rows_for(run, scenario)
        except (ValueError, KeyError, TypeError) as exc:
            skipped.append({**identity, "error": str(exc)})
    if not rows:
        parser.error("No cached pipeline runs found")

    args.out.mkdir(parents=True, exist_ok=True)
    with open(args.out / "items.csv", "w", newline="", encoding="utf8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    summary = summarize(rows, len(seen))
    summary["skipped"] = skipped
    ab.save(args.out / "summary.json", summary)
    report(summary, rows, args.out)
    ab.save(args.out / "manifest.json", {
        "protocol": PROTOCOL, "distinct_pipelines": len(seen), "skipped": skipped,
        "input_hashes": {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
                         for path in [*rp.DATASETS.values(), "scripts/score_runs.py",
                                      "scripts/run_provenance.py", "scripts/run_output_side.py"]}})
    print(ab.dump({name: {k: v for k, v in summary[name].items() if k != "by_category"}
                   for name in CRITERIA}))


if __name__ == "__main__":
    main()
