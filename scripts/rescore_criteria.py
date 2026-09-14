#!/usr/bin/env python3
"""Re-score every stored workflow under three lexical match criteria; no API calls.

score_runs.py is left untouched so that frozen manifest hashes keep verifying.
"""
import argparse
import collections
import statistics
from pathlib import Path

import run_provenance as rp
import run_question_ablation as ab
import score_runs as sr

ROOT = ab.ROOT
CRITERIA = ("document", "field", "exact")
ACCEPTED = {"document": ("scatter", "field", "exact"), "field": ("field", "exact"), "exact": ("exact",)}
STAGE_ORDER = ("one_shot", "checklist", "update")


def reference_categories(scenario):
    items = rp.reference_items(scenario)
    # The legacy eighth category matches automation targets by activity ID, as the stored scorer does.
    items["automation_opportunities"] = [item["target"] for item in scenario["reference_workflow"].get("automation_opportunities", [])]
    return items


def coverage(scenario, result):
    field = rp.source(result)
    levels = {category: [rp.match_level(field, item) for item in items]
              for category, items in reference_categories(scenario).items()}
    scores = {}
    for criterion in CRITERIA:
        per_category = {category: (sum(level in ACCEPTED[criterion] for level in values) / len(values) if values else 0.0)
                        for category, values in levels.items()}
        scores[criterion] = {**per_category,
                             "legacy_overall": statistics.mean(per_category[c] for c in sr.CATEGORIES),
                             "process_overall": statistics.mean(per_category[c] for c in rp.PROCESS_CATEGORIES)}
    return scores


def legacy_rows(scenarios, runs):
    rows = []
    for path in sorted(runs.glob("*.json")):
        record = ab.read(path)
        scenario = scenarios.get(record.get("request", {}).get("scenario", {}).get("id"))
        stage = record.get("result", {}).get("stage") or record.get("request", {}).get("stage")
        if not scenario or stage not in STAGE_ORDER:
            continue
        parsed = record["result"].get("parsed")
        result = parsed if parsed is not None else record["result"].get("raw_text", "")
        rows.append({"corpus": "runs", "group": stage, "domain": "semiconductor_work",
                     "scenario_id": scenario["id"], "scores": coverage(scenario, result)})
    return rows


def ablation_rows(scenarios, ablation):
    rows = []
    for run in rp.discover(ablation):
        scenario = scenarios.get(run["domain"], {}).get(run["scenario_id"])
        if not scenario or run["cached"]:
            continue
        workflow = rp.payload(ab.read(run["paths"]["update"]))
        result = {key: workflow.get(key) for key in ("workflow", "automation_opportunities")}
        rows.append({"corpus": run["corpus"], "group": run["arm"], "domain": run["domain"],
                     "scenario_id": run["scenario_id"], "scores": coverage(scenario, result)})
    return rows


def matched_pilot(rows):
    # The coordinated pilot reuses the question-ablation scenarios, arms and settings; group them for a paired view.
    keep = {("generic_questions_v1", "generic"), ("generic_questions_v1", "gapelicit"),
            ("coordinated_questions_v1", "coordinated")}
    return [{**row, "corpus": "matched_pilot"} for row in rows if (row["corpus"], row["group"]) in keep]


def paired(rows, metric):
    grouped = collections.OrderedDict()
    for row in rows:
        grouped.setdefault((row["corpus"], row["domain"]), {}).setdefault(row["group"], {})[row["scenario_id"]] = row["scores"]
    outcome = {}
    for (corpus, domain), arms in grouped.items():
        if len(arms) < 2:
            continue
        leader = max(arms, key=lambda arm: statistics.mean(s[CRITERIA[0]][metric] for s in arms[arm].values()))
        records = {}
        for arm in arms:
            if arm == leader:
                continue
            shared = sorted(set(arms[leader]) & set(arms[arm]))
            for criterion in CRITERIA:
                differences = [arms[leader][sid][criterion][metric] - arms[arm][sid][criterion][metric] for sid in shared]
                records.setdefault(f"{leader} vs {arm}", {})[criterion] = {
                    "scenarios": len(shared), "wins": sum(d > 1e-9 for d in differences),
                    "ties": sum(abs(d) <= 1e-9 for d in differences), "losses": sum(d < -1e-9 for d in differences),
                    "mean_difference": round(statistics.mean(differences), 4) if differences else None}
        outcome[f"{corpus}/{domain}"] = records
    return outcome


