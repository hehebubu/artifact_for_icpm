#!/usr/bin/env python3
"""Draw a blinded sample of OUTPUT-side elements for human rating.

run_output_side.py classifies every element a reconstruction states. Nothing human
has looked at that classification, and its largest class -- elements stated outside
the reference with no lexical trace in anything the run was given -- is the one the
paper leans on hardest. This draws a sample of it, plus controls on the three classes
the classifier assigns by rule, so the rules themselves can be checked.

Like sample_human_eval.py, items are clustered into a few pipelines on purpose: a
rater reads one initial description, one answer set and one reconstruction per
cluster, so concentrating the items keeps the reading cost down. Items within a
cluster are not independent draws; report the design as a purposive stratified
cluster sample.

The strata below use the within-field criterion, the one the paper reports.
"""
import argparse
import collections
import csv
import json
import random
from pathlib import Path

import run_question_ablation as ab

ROOT = ab.ROOT
STRUCTURAL = ("activities", "decisions", "exceptions")
STRATA = (
    # The claim with no human check behind it, in the categories that carry a model.
    ("untraceable_structural",
     lambda r: r["label_field"] == "untraceable" and r["category"] in STRUCTURAL, 10),
    # The same class in the data-label categories, where benign elaboration is likelier.
    ("untraceable_data",
     lambda r: r["label_field"] == "untraceable" and r["category"] not in STRUCTURAL, 6),
    # Control: does "traceable to the description or the answers" hold up to a reader?
    ("grounded", lambda r: r["label_field"] == "grounded", 4),
    # Do the two rule-assigned classes survive reading?
    ("restated_artifact", lambda r: r["label_field"] == "restated_artifact", 2),
    ("abstention", lambda r: r["label_field"] == "abstention", 2),
)
CLUSTERS, WARMUP = 8, 3


def run_key(row):
    return row["corpus"], row["domain"], row["scenario_id"], row["arm"]


def pick_clusters(rows, count):
    """Choose the pipelines richest in the stratum that motivates the study."""
    weight = collections.Counter()
    for row in rows:
        if STRATA[0][1](row):
            weight[run_key(row)] += 2
        elif STRATA[1][1](row):
            weight[run_key(row)] += 1
    return [key for key, _ in weight.most_common(count)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--items", type=Path, default=ROOT / "data/ablation/output_side_v1/items.csv")
    parser.add_argument("--out", type=Path, default=ROOT / "data/ablation/human_eval_output_v1")
    parser.add_argument("--seed", type=int, default=20261111)
    args = parser.parse_args()

    rows = list(csv.DictReader(args.items.open(encoding="utf-8")))
    generator = random.Random(args.seed)

    clusters = pick_clusters(rows, CLUSTERS)
    inside = [r for r in rows if run_key(r) in clusters]

    sample, used = [], set()
    for name, predicate, size in STRATA:
        pool = [r for r in inside if predicate(r) and id(r) not in used]
        by_run = collections.OrderedDict()
        for row in sorted(pool, key=lambda r: clusters.index(run_key(r))):
            by_run.setdefault(run_key(row), []).append(row)
        picked, rounds = [], 0
        # Spread the quota over the clusters rather than draining one of them.
        while len(picked) < min(size, len(pool)) and rounds < 50:
            for key in clusters:
                members = [r for r in by_run.get(key, []) if id(r) not in used]
                if members and len(picked) < min(size, len(pool)):
                    choice = generator.choice(members)
                    used.add(id(choice))
                    picked.append(choice)
            rounds += 1
        sample += [{**row, "stratum": name, "role": "scored"} for row in picked]

    # Warm-up items come from a pipeline outside the scored clusters.
    spare = [k for k in {run_key(r) for r in rows if STRATA[0][1](r)} if k not in clusters]
    warmup = []
    if spare:
        chosen = generator.choice(spare)
        pool = [r for r in rows if run_key(r) == chosen
                and (STRATA[0][1](r) or STRATA[1][1](r) or STRATA[2][1](r))]
        warmup = [{**row, "stratum": "warmup", "role": "warmup"}
                  for row in generator.sample(pool, min(WARMUP, len(pool)))]

    generator.shuffle(sample)
    for index, row in enumerate(warmup, start=1):
        row["item_no"] = f"W{index}"
    for index, row in enumerate(sample, start=1):
        row["item_no"] = f"O{index:02d}"

    args.out.mkdir(parents=True, exist_ok=True)
    fields = ["item_no", "role", "stratum", "corpus", "domain", "scenario_id", "arm",
              "category", "item", "reference_match", "desc_match", "answer_match",
              "label_document", "label_field", "label_exact"]
    with (args.out / "sample.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(warmup + sample)

    populations = {name: sum(1 for r in rows if predicate(r)) for name, predicate, _ in STRATA}
    manifest = {"seed": args.seed, "direction": "output-side",
                "criterion": "within-field",
                "design": "purposive stratified cluster sample",
                "clusters": len({run_key(r) for r in sample}),
                "warmup": len(warmup), "scored": len(sample),
                "strata": {name: sum(1 for r in sample if r["stratum"] == name)
                           for name, _, _ in STRATA},
                "stratum_populations": populations,
                "categories": dict(collections.Counter(r["category"] for r in sample)),
                "blocks_to_read": len({run_key(r) for r in warmup + sample})}
    (args.out / "sample_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
