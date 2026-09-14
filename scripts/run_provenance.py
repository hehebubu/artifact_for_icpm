#!/usr/bin/env python3
"""Item-level provenance over cached pipeline logs; no API calls, standard library only."""
import argparse
import collections
import hashlib
from pathlib import Path

import run_question_ablation as ab
import score_runs as sr

ROOT = ab.ROOT
PROTOCOL = "provenance-v1"
STAGES = ("questions", "oracle_answers", "update")
FIELDS = ("desc", "question", "answer", "output", "gaps")
PROCESS_CATEGORIES = [c for c in sr.CATEGORIES if c != "automation_opportunities"]
LABELS = ("carried", "lost", "recovered", "dropped", "unsupported", "missed")
RATIOS = ("description_retention", "answer_retention", "unsupported_share_of_new_output")
CORPORA = (
    {"name": "generic_questions_v1", "arms": ("generic", "gapelicit"),
     "layout": "runs/r01/{scenario}/{arm}", "domain": "semiconductor_work"},
    {"name": "coordinated_questions_v1", "arms": ("coordinated",),
     "layout": "runs/{scenario}", "domain": "semiconductor_work"},
    {"name": "domain_taxonomy_v1", "arms": ("generic", "common", "domain"),
     "layout": "runs/{domain}/{scenario}/{arm}", "domain": None},
)
DATASETS = {"semiconductor_work": "data/scenarios.json", "childcare": "data/scenarios_childcare.json"}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def payload(record):
    if record["response"].get("stop_reason") != "end_turn":
        raise ValueError("Incomplete response")
    return ab.parse_response("\n".join(b.get("text", "") for b in record["response"]["content"] if b.get("type") == "text"))


def resolve(directory):
    paths = {stage: directory / f"{stage}.json" for stage in STAGES}
    if all(path.exists() for path in paths.values()):
        return paths, False
    evaluation = directory / "evaluation.json"
    if evaluation.exists():
        cached = {Path(source).stem: ROOT / source for source in ab.read(evaluation).get("source_files") or []}
        if set(cached) == set(STAGES) and all(path.exists() for path in cached.values()):
            return cached, True
    return None, False


def discover(root):
    for corpus in CORPORA:
        base = root / corpus["name"]
        if not base.exists():
            continue
        domains = [corpus["domain"]] if corpus["domain"] else sorted(p.name for p in (base / "runs").iterdir() if p.is_dir())
        for domain in domains:
            for arm in corpus["arms"]:
                for directory in sorted(base.glob(corpus["layout"].format(domain=domain, scenario="*", arm=arm))):
                    paths, cached = resolve(directory) if directory.is_dir() else (None, False)
                    if paths:
                        scenario_id = directory.parent.name if "{arm}" in corpus["layout"] else directory.name
                        yield {"corpus": corpus["name"], "domain": domain, "scenario_id": scenario_id,
                               "arm": arm, "cached": cached, "paths": paths}


def reference_items(scenario):
    reference = scenario["reference_workflow"]
    return {
        "activities": [item["name"] for item in reference.get("activities", [])],
        "actors": reference.get("actors", []),
        "systems": reference.get("systems", []),
        "inputs": reference.get("inputs", []),
        "outputs": reference.get("outputs", []),
        "decisions": [item["condition"] for item in reference.get("decisions", [])],
        "exceptions": reference.get("exceptions", []),
    }


def automation_items(scenario):
    reference = scenario["reference_workflow"]
    names = {item["id"]: item["name"] for item in reference.get("activities", [])}
    return [(item["target"], names.get(item["target"], item["target"]))
            for item in reference.get("automation_opportunities", [])]


def leaves(value):
    if isinstance(value, dict):
        return [leaf for child in value.values() for leaf in leaves(child)]
    if isinstance(value, list):
        return [leaf for child in value for leaf in leaves(child)]
    return [sr.normalize(value)] if isinstance(value, str) and value.strip() else []


def source(value):
    # The stored scorer tokenizes the serialized document, including its JSON keys; leaves keep field boundaries.
    return {"text": sr.normalize(ab.dump(value)), "leaves": leaves(value)}


def texts(scenario, questions, answers, workflow):
    structured = {key: workflow.get(key) for key in ("workflow", "automation_opportunities")}
    return {
        "desc": source(scenario["initial_description"]),
        "question": source(questions.get("clarification_questions", [])),
        "answer": source([item.get("answer", "") for item in answers.get("answers", [])]),
        "output": source(structured),
        "gaps": source(workflow.get("remaining_gaps", [])),
        "automation": source(workflow.get("automation_opportunities", [])),
    }


