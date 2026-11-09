#!/usr/bin/env python3
"""Draw a blinded sample of reference items for human rating.

Items are clustered into a few pipelines on purpose. A rater has to read one
reconstructed workflow and one answer set per pipeline, so concentrating the
items keeps the reading cost near an hour instead of several. The cost is that
items within a pipeline are not independent draws; report the design as a
purposive stratified cluster sample.
"""
import argparse
import collections
import csv
import json
import random
from pathlib import Path

import run_question_ablation as ab

ROOT = ab.ROOT
STRATA = (
    ("undecidable", lambda r: r["label_field"] == "dropped" and r["output_match"] == "scatter", 12),
    ("unsupported", lambda r: r["label"] == "unsupported" and r["label_field"] == "unsupported", 6),
    ("recovered", lambda r: r["label_field"] == "recovered", 4),
    ("absent", lambda r: r["label_field"] == "dropped" and r["output_match"] == "none", 2),
)
CLUSTERS, WARMUP = 8, 3


def run_key(row):
    return row["corpus"], row["domain"], row["scenario_id"], row["arm"]


def pick_clusters(rows, count):
    """Choose the pipelines richest in the strata that motivate the study."""
    weight = collections.Counter()
    for row in rows:
        if STRATA[0][1](row):
            weight[run_key(row)] += 2
        elif STRATA[1][1](row):
            weight[run_key(row)] += 1
    return [key for key, _ in weight.most_common(count)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--items", type=Path, default=ROOT / "data/ablation/provenance_v1/items.csv")
    parser.add_argument("--out", type=Path, default=ROOT / "data/ablation/human_eval_v1")
    parser.add_argument("--seed", type=int, default=20261106)
    args = parser.parse_args()

    rows = [r for r in csv.DictReader(args.items.open(encoding="utf-8"))
            if r["cached"] == "no" and r["category"] != "automation_targets"]
    generator = random.Random(args.seed)

    clusters = pick_clusters(rows, CLUSTERS)
    inside = [r for r in rows if run_key(r) in clusters]

    sample, used = [], set()
    for name, predicate, size in STRATA:
        pool = [r for r in inside if predicate(r) and id(r) not in used]
        # Spread the quota over the clusters rather than draining one of them.
        by_run = collections.OrderedDict()
        for row in sorted(pool, key=lambda r: clusters.index(run_key(r))):
            by_run.setdefault(run_key(r := row), []).append(row)
        picked, rounds = [], 0
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
    spare_runs = [k for k in {run_key(r) for r in rows if STRATA[0][1](r)} if k not in clusters]
    warmup = []
    if spare_runs:
        chosen = generator.choice(spare_runs)
        pool = [r for r in rows if run_key(r) == chosen and (STRATA[0][1](r) or STRATA[2][1](r))]
        warmup = [{**row, "stratum": "warmup", "role": "warmup"}
                  for row in generator.sample(pool, min(WARMUP, len(pool)))]

    generator.shuffle(sample)
    for index, row in enumerate(warmup, start=1):
        row["item_no"] = f"W{index}"
    for index, row in enumerate(sample, start=1):
        row["item_no"] = f"I{index:02d}"

    args.out.mkdir(parents=True, exist_ok=True)
    fields = ["item_no", "role", "stratum", "corpus", "domain", "scenario_id", "arm", "category", "item",
              "desc_match", "question_match", "answer_match", "output_match", "gaps_match",
              "label", "label_field", "label_exact"]
    with (args.out / "sample.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(warmup + sample)

    manifest = {"seed": args.seed, "design": "purposive stratified cluster sample",
                "clusters": len({run_key(r) for r in sample}), "warmup": len(warmup), "scored": len(sample),
                "strata": {name: sum(1 for r in sample if r["stratum"] == name) for name, _, _ in STRATA},
                "categories": dict(collections.Counter(r["category"] for r in sample)),
                "blocks_to_read": len({run_key(r) for r in warmup + sample})}
    (args.out / "sample_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
