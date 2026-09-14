#!/usr/bin/env python3
"""Emit LaTeX tables for the criterion band, provenance and answer-ladder results."""
import json
from pathlib import Path

import run_question_ablation as ab

ROOT = ab.ROOT
TABLES = ROOT / "tables"
LEVEL_LABEL = {"L3": "L3 full", "L3p": "L3p reworded", "L2": "L2 compressed",
               "L1": "L1 partial", "L0": "L0 vague"}


def wrap(caption, label, spec, header, rows, note=None):
    lines = ["\\begin{table}[t]", f"\\caption{{{caption}}}", f"\\label{{{label}}}", "\\centering",
             "\\small", f"\\begin{{tabular}}{{{spec}}}", "\\toprule", header, "\\midrule", *rows,
             "\\bottomrule", "\\end{tabular}"]
    if note:
        lines.append(f"\\par\\vspace{{2pt}}\\footnotesize {note}")
    return "\n".join(lines + ["\\end{table}", ""])


def criterion_band():
    data = json.loads((ROOT / "data/ablation/criterion_sensitivity/summary.json").read_text())
    groups = data["process_overall"]["runs/semiconductor_work"]
    rows = [f"{name} & " + " & ".join(f"{groups[key][c]:.3f}" for c in ("document", "field", "exact")) + " \\\\"
            for key, name in (("one_shot", "One-shot"), ("checklist", "Checklist"), ("update", "Active"))]
    return wrap("Reference coverage under three lexical match criteria. The stored criterion accepts an item "
                "when its tokens occur anywhere in the serialized output; within-field requires the same tokens "
                "inside one field value; exact requires the full phrase.",
                "tab:criterion-band", "lccc",
                "Condition & Document & Within-field & Exact \\\\", rows,
                "Seven process categories; the ID-matched automation category is excluded.")


def provenance():
    data = json.loads((ROOT / "data/ablation/provenance_v1/summary.json").read_text())
    rows = []
    for name, key in (("Stored document", "overall"), ("Within-field", "overall_within_field_criterion"),
                      ("Exact phrase", "overall_exact_match_criterion")):
        s = data[key]
        rows.append(f"{name} & {s['recovered']} & {s['dropped']} & {s['unsupported']} & {s['missed']} \\\\")
    core = data["robust_core"]
    note = (f"Under both the stored and within-field criteria, {core['unsupported_under_both_criteria']} items are "
            f"unsupported and {core['dropped_under_both_criteria']} are dropped; a further "
            f"{core['dropped_only_scattered_output_evidence']} answered items are dropped under the within-field "
            "criterion alone, which no lexical test separates from rewording.")
    return wrap(f"Provenance of {data['overall']['items']} reference items across "
                f"{data['distinct_pipelines']} elicitation pipelines. Recovered: answered and present in the "
                "output. Dropped: answered but absent. Unsupported: present without support in the description "
                "or the answers. Missed: neither answered nor present.",
                "tab:provenance", "lcccc",
                "Match criterion & Recovered & Dropped & Unsupported & Missed \\\\", rows, note)


def ladder():
    data = json.loads((ROOT / "data/ablation/answer_ladder_v1/summary.json").read_text())
    levels, paired = data["levels_summary"], data["paired_vs_anchor"]
    rows = []
    for level in data["levels"]:
        stats = levels[level]
        cells = [f"{stats[f'{c}_process']['mean']:.3f}" for c in ("document", "field", "exact")]
        difference = paired.get(level, {}).get("field_process")
        gap = "--" if not difference else \
            f"{difference['mean_difference']:+.3f} [{difference['ci_low']:+.3f}, {difference['ci_high']:+.3f}]"
        rows.append(f"{LEVEL_LABEL[level]} & {stats['answer_words']['mean']:.0f} & " +
                    " & ".join(cells) + f" & {gap} \\\\")
    return wrap("Answer-quality ladder over 200 pipelines (8 scenarios, 5 repeats, temperature 0.7). "
                "L3p conveys the same information as L3 in different words. The last column is the paired "
                "difference from L3 under the within-field criterion with a bootstrap 95\\% confidence interval.",
                "tab:answer-ladder", "lccccc",
                "Answer level & Words & Document & Within-field & Exact & L3 $-$ level (within-field) \\\\", rows,
                "Rewording alone costs as much coverage as compressing every answer to 25 words.")


def main():
    TABLES.mkdir(exist_ok=True)
    for name, builder in (("criterion_band_table", criterion_band), ("provenance_table", provenance),
                          ("answer_ladder_table", ladder)):
        (TABLES / f"{name}.tex").write_text(builder(), encoding="utf-8")
        print(f"wrote tables/{name}.tex")


if __name__ == "__main__":
    main()