def flatten(rows):
    flat = []
    for row in rows:
        for criterion in CRITERIA:
            flat.append({**{k: row[k] for k in ("corpus", "domain", "group", "scenario_id")}, "criterion": criterion,
                         **{k: round(v, 4) for k, v in row["scores"][criterion].items()}})
    return flat


def means(rows, metric):
    grouped = collections.OrderedDict()
    for row in rows:
        grouped.setdefault((row["corpus"], row["domain"]), {}).setdefault(row["group"], {})
    for row in rows:
        for criterion in CRITERIA:
            grouped[(row["corpus"], row["domain"])][row["group"]].setdefault(criterion, []).append(row["scores"][criterion][metric])
    return {f"{corpus}/{domain}": {group: {criterion: round(statistics.mean(values), 4) for criterion, values in criteria.items()}
                                   for group, criteria in groups.items()}
            for (corpus, domain), groups in grouped.items()}


def ordering(groups, criterion):
    return [name for name, _ in sorted(groups.items(), key=lambda item: -item[1][criterion])]


def report(summary, out, metric):
    lines = ["# Coverage Under Three Lexical Match Criteria", "",
             "Every stored workflow is re-scored without new model calls. `document` reproduces the stored scorer, "
             "which accepts an item when its informative tokens occur anywhere in the serialized output, including "
             "in its JSON keys. `field` applies the same token test inside a single field value. `exact` requires "
             "the full normalized phrase inside a single field value.", "",
             f"Reported metric: {metric}.", ""]
    for block, label in (("legacy_overall", "Legacy eight-category mean, including ID-matched automation targets"),
                         ("process_overall", "Seven process categories")):
        lines += [f"## {label}", ""]
        for name, groups in summary[block].items():
            lines += [f"### {name}", "", "| Arm | " + " | ".join(CRITERIA) + " |", "|---" * (len(CRITERIA) + 1) + "|"]
            for group, values in groups.items():
                lines.append(f"| {group} | " + " | ".join(f"{values[c]:.4f}" for c in CRITERIA) + " |")
            rankings = {criterion: ordering(groups, criterion) for criterion in CRITERIA}
            stable = len({tuple(order) for order in rankings.values()}) == 1
            lines += ["", ("Ranking is identical under all three criteria: " if stable else "Ranking changes: ") +
                      "; ".join(f"{criterion}: " + " > ".join(order) for criterion, order in rankings.items()), ""]
            for pair, criteria in summary[f"{block}_paired"].get(name, {}).items():
                counts = "; ".join(f"{criterion} {v['wins']}-{v['ties']}-{v['losses']} "
                                   f"(mean {v['mean_difference']:+.4f})" for criterion, v in criteria.items())
                lines += [f"Per-scenario win-tie-loss, {pair}: {counts}", ""]
    (out / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=Path, default=ROOT / "data/runs")
    parser.add_argument("--ablation", type=Path, default=ROOT / "data/ablation")
    parser.add_argument("--out", type=Path, default=ROOT / "data/ablation/criterion_sensitivity")
    args = parser.parse_args()

    datasets = {domain: ab.load_scenarios(ROOT / path) for domain, path in rp.DATASETS.items()}
    rows = legacy_rows(datasets["semiconductor_work"], args.runs) + ablation_rows(datasets, args.ablation)
    rows += matched_pilot(rows)
    args.out.mkdir(parents=True, exist_ok=True)
    sr.write_scores(args.out / "scores.csv", flatten(rows))
    summary = {"criteria": list(CRITERIA), "runs": len(rows),
               "legacy_overall": means(rows, "legacy_overall"), "process_overall": means(rows, "process_overall"),
               "legacy_overall_paired": paired(rows, "legacy_overall"),
               "process_overall_paired": paired(rows, "process_overall")}
    ab.save(args.out / "summary.json", summary)
    report(summary, args.out, "mean coverage per arm")
    print(ab.dump(summary["process_overall"]))
    print(f"Re-scored {len(rows)} workflows under {len(CRITERIA)} criteria into {args.out}")


if __name__ == "__main__":
    main()