def match_level(field, item):
    # exact: the whole phrase occurs inside one field value; field: the token test passes within one value;
    # scatter: only the stored scorer's document-wide token test passes.
    phrase = sr.normalize(item)
    if phrase and any(phrase in leaf for leaf in field["leaves"]):
        return "exact"
    if any(sr.soft_contains(leaf, item) for leaf in field["leaves"]):
        return "field"
    return "scatter" if sr.soft_contains(field["text"], item) else "none"


def label_for(in_desc, in_answer, in_output):
    if in_desc:
        return "carried" if in_output else "lost"
    if in_answer:
        return "recovered" if in_output else "dropped"
    return "unsupported" if in_output else "missed"


def item_row(identity, category, item, field, output_key="output"):
    levels = {key: match_level(field[output_key if key == "output" else key], item) for key in FIELDS}
    keys = ("desc", "answer", "output")
    return {**identity, "category": category, "item": item,
            **{f"{key}_match": levels[key] for key in FIELDS},
            **{f"label{suffix}": label_for(*(levels[key] in accepted for key in keys))
               for suffix, accepted in (("", ("scatter", "field", "exact")), ("_field", ("field", "exact")), ("_exact", ("exact",)))}}


def rows_for(run, scenario):
    records = {stage: ab.read(path) for stage, path in run["paths"].items()}
    questions, answers, workflow = (payload(records[stage]) for stage in STAGES)
    field = texts(scenario, questions, answers, workflow)
    identity = {key: run[key] for key in ("corpus", "domain", "scenario_id", "arm")}
    identity["cached"] = "yes" if run["cached"] else "no"
    rows = [item_row(identity, category, item, field)
            for category, items in reference_items(scenario).items() for item in items]
    rows += [item_row(identity, "automation_targets", f"{target}: {name}", field, output_key="automation")
             for target, name in automation_items(scenario)]
    return rows


def ratio(numerator, denominator):
    return round(numerator / denominator, 4) if denominator else None


def tally(rows, key="label"):
    counts = collections.Counter(row[key] for row in rows)
    covered = [row for row in rows if row["output_match"] != "none"]
    return {"items": len(rows), **{label: counts[label] for label in LABELS},
            "description_retention": ratio(counts["carried"], counts["carried"] + counts["lost"]),
            "answer_retention": ratio(counts["recovered"], counts["recovered"] + counts["dropped"]),
            "unsupported_share_of_new_output": ratio(counts["unsupported"], counts["recovered"] + counts["unsupported"]),
            "dropped_declared_as_gap": sum(1 for row in rows if row[key] == "dropped" and row["gaps_match"] != "none"),
            "within_field_share_of_covered": ratio(sum(1 for row in covered if row["output_match"] != "scatter"), len(covered)),
            "exact_share_of_covered": ratio(sum(1 for row in covered if row["output_match"] == "exact"), len(covered))}


def robust_core(rows):
    # Findings that survive both the stored document criterion and the stricter within-field criterion.
    both = lambda label: [row for row in rows if row["label"] == label and row["label_field"] == label]
    return {"dropped_under_both_criteria": len(both("dropped")),
            "dropped_with_no_output_trace": sum(1 for row in rows if row["label_field"] == "dropped" and row["output_match"] == "none"),
            "dropped_only_scattered_output_evidence": sum(1 for row in rows if row["label_field"] == "dropped" and row["output_match"] == "scatter"),
            "unsupported_under_both_criteria": len(both("unsupported")),
            "missed_under_both_criteria": len(both("missed")),
            "recovered_under_both_criteria": len(both("recovered"))}


def group(rows, key):
    grouped = collections.OrderedDict()
    for row in rows:
        grouped.setdefault(key(row), []).append(row)
    return grouped


