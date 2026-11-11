#!/usr/bin/env python3
"""Analyse the output-side ratings against the classifier's own labels.

Reads every ratings_*.csv in the sample directory (the sheet exports one per rater),
computes agreement, takes the majority judgement per item, and sets it against what
run_output_side.py called each element.

The question the paper asks of this sample: of the elements the classifier calls
untraceable, how many does a reader also find unsupported, and how many turn out to be
paraphrase or derivation that the lexical test missed? The confusion table below is the
answer, and the "mistakable" count says how many of the genuine additions would read to
an analyst as elicited fact.

    python3 scripts/analyze_output_eval.py
"""
import argparse
import collections
import csv
import itertools
import json
from pathlib import Path

import run_question_ablation as ab
from analyze_human_eval import cohen_kappa, fleiss_kappa

ROOT = ab.ROOT
QUESTIONS = {"q1_support": ("supported", "partial", "unsupported", "unclear"),
             "q2_nature": ("paraphrase", "derivation", "abstention", "declared_gap", "addition")}
# What the classifier's label would predict a reader should answer for q2.
EXPECTED = {"grounded": ("paraphrase", "derivation"), "abstention": ("abstention",),
            "restated_artifact": ("derivation",), "untraceable": ("addition", "declared_gap")}


def majority(values):
    """The value a majority of raters gave, or "tie" when none has one."""
    counts = collections.Counter(v for v in values if v)
    if not counts:
        return "none"
    top = counts.most_common()
    return "tie" if len(top) > 1 and top[0][1] == top[1][1] else top[0][0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dir", type=Path, default=ROOT / "data/ablation/human_eval_output_v1")
    args = parser.parse_args()

    sample = {r["item_no"]: r for r in csv.DictReader((args.dir / "sample.csv").open(encoding="utf-8"))}
    files = sorted(p for p in args.dir.rglob("ratings_*.csv"))
    if not files:
        parser.error(f"no ratings_*.csv under {args.dir}")
    ratings = {}
    for path in files:
        rater = path.stem.replace("ratings_output_", "").replace("ratings_", "")
        for row in csv.DictReader(path.open(encoding="utf-8")):
            ratings.setdefault(row["item_no"], {})[rater] = row
    raters = sorted({r for v in ratings.values() for r in v})

    scored = [n for n in sample if sample[n]["role"] == "scored"
              and len(ratings.get(n, {})) == len(raters)]
    summary = {"raters": raters, "scored_items": len(scored),
               "warmup_excluded": sum(1 for n in sample if sample[n]["role"] == "warmup"),
               "agreement": {}, "majority": {}, "classifier_vs_human": {}}

    for question, categories in QUESTIONS.items():
        table = [[sum(1 for r in raters if ratings[n][r][question] == c) for c in categories]
                 for n in scored]
        block = {"fleiss_kappa": fleiss_kappa(table) if len(raters) > 2 else None,
                 "unanimous_items": sum(1 for row in table if max(row) == len(raters)),
                 "pairwise_cohen": {f"{a}-{b}": cohen_kappa(
                     [ratings[n][a][question] for n in scored],
                     [ratings[n][b][question] for n in scored])
                     for a, b in itertools.combinations(raters, 2)}}
        summary["agreement"][question] = block
        summary["majority"][question] = dict(collections.Counter(
            majority([ratings[n][r][question] for r in raters]) for n in scored))

    # Does the classifier's label predict what a reader says the element is?
    confusion = collections.Counter()
    for item in scored:
        label = sample[item]["label_field"]
        human = majority([ratings[item][r]["q2_nature"] for r in raters])
        confusion[(label, human)] += 1
    summary["classifier_vs_human"] = {f"{label} -> {human}": n
                                      for (label, human), n in sorted(confusion.items())}
    summary["label_agrees_with_reader"] = {
        label: {"n": sum(n for (l, _), n in confusion.items() if l == label),
                "as_expected": sum(n for (l, h), n in confusion.items()
                                   if l == label and h in EXPECTED.get(label, ()))}
        for label in sorted({l for l, _ in confusion})}

    # Of the elements a reader calls genuine additions, how many read as elicited fact?
    additions = [n for n in scored
                 if majority([ratings[n][r]["q2_nature"] for r in raters]) == "addition"]
    summary["additions"] = {
        "n": len(additions),
        "mistakable_for_elicited_fact": sum(
            1 for n in additions
            if majority([ratings[n][r]["q3_mistakable"] for r in raters]) == "mistakable"),
        "by_category": dict(collections.Counter(sample[n]["category"] for n in additions)),
        "from_untraceable": sum(1 for n in additions if sample[n]["label_field"] == "untraceable")}

    summary["incomplete_items"] = [n for n in sample
                                   if sample[n]["role"] == "scored" and n not in scored]
    ab.save(args.dir / "agreement.json", summary)
    print(ab.dump(summary))


if __name__ == "__main__":
    main()
