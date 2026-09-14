#!/usr/bin/env python3
"""Answer-quality ladder with repeated generation; standard library only.

One question set per scenario and repeat is shared by every answer level, so the
levels differ only in the simulated expert's answers.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import http.client
from pathlib import Path
import random
import statistics
import time
import urllib.error

import rescore_criteria as rc
import run_provenance as rp
import run_question_ablation as ab

ROOT = ab.ROOT
PROTOCOL = "answer-ladder-v1"
LEVELS = ("L3", "L3p", "L2", "L1", "L0")
ANCHOR = "L3"
STAGES = ("questions", "oracle_answers", "update")
LADDER = {
    "L3": "",
    "L3p": """
Additional constraint for this respondent: convey the same information as above, but do not reuse the
reference workflow's wording. Rephrase every activity, system, artifact, actor and condition in your own
words while preserving the meaning. Do not copy reference phrases verbatim.
""",
    "L2": """
Additional constraint for this respondent: this expert is in a hurry. Use at most 25 words per answer.
Keep the most decision-relevant fact and drop elaboration. Do not add information to compensate.
""",
    "L1": """
Additional constraint for this respondent: this expert knows only part of the process. Answer questions
Q1 through Q{half} as instructed above. For every remaining question, reply exactly:
"I am not sure about that." Do not provide any fact for those questions.
""",
    "L0": """