def summarize(rows):
    process = [row for row in rows if row["category"] != "automation_targets"]
    # Cached arms replay logs owned by another corpus; pool only distinct pipelines.
    distinct = [row for row in process if row["cached"] == "no"]
    return {
        "protocol": PROTOCOL,
        "stored_arms": len({(r["corpus"], r["domain"], r["scenario_id"], r["arm"]) for r in rows}),
        "distinct_pipelines": len({(r["corpus"], r["domain"], r["scenario_id"], r["arm"]) for r in rows if r["cached"] == "no"}),
        "overall": tally(distinct),
        "robust_core": robust_core(distinct),
        "overall_within_field_criterion": tally(distinct, "label_field"),
        "overall_exact_match_criterion": tally(distinct, "label_exact"),
        "by_corpus_arm": {f"{k[0]}/{k[1]}": tally(v) for k, v in group(process, lambda r: (r["corpus"], r["arm"])).items()},
        "by_corpus_arm_within_field_criterion": {f"{k[0]}/{k[1]}": tally(v, "label_field")
                                                 for k, v in group(process, lambda r: (r["corpus"], r["arm"])).items()},
        "by_corpus_arm_exact_match_criterion": {f"{k[0]}/{k[1]}": tally(v, "label_exact")
                                                for k, v in group(process, lambda r: (r["corpus"], r["arm"])).items()},
        "by_domain": {k: tally(v) for k, v in group(distinct, lambda r: r["domain"]).items()},
        "by_category": {k: tally(v) for k, v in group(distinct, lambda r: r["category"]).items()},
        "by_category_within_field_criterion": {k: tally(v, "label_field") for k, v in group(distinct, lambda r: r["category"]).items()},
        "by_category_exact_match_criterion": {k: tally(v, "label_exact") for k, v in group(distinct, lambda r: r["category"]).items()},
        "by_scenario": {f"{k[0]}/{k[1]}": tally(v) for k, v in group(distinct, lambda r: (r["domain"], r["scenario_id"])).items()},
        "automation_targets_activity_name_match": tally([row for row in rows
                                                         if row["category"] == "automation_targets" and row["cached"] == "no"]),
    }


def table(mapping, keys, header="Group"):
    lines = ["", f"| {header} | " + " | ".join(keys) + " |", "|---" * (len(keys) + 1) + "|"]
    for name, stats in mapping.items():
        values = ["--" if stats[k] is None else (f"{stats[k]:.3f}" if isinstance(stats[k], float) else str(stats[k])) for k in keys]
        lines.append(f"| {name} | " + " | ".join(values) + " |")
    return lines


def frequent(rows, predicate, limit=12):
    counts = collections.Counter((row["category"], row["item"]) for row in rows if predicate(row))
    return [f"- {count}x `{category}` {item}" for (category, item), count in counts.most_common(limit)] or ["- none"]


