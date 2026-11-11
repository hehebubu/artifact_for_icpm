#!/usr/bin/env python3
"""Compare blinded human ratings with the three lexical membership criteria."""
import argparse
import collections
import csv
import json
from pathlib import Path

import run_question_ablation as ab

ROOT = ab.ROOT
IN_OUTPUT = {"present", "paraphrase"}
# Which output match levels each criterion accepts as "the item is in the output".
ACCEPTS = {"document": {"scatter", "field", "exact"}, "field": {"field", "exact"}, "exact": {"exact"}}


def fleiss_kappa(table):
    """table: list of per-item category counts, all rows summing to the same n."""
    rows = [r for r in table if sum(r) > 0]
    if not rows:
        return None
    n = sum(rows[0])
    N, k = len(rows), len(rows[0])
    if n < 2:
        return None
    p_j = [sum(row[j] for row in rows) / (N * n) for j in range(k)]
    P_i = [(sum(c * c for c in row) - n) / (n * (n - 1)) for row in rows]
    P_bar = sum(P_i) / N
    P_e = sum(p * p for p in p_j)
    return (P_bar - P_e) / (1 - P_e) if P_e < 1 else None


def cohen_kappa(a, b):
    pairs = [(x, y) for x, y in zip(a, b) if x and y]
    if not pairs:
        return None
    cats = sorted({c for pair in pairs for c in pair})
    n = len(pairs)
    po = sum(x == y for x, y in pairs) / n
    pe = sum((sum(x == c for x, _ in pairs) / n) * (sum(y == c for _, y in pairs) / n) for c in cats)
    return (po - pe) / (1 - pe) if pe < 1 else None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dir", type=Path, default=ROOT / "data/ablation/human_eval_v1")
    parser.add_argument("--ratings", type=Path, default=None)
    args = parser.parse_args()

    ratings_path = args.ratings or (args.dir / "ratings_3raters_combined.csv")
    rows = [r for r in csv.DictReader(ratings_path.open(encoding="utf-8-sig")) if r["item_no"]]
    sample = {r["item_no"]: r for r in csv.DictReader((args.dir / "sample.csv").open(encoding="utf-8-sig"))}

    raters = sorted({r["rater"] for r in rows})
    scored = sorted({r["item_no"] for r in rows if not r["item_no"].startswith("W")})
    by = {(r["rater"], r["item_no"]): r for r in rows}

    summary = {"raters": raters, "scored_items": len(scored), "warmup_excluded":
               len({r["item_no"] for r in rows if r["item_no"].startswith("W")})}

    # --- agreement among raters -------------------------------------------------
    agreement = {}
    for q, cats in (("q1_present", ["present", "paraphrase", "absent"]),
                    ("q3_support", ["supported", "unsupported", "unclear"])):
        table = []
        for item in scored:
            counts = collections.Counter(by[(r, item)][q] for r in raters if (r, item) in by)
            table.append([counts.get(c, 0) for c in cats])
        exact_agree = sum(1 for row in table if max(row) == len(raters))
        agreement[q] = {"fleiss_kappa": round(fleiss_kappa(table), 4),
                        "unanimous_items": exact_agree,
                        "unanimous_rate": round(exact_agree / len(scored), 4),
                        "pairwise_cohen": {f"{a}-{b}": round(cohen_kappa(
                            [by[(a, i)][q] for i in scored], [by[(b, i)][q] for i in scored]), 4)
                            for idx, a in enumerate(raters) for b in raters[idx + 1:]}}
    summary["agreement"] = agreement

    # --- majority judgement -----------------------------------------------------
    majority = {}
    for item in scored:
        q1 = collections.Counter(by[(r, item)]["q1_present"] for r in raters if (r, item) in by)
        q3 = collections.Counter(by[(r, item)]["q3_support"] for r in raters if (r, item) in by)
        majority[item] = {"q1": q1.most_common(1)[0][0], "q1_votes": dict(q1),
                          "q3": q3.most_common(1)[0][0], "q3_votes": dict(q3),
                          "q1_split": max(q1.values()) < len(raters)}
    summary["majority_q1"] = dict(collections.Counter(m["q1"] for m in majority.values()))
    summary["majority_q3"] = dict(collections.Counter(m["q3"] for m in majority.values()))

    # --- do the lexical criteria match the humans? ------------------------------
    criteria = {}
    for name, accepted in ACCEPTS.items():
        tp = fp = fn = tn = 0
        for item in scored:
            lex_in = sample[item]["output_match"] in accepted
            human_in = majority[item]["q1"] in IN_OUTPUT
            tp += lex_in and human_in
            fp += lex_in and not human_in
            fn += not lex_in and human_in
            tn += not lex_in and not human_in
        total = tp + fp + fn + tn
        criteria[name] = {"agree": tp + tn, "agreement_rate": round((tp + tn) / total, 4),
                          "criterion_says_present_human_says_absent": fp,
                          "criterion_says_absent_human_says_present": fn}
    summary["criterion_vs_human_presence"] = criteria

    # --- the stratum the study exists for ---------------------------------------
    undecidable = [i for i in scored if sample[i]["stratum"] == "undecidable"]
    counts = collections.Counter(majority[i]["q1"] for i in undecidable)
    summary["undecidable_stratum"] = {
        "items": len(undecidable), "majority_q1": dict(counts),
        "reworded_not_lost": counts.get("paraphrase", 0) + counts.get("present", 0),
        "genuinely_absent": counts.get("absent", 0),
        "split_votes": sum(1 for i in undecidable if majority[i]["q1_split"])}

    unsupported = [i for i in scored if sample[i]["stratum"] == "unsupported"]
    q3 = collections.Counter(majority[i]["q3"] for i in unsupported)
    summary["unsupported_stratum"] = {"items": len(unsupported), "majority_q3": dict(q3),
                                      "humans_confirm_unsupported": q3.get("unsupported", 0),
                                      "humans_say_supported": q3.get("supported", 0),
                                      "unclear": q3.get("unclear", 0)}

    recovered = [i for i in scored if sample[i]["stratum"] == "recovered"]
    summary["recovered_stratum"] = {
        "items": len(recovered),
        "majority_q1": dict(collections.Counter(majority[i]["q1"] for i in recovered)),
        "attachment_correct": sum(1 for i in recovered
                                  if collections.Counter(by[(r, i)]["q2_attachment"]
                                                         for r in raters).most_common(1)[0][0] == "correct")}

    # --- attachment --------------------------------------------------------------
    q2 = collections.Counter()
    for item in scored:
        votes = [by[(r, item)]["q2_attachment"] for r in raters if (r, item) in by and by[(r, item)]["q2_attachment"]]
        if votes:
            q2[collections.Counter(votes).most_common(1)[0][0]] += 1
    summary["attachment_majority"] = dict(q2)

    out = args.dir / "agreement.json"
    out.write_text(json.dumps({"summary": summary, "per_item": majority}, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