Additional constraint for this respondent: this expert answers vaguely and never commits to specifics.
Do not name any actor, system, artifact, threshold, condition or exception from the reference workflow.
Use hedged generalities such as "the person in charge usually checks it before it goes out".
Answer every question in this style, at most 30 words each.
""",
}


def run_stage(directory, stage, prompt, args, api_key, attempts=4):
    # ab.call_api retries HTTP status codes only; connection resets reach us unretried.
    for attempt in range(attempts):
        try:
            return ab.run_stage(directory, stage, prompt, args, api_key)
        except (OSError, http.client.HTTPException, urllib.error.URLError) as exc:
            if attempt == attempts - 1:
                raise RuntimeError(f"{exc} after {attempts} connection attempts") from None
            time.sleep(min(30, 3 * 2 ** attempt))


def oracle_prompt(scenario, questions, level, count):
    # L3 must stay byte-identical to the frozen protocol so it anchors the ladder.
    return ab.oracle_prompt(scenario, questions) + LADDER[level].format(half=(count + 1) // 2)


def evaluate(scenario, run, level, answers, workflow, paths):
    result = {key: workflow.get(key) for key in ("workflow", "automation_opportunities")}
    scores = rc.coverage(scenario, result)
    items = rp.rows_for(run, scenario)
    process = [row for row in items if row["category"] != "automation_targets"]
    row = {"scenario_id": scenario["id"], "repeat": run["repeat"], "level": level,
           **{f"{criterion}_process": round(scores[criterion]["process_overall"], 4) for criterion in rc.CRITERIA},
           **{f"{criterion}_legacy": round(scores[criterion]["legacy_overall"], 4) for criterion in rc.CRITERIA},
           **{f"field_{category}": round(
               sum(rp.match_level(rp.source(result), item) in rc.ACCEPTED["field"]
                   for item in values) / len(values), 4) if values else 0.0
              for category, values in rp.reference_items(scenario).items()},
           "answer_words": sum(len(a["answer"].split()) for a in answers["answers"]),
           "unsure_answers": sum(1 for a in answers["answers"] if "not sure" in a["answer"].lower()),
           **{key: sum(ab.read(path)["response"].get("usage", {}).get(key, 0) for path in paths.values())
              for key in ("input_tokens", "output_tokens")},
           **{f"provenance_{label}": sum(1 for r in process if r["label_field"] == label) for label in rp.LABELS}}
    return row, {"row": row, "coverage": scores, "provenance": rp.tally(process, "label_field"), "items": items}


def run_scenario(scenario, repeat, args, api_key):
    rows, errors = [], []
    base = args.out / "runs" / f"r{repeat:02d}" / scenario["id"]
    try:
        questions = run_stage(base, "questions", ab.question_prompt(scenario, "generic", args.questions), args, api_key)
        texts = [{"id": q["id"], "question": q["question"]} for q in questions["clarification_questions"]]
    except (RuntimeError, ValueError, KeyError, TypeError, OSError) as exc:
        error = {"scenario_id": scenario["id"], "repeat": repeat, "level": "questions", "error": str(exc)}
        ab.save(base / "failure.json", error)
        print(f"r{repeat:02d} {scenario['id']} questions: FAILED ({exc})", flush=True)
        return rows, [error]
    # Counterbalance level order across scenarios and repeats.
    offset = (int(scenario["id"][1:]) + repeat) % len(LEVELS)
    for level in LEVELS[offset:] + LEVELS[:offset]:
        directory = base / level
        try:
            answers = run_stage(directory, "oracle_answers", oracle_prompt(scenario, texts, level, args.questions), args, api_key)
            workflow = run_stage(directory, "update", ab.update_prompt(scenario, answers), args, api_key)
            paths = {"questions": base / "questions.json", **{s: directory / f"{s}.json" for s in STAGES[1:]}}
            run = {"corpus": PROTOCOL, "domain": args.domain, "scenario_id": scenario["id"], "arm": level,
                   "repeat": repeat, "cached": False, "paths": paths}
            row, evaluation = evaluate(scenario, run, level, answers, workflow, paths)
            ab.save(directory / "evaluation.json", evaluation)
            rows.append(row)
            print(f"r{repeat:02d} {scenario['id']} {level}: field={row['field_process']:.3f} "
                  f"document={row['document_process']:.3f} words={row['answer_words']}", flush=True)
        except (RuntimeError, ValueError, KeyError, TypeError, OSError) as exc:
            error = {"scenario_id": scenario["id"], "repeat": repeat, "level": level, "error": str(exc)}
            errors.append(error)
            ab.save(directory / "failure.json", error)
            print(f"r{repeat:02d} {scenario['id']} {level}: FAILED ({exc})", flush=True)
    return rows, errors


def bootstrap(differences, seed, resamples=10000):
    if len(differences) < 2:
        return None
    generator = random.Random(seed)
    means = sorted(statistics.mean(generator.choices(differences, k=len(differences))) for _ in range(resamples))
    low, high = means[int(0.025 * resamples)], means[int(0.975 * resamples) - 1]
    return {"mean_difference": round(statistics.mean(differences), 4), "ci_low": round(low, 4),
            "ci_high": round(high, 4), "pairs": len(differences)}


def summarize(args, rows, errors):
    by_level = {level: [row for row in rows if row["level"] == level] for level in LEVELS}
    paired = {}
    for row in rows:
        paired.setdefault((row["scenario_id"], row["repeat"]), {})[row["level"]] = row
    complete = [levels for levels in paired.values() if all(level in levels for level in LEVELS)]
    metrics = [f"{criterion}_process" for criterion in rc.CRITERIA] + ["answer_words", "unsure_answers"] + \
              [f"provenance_{label}" for label in rp.LABELS]
    summary = {"protocol": PROTOCOL, "levels": list(LEVELS), "complete_sets": len(complete),
               "expected_sets": args.repeats * args.expected_scenarios, "errors": errors,
               "levels_summary": {level: {metric: {
                   "mean": round(statistics.mean(r[metric] for r in group), 4),
                   "sd": round(statistics.stdev(r[metric] for r in group), 4) if len(group) > 1 else None}
                   for metric in metrics} for level, group in by_level.items() if group},
               "paired_vs_anchor": {level: {metric: bootstrap(
                   [levels[ANCHOR][metric] - levels[level][metric] for levels in complete], args.seed)
                   for metric in [f"{criterion}_process" for criterion in rc.CRITERIA]}
                   for level in LEVELS if level != ANCHOR}}
    return summary


def report(args, summary, rows):
    levels = [level for level in LEVELS if level in summary["levels_summary"]]
    value = lambda level, metric, key="mean": summary["levels_summary"][level][metric][key]
    cell = lambda level, metric: (f"{value(level, metric):.3f}" +
                                  (f" ± {value(level, metric, 'sd'):.3f}" if value(level, metric, "sd") is not None else ""))
    lines = ["# Answer-Quality Ladder", "",
             f"Complete level sets: {summary['complete_sets']}/{summary['expected_sets']}. "
             f"Repeats: {args.repeats} at temperature {args.temperature}. One shared question set per scenario "
             "and repeat; the levels differ only in the simulated expert's answers.", "",
             "Levels: `L3` the frozen full-answer protocol; `L3p` the same information rephrased away from the "
             "reference wording; `L2` at most 25 words per answer; `L1` only the first half of the questions "
             "answered; `L0` vague answers with no specifics.", "",
             "| Level | " + " | ".join(f"{c} coverage" for c in rc.CRITERIA) + " | answer words | unsure answers |",
             "|---" * (len(rc.CRITERIA) + 3) + "|"]
    for level in levels:
        lines.append(f"| {level} | " + " | ".join(cell(level, f"{c}_process") for c in rc.CRITERIA) +
                     f" | {cell(level, 'answer_words')} | {cell(level, 'unsure_answers')} |")
    lines += ["", "Values are mean ± standard deviation across scenarios and repeats.", "",
              "## Paired difference from L3, bootstrap 95% CI", "",
              "| Level | " + " | ".join(f"{c} coverage" for c in rc.CRITERIA) + " |", "|---" * (len(rc.CRITERIA) + 1) + "|"]
    for level in levels:
        if level == ANCHOR:
            continue
        cells = []
        for criterion in rc.CRITERIA:
            stat = summary["paired_vs_anchor"][level][f"{criterion}_process"]
            cells.append("--" if not stat else f"{stat['mean_difference']:+.3f} [{stat['ci_low']:+.3f}, {stat['ci_high']:+.3f}]")
        lines.append(f"| L3 - {level} | " + " | ".join(cells) + " |")
    lines += ["", "A positive difference means the full-answer anchor scores higher than that level. "
              "The L3 - L3p row isolates how much of the anchor's coverage rests on the simulated expert "
              "reusing the reference vocabulary rather than on the information conveyed.", "",
              "## Provenance of reference items by level", "",
              "| Level | " + " | ".join(rp.LABELS) + " |", "|---" * (len(rp.LABELS) + 1) + "|"]
    for level in levels:
        lines.append(f"| {level} | " + " | ".join(cell(level, f"provenance_{label}") for label in rp.LABELS) + " |")
    lines += ["", "Counts are per pipeline, under the within-field criterion.", "",
              "## Limits", "",
              "The ladder varies a simulated respondent, not real experts; L1 withholds the second half of the "
              "questions by position, which is a stand-in for partial knowledge rather than a model of it. "
              "Coverage stays lexical under every criterion and does not establish semantic correctness. "
              "Repeats estimate generation variance for these scenarios only; they do not add independent scenarios.", ""]
    (args.out / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenarios", type=Path, default=ROOT / "data/scenarios.json")
    parser.add_argument("--domain", default="semiconductor_work")
    parser.add_argument("--out", type=Path, default=ROOT / "data/ablation/answer_ladder_v1")
    parser.add_argument("--model", default="claude-sonnet-4-6")
    parser.add_argument("--questions", type=int, default=6)
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--max-tokens", type=int, default=4000)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--seed", type=int, default=20260908)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--report-only", action="store_true")
    args = parser.parse_args()
    if min(args.questions, args.repeats, args.workers, args.max_tokens) < 1 or not 0 <= args.temperature <= 1:
        parser.error("Counts must be positive; temperature must be between 0 and 1")

    scenarios = list(ab.load_scenarios(args.scenarios).values())
    args.expected_scenarios = len(scenarios)
    config = {"protocol": PROTOCOL, "levels": list(LEVELS), "anchor": ANCHOR,
              "dataset_sha256": hashlib.sha256(args.scenarios.read_bytes()).hexdigest(),
              "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "scorer_sha256": hashlib.sha256((ROOT / "scripts/score_runs.py").read_bytes()).hexdigest(),
              "criteria": list(rc.CRITERIA), "primary_endpoint": "field_criterion_seven_category_process_coverage",
              **{k: getattr(args, k) for k in ("model", "domain", "questions", "repeats", "temperature", "max_tokens", "seed")}}
    calls = len(scenarios) * args.repeats * (1 + 2 * len(LEVELS))
    print(f"{len(scenarios)} scenarios x {args.repeats} repeats x (1 question + {len(LEVELS)} levels x 2 stages) = "
          f"{calls} API calls before retries (cached calls skipped).", flush=True)
    if args.dry_run:
        print(ab.dump(config))
        return

    manifest = args.out / "manifest.json"
    if manifest.exists():
        original = ab.read(manifest)
        if {k: v for k, v in original.items() if k != "script_sha256"} != {k: v for k, v in config.items() if k != "script_sha256"}:
            parser.error("Existing experiment configuration differs; choose a new --out directory")
    if args.report_only:
        rows = [ab.read(path)["row"] for path in (args.out / "runs").glob("*/*/*/evaluation.json")]
        errors = [ab.read(path) for path in (args.out / "runs").glob("*/*/*/failure.json")
                  if not (path.parent / "evaluation.json").exists()]
    else:
        api_key = ab.load_key()
        if not api_key:
            parser.error("ANTHROPIC_API_KEY is missing; set it in the environment or project .env")
        if not manifest.exists():
            ab.save(manifest, config)
        ab.save(args.out / "implementations" / f"{config['script_sha256']}.json", config)
        rows, errors = [], []
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = [pool.submit(run_scenario, scenario, repeat, args, api_key)
                       for repeat in range(1, args.repeats + 1) for scenario in scenarios]
            for future in as_completed(futures):
                scenario_rows, scenario_errors = future.result()
                rows.extend(scenario_rows)
                errors.extend(scenario_errors)

    rows.sort(key=lambda r: (r["scenario_id"], r["repeat"], LEVELS.index(r["level"])))
    ab.write_scores(args.out / "scores.csv", rows)
    summary = summarize(args, rows, errors)
    ab.save(args.out / "summary.json", summary)
    report(args, summary, rows)
    print(ab.dump(summary["levels_summary"]), flush=True)


if __name__ == "__main__":
    main()