def report(summary, rows, out):
    counts, strict = summary["overall"], summary["overall_exact_match_criterion"]
    keys = ["items", *LABELS, *RATIOS]
    lines = ["# Item-Level Provenance of Reference Facts", "",
             f"Cached-log analysis of {summary['stored_arms']} stored arms "
             f"({summary['distinct_pipelines']} distinct pipelines; cached arms replay logs owned by another corpus "
             "and are pooled only in the per-arm tables). No new model calls.", "",
             "Every reference item is traced through the initial description, the clarification questions, the "
             "simulated expert answers, and the reconstructed workflow. Labels: `carried`/`lost` for items already "
             "stated in the initial description; `recovered`/`dropped` for newly answered items that the "
             "reconstruction keeps or loses; `unsupported` for items present in the output but in neither the "
             "description nor the answers; `missed` for items neither answered nor produced.", "",
             f"Process-category items: {counts['items']}. Answer retention {counts['answer_retention']}, "
             f"description retention {counts['description_retention']}, unsupported share of newly produced items "
             f"{counts['unsupported_share_of_new_output']}.", "",
             "## By corpus and arm"] + table(summary["by_corpus_arm"], keys)
    lines += ["", "## By domain"] + table(summary["by_domain"], keys)
    lines += ["", "## By information category"] + table(summary["by_category"], keys)
    lines += ["", "## By scenario"] + table(summary["by_scenario"], keys)

    process = [row for row in rows if row["category"] != "automation_targets" and row["cached"] == "no"]
    lines += ["", "## Most frequently dropped answered items", ""] + frequent(process, lambda r: r["label"] == "dropped")
    lines += ["", "## Most frequent unsupported output items", ""] + frequent(process, lambda r: r["label"] == "unsupported")

    field = summary["overall_within_field_criterion"]
    lines += ["", "## Sensitivity to the lexical match criterion", "",
              "The stored scorer tokenizes the whole serialized output, including its JSON keys, and counts an item "
              "as covered when its informative tokens each occur anywhere in that document, so tokens scattered "
              "across unrelated fields satisfy it. Two stricter criteria repeat the same accounting: `within-field` "
              "requires the same token test to pass inside a single field value, and `exact` requires the full "
              "normalized phrase inside a single field value. The within-field criterion is the one worth adopting; "
              "the exact criterion is a lower bound that any rewording defeats.", "",
              f"Of the items the stored criterion counts as covered, {counts['within_field_share_of_covered']} survive "
              f"the within-field test and {counts['exact_share_of_covered']} match exactly. Recovered items fall from "
              f"{counts['recovered']} to {field['recovered']} to {strict['recovered']}, and missed items rise from "
              f"{counts['missed']} to {field['missed']} to {strict['missed']}, across the three criteria.", ""]
    lines += ["### Overall"] + table({"stored document criterion": counts, "within-field criterion": field,
                                      "exact phrase criterion": strict}, keys, "Criterion")
    core = summary["robust_core"]
    lines += ["", "### Findings that hold under both the stored and the within-field criterion", "",
              f"- recovered: {core['recovered_under_both_criteria']}",
              f"- dropped: {core['dropped_under_both_criteria']}, of which "
              f"{core['dropped_with_no_output_trace']} leave no trace of the item anywhere in the output",
              f"- unsupported: {core['unsupported_under_both_criteria']}",
              f"- missed: {core['missed_under_both_criteria']}", "",
              f"A further {core['dropped_only_scattered_output_evidence']} answered items are counted as dropped only "
              "by the within-field criterion: their words do occur in the output but never inside one field value, "
              "which is what a reworded activity name looks like as well as what a real omission looks like. "
              "That gap is the part only human reading can settle."]
    lines += ["", "### By arm, within-field criterion"] + table(summary["by_corpus_arm_within_field_criterion"], keys)
    lines += ["", "### By arm, exact phrase criterion"] + table(summary["by_corpus_arm_exact_match_criterion"], keys)
    lines += ["", "### By category, within-field criterion"] + table(summary["by_category_within_field_criterion"], keys)
    lines += ["", "### By category, exact phrase criterion"] + table(summary["by_category_exact_match_criterion"], keys)
    lines += ["", "### Items counted as covered only by tokens scattered across fields", ""]
    lines += frequent(process, lambda r: r["output_match"] == "scatter")

    lines += ["", "## Automation-opportunity targets", "",
              "The stored scorer matches automation targets by activity ID, which the reconstruction generates "
              "independently, so that legacy category is near-saturated and uninformative. The row below instead "
              "matches the referenced activity name inside the produced automation section."]
    lines += table(summary["automation_targets_activity_name_match"] and
                   {"automation targets": summary["automation_targets_activity_name_match"]}, keys)

    lines += ["", "## Limits", "",
              "Membership is lexical, so `unsupported` can include paraphrase of an answer and `recovered` does not "
              "establish that an item is placed correctly in the reconstructed process; only human reading of "
              "`items.csv` can settle either. Items already present in the initial description are identified "
              "lexically, because the dataset omission annotations are category-level. Counts pool one generation "
              "per pipeline and carry no repeated-sampling variance estimate.", ""]
    (out / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ablation", type=Path, default=ROOT / "data/ablation")
    parser.add_argument("--out", type=Path, default=ROOT / "data/ablation/provenance_v1")
    args = parser.parse_args()

    scenarios = {domain: ab.load_scenarios(ROOT / path) for domain, path in DATASETS.items()}
    rows, skipped = [], []
    for run in discover(args.ablation):
        identity = {key: run[key] for key in ("corpus", "domain", "scenario_id", "arm")}
        scenario = scenarios.get(run["domain"], {}).get(run["scenario_id"])
        if not scenario:
            skipped.append({**identity, "error": "unknown scenario"})
            continue
        try:
            rows += rows_for(run, scenario)
        except (ValueError, KeyError, TypeError) as exc:
            skipped.append({**identity, "error": str(exc)})
    if not rows:
        parser.error("No cached pipeline runs found")

    args.out.mkdir(parents=True, exist_ok=True)
    sr.write_scores(args.out / "items.csv", rows)
    summary = summarize(rows)
    summary["skipped"] = skipped
    ab.save(args.out / "summary.json", summary)
    report(summary, rows, args.out)
    ab.save(args.out / "manifest.json", {"protocol": PROTOCOL, "stored_arms": summary["stored_arms"],
            "distinct_pipelines": summary["distinct_pipelines"], "skipped": skipped,
            "input_hashes": {path: sha(ROOT / path) for path in
                             [*DATASETS.values(), "scripts/score_runs.py", "scripts/run_provenance.py"]}})
    print(ab.dump({"stored": summary["overall"], "within_field": summary["overall_within_field_criterion"],
                   "exact": summary["overall_exact_match_criterion"]}))
    print(f"Wrote {len(rows)} item rows from {summary['distinct_pipelines']} distinct pipelines to {args.out}")


if __name__ == "__main__":
    main()
