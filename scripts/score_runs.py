#!/usr/bin/env python3
import argparse
import csv
import json
import re
from pathlib import Path


STAGE_ORDER = ["one_shot", "checklist", "update"]
STAGE_LABELS = {
    "one_shot": "One-shot",
    "checklist": "Checklist",
    "update": "Active",
}

CATEGORIES = [
    "activities",
    "actors",
    "systems",
    "inputs",
    "outputs",
    "decisions",
    "exceptions",
    "automation_opportunities",
]

WORKFLOW_STAGES = {"one_shot", "checklist", "update"}


def main():
    parser = argparse.ArgumentParser(description="Score LLM workflow runs against synthetic reference workflows.")
    parser.add_argument("--scenarios", default="data/scenarios.json", help="Path to scenario dataset JSON.")
    parser.add_argument("--runs", default="data/runs", help="Directory containing saved run JSON files.")
    parser.add_argument("--out", default="data/evaluation/scores.csv", help="Output CSV path.")
    parser.add_argument("--summary", default="data/evaluation/summary.json", help="Output summary JSON path.")
    parser.add_argument("--tables-dir", default="tables", help="Directory for generated LaTeX tables.")
    parser.add_argument("--figures-dir", default="figures", help="Directory for generated TikZ figures.")
    parser.add_argument("--include-non-workflow", action="store_true", help="Also score question/oracle logs.")
    args = parser.parse_args()

    scenarios = load_scenarios(Path(args.scenarios))
    run_files = sorted(Path(args.runs).glob("*.json"))
    rows = []

    for run_file in run_files:
        run = read_json(run_file)
        scenario_id = run.get("request", {}).get("scenario", {}).get("id")
        if scenario_id not in scenarios:
            continue

        parsed = run.get("result", {}).get("parsed")
        result = parsed if parsed is not None else run.get("result", {}).get("raw_text", "")
        stage = run.get("result", {}).get("stage") or run.get("request", {}).get("stage", "unknown")
        if not args.include_non_workflow and stage not in WORKFLOW_STAGES:
            continue
        scores = score_result(scenarios[scenario_id], result)
        row = {
            "scenario_id": scenario_id,
            "stage": stage,
            "stage_label": STAGE_LABELS.get(stage, stage),
            "model": run.get("result", {}).get("model", ""),
            "parse_success": "yes" if parsed is not None else "no",
            "run_file": str(run_file),
            **{f"{category}_score": scores[category]["score"] for category in CATEGORIES},
            **{f"{category}_covered": scores[category]["covered"] for category in CATEGORIES},
            **{f"{category}_total": scores[category]["total"] for category in CATEGORIES},
            "overall_score": scores["overall_score"],
        }
        rows.append(row)

    write_scores(Path(args.out), rows)
    write_summary(Path(args.summary), rows)
    write_latex_tables(Path(args.tables_dir), rows)
    write_tikz_figures(Path(args.figures_dir), rows)
    print(f"Wrote {len(rows)} scored runs to {args.out}")
    print(f"Wrote summary to {args.summary}")
    print(f"Wrote LaTeX tables to {args.tables_dir}")
    print(f"Wrote TikZ figures to {args.figures_dir}")


def load_scenarios(path):
    data = read_json(path)
    return {scenario["id"]: scenario for scenario in data["scenarios"]}


def score_result(scenario, result):
    reference = scenario["reference_workflow"]
    result_text = normalize(json.dumps(result, ensure_ascii=False))
    ref_items = {
        "activities": [item["name"] for item in reference.get("activities", [])],
        "actors": reference.get("actors", []),
        "systems": reference.get("systems", []),
        "inputs": reference.get("inputs", []),
        "outputs": reference.get("outputs", []),
        "decisions": [item["condition"] for item in reference.get("decisions", [])],
        "exceptions": reference.get("exceptions", []),
        "automation_opportunities": [item["target"] for item in reference.get("automation_opportunities", [])],
    }

    scores = {}
    for category, items in ref_items.items():
        covered_items = [item for item in items if soft_contains(result_text, item)]
        total = len(items)
        covered = len(covered_items)
        scores[category] = {
            "covered": covered,
            "total": total,
            "score": round(covered / total, 3) if total else 0.0,
            "covered_items": covered_items,
            "missing_items": [item for item in items if item not in covered_items],
        }

    scores["overall_score"] = round(sum(scores[category]["score"] for category in CATEGORIES) / len(CATEGORIES), 3)
    return scores


def soft_contains(text, item):
    item_norm = normalize(item)
    if item_norm in text:
        return True

    tokens = [token for token in item_norm.split() if len(token) > 2]
    if not tokens:
        return False

    if len(tokens) <= 2:
        return all(token in text for token in tokens)

    matches = sum(1 for token in tokens if token in text)
    return matches / len(tokens) >= 0.6


