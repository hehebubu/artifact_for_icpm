#!/usr/bin/env python3
"""Top up the forward-direction human sample without disturbing the first 24.

The first round rated 24 items (data/ablation/human_eval_v1). Two of its strata are
thin -- six items called unsupported by both criteria, twelve called dropped on
scattered output evidence alone -- and the paper's claim about the lexical labels
rests on them. This draws a second, disjoint sample that thickens those strata.

The first round's items are excluded, so its ratings stay valid and the two rounds can
be pooled or reported apart. Use the existing sheet builder on the output directory:

    python3 scripts/sample_forward_topup.py
    python3 scripts/build_rating_sheet.py --dir data/ablation/human_eval_v1_topup
"""
import argparse
import collections
import csv
import json
import random
from pathlib import Path

import run_question_ablation as ab
import sample_human_eval as base

ROOT = ab.ROOT
STRATA = (
    ("undecidable", base.STRATA[0][1], 6),
    ("unsupported", base.STRATA[1][1], 6),
    ("recovered", base.STRATA[2][1], 4),
    # No "absent" stratum: its population is 14, round 1 took two of them, and the rest
    # sit in pipelines outside these clusters, so drawing them would cost a whole extra
    # block of reading for two items. Round 1 covers that stratum.
)
CLUSTERS, WARMUP = 6, 3


def identity(row):
    return (row["corpus"], row["domain"], row["scenario_id"], row["arm"],
            row["category"], row["item"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--items", type=Path, default=ROOT / "data/ablation/provenance_v1/items.csv")
    parser.add_argument("--rated", type=Path, default=ROOT / "data/ablation/human_eval_v1/sample.csv")
    parser.add_argument("--out", type=Path, default=ROOT / "data/ablation/human_eval_v1_topup")
    parser.add_argument("--seed", type=int, default=20261111)
    args = parser.parse_args()

    already = {identity(r) for r in csv.DictReader(args.rated.open(encoding="utf-8"))}
    rows = [r for r in csv.DictReader(args.items.open(encoding="utf-8"))
            if r["cached"] == "no" and r["category"] != "automation_targets"
            and identity(r) not in already]
    generator = random.Random(args.seed)

    clusters = base.pick_clusters(rows, CLUSTERS)
    inside = [r for r in rows if base.run_key(r) in clusters]

    sample, used = [], set()
    for name, predicate, size in STRATA:
        pool = [r for r in inside if predicate(r) and id(r) not in used]
        by_run = collections.OrderedDict()
        for row in sorted(pool, key=lambda r: clusters.index(base.run_key(r))):
            by_run.setdefault(base.run_key(row), []).append(row)
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

    spare = [k for k in {base.run_key(r) for r in rows if STRATA[0][1](r)} if k not in clusters]
    warmup = []
    if spare:
        chosen = generator.choice(spare)
        pool = [r for r in rows if base.run_key(r) == chosen
                and (STRATA[0][1](r) or STRATA[2][1](r))]
        warmup = [{**row, "stratum": "warmup", "role": "warmup"}
                  for row in generator.sample(pool, min(WARMUP, len(pool)))]

    generator.shuffle(sample)
    for index, row in enumerate(warmup, start=1):
        row["item_no"] = f"W{index}"
    for index, row in enumerate(sample, start=1):
        row["item_no"] = f"T{index:02d}"

    args.out.mkdir(parents=True, exist_ok=True)
    fields = ["item_no", "role", "stratum", "corpus", "domain", "scenario_id", "arm", "category", "item",
              "desc_match", "question_match", "answer_match", "output_match", "gaps_match",
              "label", "label_field", "label_exact"]
    with (args.out / "sample.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(warmup + sample)

    manifest = {"seed": args.seed, "round": 2,
                "design": "purposive stratified cluster sample, disjoint from round 1",
                "excluded_from_round_1": len(already),
                "clusters": len({base.run_key(r) for r in sample}),
                "warmup": len(warmup), "scored": len(sample),
                "strata": {name: sum(1 for r in sample if r["stratum"] == name) for name, _, _ in STRATA},
                "categories": dict(collections.Counter(r["category"] for r in sample)),
                "blocks_to_read": len({base.run_key(r) for r in warmup + sample})}
    (args.out / "sample_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