def normalize(value):
    text = str(value).lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def write_scores(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return

    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_summary(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    grouped = {}
    for row in rows:
        stage = row["stage"]
        grouped.setdefault(stage, []).append(row)

    summary = {}
    for stage, stage_rows in grouped.items():
        summary[stage] = {
            "runs": len(stage_rows),
            "overall_score_mean": round(mean(float(row["overall_score"]) for row in stage_rows), 3),
            "category_score_mean": {
                category: round(mean(float(row[f"{category}_score"]) for row in stage_rows), 3)
                for category in CATEGORIES
            },
        }

    path.write_text(json.dumps(summary, indent=2), encoding="utf-8")


def write_latex_tables(path, rows):
    path.mkdir(parents=True, exist_ok=True)
    by_scenario = {}
    for row in rows:
        by_scenario.setdefault(row["scenario_id"], {})[row["stage"]] = row

    scenario_lines = [
        "\\begin{table}[H]",
        "\\caption{Reference coverage score by scenario and method.}",
        "\\label{tab:scenario-coverage}",
        "\\centering",
        "\\begin{tabular}{lccc}",
        "\\toprule",
        "Scenario & One-shot & Checklist & Active \\\\",
        "\\midrule",
    ]
    for scenario_id in sorted(by_scenario):
        values = []
        for stage in STAGE_ORDER:
            row = by_scenario[scenario_id].get(stage)
            values.append(format_score(row["overall_score"]) if row else "--")
        scenario_lines.append(f"{scenario_id} & {values[0]} & {values[1]} & {values[2]} \\\\")
    scenario_lines.extend([
        "\\midrule",
        f"Mean & {format_score(stage_mean(rows, 'one_shot', 'overall_score'))} & {format_score(stage_mean(rows, 'checklist', 'overall_score'))} & {format_score(stage_mean(rows, 'update', 'overall_score'))} \\\\",
        "\\bottomrule",
        "\\end{tabular}",
        "\\end{table}",
        "",
    ])
    (path / "scenario_coverage_table.tex").write_text("\n".join(scenario_lines), encoding="utf-8")

    category_lines = [
        "\\begin{table}[H]",
        "\\caption{Mean reference coverage by information category.}",
        "\\label{tab:category-coverage}",
        "\\centering",
        "\\begin{tabular}{lccc}",
        "\\toprule",
        "Category & One-shot & Checklist & Active \\\\",
        "\\midrule",
    ]
    for category in CATEGORIES:
        label = category.replace("_", " ").title()
        vals = [format_score(stage_mean(rows, stage, f"{category}_score")) for stage in STAGE_ORDER]
        category_lines.append(f"{label} & {vals[0]} & {vals[1]} & {vals[2]} \\\\")
    category_lines.extend([
        "\\bottomrule",
        "\\end{tabular}",
        "\\end{table}",
        "",
    ])
    (path / "category_coverage_table.tex").write_text("\n".join(category_lines), encoding="utf-8")


def write_tikz_figures(path, rows):
    path.mkdir(parents=True, exist_ok=True)
    means = [stage_mean(rows, stage, "overall_score") for stage in STAGE_ORDER]
    max_height = 4.2
    bar_width = 1.15
    gap = 0.55
    colors = {
        "one_shot": "gray!55",
        "checklist": "teal!55",
        "update": "orange!70",
    }

    lines = [
        "\\begin{figure}[H]",
        "\\centering",
        "\\begin{tikzpicture}[font=\\small]",
        "\\draw[->] (0,0) -- (0,4.7) node[above] {Coverage};",
        "\\draw[->] (0,0) -- (6.0,0);",
    ]
    for tick in [0, 0.25, 0.5, 0.75, 1.0]:
        y = tick * max_height
        lines.append(f"\\draw[gray!35] (0,{y:.2f}) -- (5.7,{y:.2f});")
        lines.append(f"\\node[left] at (0,{y:.2f}) {{{tick:.2f}}};")

    for index, stage in enumerate(STAGE_ORDER):
        x = 0.65 + index * (bar_width + gap)
        height = means[index] * max_height
        lines.append(f"\\filldraw[fill={colors[stage]}, draw=black!55] ({x:.2f},0) rectangle ({x + bar_width:.2f},{height:.2f});")
        lines.append(f"\\node[above] at ({x + bar_width / 2:.2f},{height:.2f}) {{{means[index]:.3f}}};")
        lines.append(f"\\node[below, align=center] at ({x + bar_width / 2:.2f},-0.12) {{{STAGE_LABELS[stage]}}};")

    lines.extend([
        "\\end{tikzpicture}",
        "\\caption{Mean reference coverage across eight synthetic workflow scenarios.}",
        "\\label{fig:overall-coverage}",
        "\\Description{Bar chart comparing mean reference coverage for one-shot, checklist, and active elicitation methods.}",
        "\\end{figure}",
        "",
    ])
    (path / "evaluation-overall-coverage.tex").write_text("\n".join(lines), encoding="utf-8")


def stage_mean(rows, stage, field):
    values = [float(row[field]) for row in rows if row["stage"] == stage]
    return mean(values)


def format_score(value):
    if value == "--":
        return value
    return f"{float(value):.3f}"


def mean(values):
    values = list(values)
    return sum(values) / len(values) if values else 0.0


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
