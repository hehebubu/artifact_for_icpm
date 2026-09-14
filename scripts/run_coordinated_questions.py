#!/usr/bin/env python3
"""Coordinate cached generic/taxonomy proposals, then answer, reconstruct and compare."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
from pathlib import Path
import statistics

import run_question_ablation as ab

PROTOCOL = "coordinated-questions-v1"
ARMS = ("generic", "gapelicit", "coordinated")


def fingerprint(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def payload(record):
    response = record["response"]
    if response.get("stop_reason") != "end_turn":
        raise ValueError("Incomplete source response")
    return ab.parse_response("\n".join(b.get("text", "") for b in response["content"] if b.get("type") == "text"))


def candidates_for(scenario, baseline, args):
    candidates, provenance = [], {}
    pools = {}
    for arm in ab.ARMS:
        file = baseline / "runs" / "r01" / scenario["id"] / arm / "questions.json"
        record = ab.read(file)
        expected = {"model": args.model, "temperature": args.temperature, "max_tokens": args.max_tokens,
                    "messages": [{"role": "user", "content": ab.question_prompt(scenario, arm, args.questions)}]}
        if record["request"] != expected:
            raise ValueError("Source question prompt/settings differ from the matched protocol")
        parsed = payload(record)
        ab.validate("questions", parsed, args.questions)
        pools[arm] = parsed["clarification_questions"]
    # Alternate source order and hide arm names to reduce presentation preference.
    order = ab.ARMS if int(scenario["id"][1:]) % 2 else ab.ARMS[::-1]
    for index in range(args.questions):
        for arm in order:
            q = pools[arm][index]
            cid = f"C{len(candidates) + 1}"
            candidates.append({"candidate_id": cid, "question": q["question"]})
            provenance[cid] = {"arm": arm, "question_id": q["id"]}
    return candidates, provenance


def coordinator_prompt(scenario, candidates, count):
    return ab.context(scenario) + """
Role: You coordinate clarification questions proposed by two independent questioning agents.
Task: Select and refine a complementary question set for workflow reconstruction and automation assessment.
Judge each candidate using the initial description: its relevance, the uncertainty it addresses,
the value of obtaining its answer, its likely burden on the respondent, and overlap with other candidates.
Preserve useful diverse perspectives. Do not assume any source is more authoritative.
Avoid redundant questions and bundles of unrelated information needs. You may select, rephrase,
or merge overlapping candidate questions, but cannot introduce an unrelated question.
You do not have the reference answers. Do not guess them or assume which facts an expert knows.
Candidate questions:
""" + ab.dump(candidates) + f"""
Return JSON with this shape:
{{"missing_information": [{{"category": "short label", "gap": "missing information", "why_it_matters": "reason"}}],
"clarification_questions": [{{"id": "Q1", "question": "final expert-facing question", "targets": ["short label"],
"source_ids": ["C1"], "selection_reason": "brief reason for including this question"}}]}}
Return exactly {count} questions with unique IDs Q1 through Q{count}.
Each question must have one main information need. Cite at least one valid candidate ID in source_ids.
Do not use any candidate ID for more than one final question.
"""


def validate_selection(parsed, candidates):
    valid = {c["candidate_id"] for c in candidates}
    used = set()
    for question in parsed["clarification_questions"]:
        ids = question.get("source_ids")
        if not isinstance(ids, list) or not ids or not all(isinstance(i, str) for i in ids):
            raise ValueError("Selection must cite candidate IDs")
        if len(set(ids)) != len(ids) or not set(ids) <= valid or used.intersection(ids):
            raise ValueError("Invalid, duplicate or reused candidate ID")
        used.update(ids)


def row_for(scenario, arm, workflow, answers, records):
    scores = ab.score_result(scenario, workflow)
    structured = ab.score_result(scenario, {k: workflow[k] for k in ("workflow", "automation_opportunities")})
    row = {"scenario_id": scenario["id"], "arm": arm, "overall_score": scores["overall_score"],
           "structured_only_score": structured["overall_score"],
           **{c: scores[c]["score"] for c in ab.CATEGORIES},
           "answer_words": sum(len(a["answer"].split()) for a in answers["answers"]),
           "pipeline_calls": len(records),
           **{k: sum(r["response"].get("usage", {}).get(k, 0) for r in records)
              for k in ("input_tokens", "output_tokens")}}
    return row, scores, structured


def baseline_row(scenario, arm, args):
    directory = args.baseline / "runs" / "r01" / scenario["id"] / arm
    records = [ab.read(directory / f"{stage}.json") for stage in ("questions", "oracle_answers", "update")]
    return row_for(scenario, arm, payload(records[2]), payload(records[1]), records)[0]


def run_scenario(scenario, args, api_key):
    directory = args.out / "runs" / scenario["id"]
    candidates, provenance = candidates_for(scenario, args.baseline, args)
    ab.save(directory / "candidates.json", {"candidates": candidates, "provenance": provenance})
    selection = ab.run_stage(directory, "questions", coordinator_prompt(scenario, candidates, args.questions), args, api_key)
    validate_selection(selection, candidates)
    texts = [{"id": q["id"], "question": q["question"]} for q in selection["clarification_questions"]]
    answers = ab.run_stage(directory, "oracle_answers", ab.oracle_prompt(scenario, texts), args, api_key)
    workflow = ab.run_stage(directory, "update", ab.update_prompt(scenario, answers), args, api_key)
    records = [ab.read(args.baseline / "runs" / "r01" / scenario["id"] / arm / "questions.json") for arm in ab.ARMS]
    records += [ab.read(directory / f"{stage}.json") for stage in ("questions", "oracle_answers", "update")]
    row, scores, structured = row_for(scenario, "coordinated", workflow, answers, records)
    provenance_counts = {"generic_only": 0, "gapelicit_only": 0, "mixed": 0}
    for q in selection["clarification_questions"]:
        sources = {provenance[cid]["arm"] for cid in q["source_ids"]}
        key = "mixed" if len(sources) == 2 else next(iter(sources)) + "_only"
        provenance_counts[key] += 1
    ab.save(directory / "evaluation.json", {"row": row, "scores": scores,
            "structured_only": structured, "selection_provenance": provenance_counts})
    print(f"{scenario['id']} coordinated: {row['overall_score']:.3f} (structured {row['structured_only_score']:.3f})", flush=True)
    return row


def report(args, scenarios, rows, errors):
    rows += [baseline_row(s, arm, args) for s in scenarios for arm in ab.ARMS]
    rows.sort(key=lambda r: (r["scenario_id"], ARMS.index(r["arm"])))
    ab.write_scores(args.out / "scores.csv", rows)
    grouped = {}
    for row in rows:
        grouped.setdefault(row["scenario_id"], {})[row["arm"]] = row
    complete = {sid: arms for sid, arms in grouped.items() if all(a in arms for a in ARMS)}
    means = {arm: {k: statistics.mean(arms[arm][k] for arms in complete.values()) if complete else None
                   for k in ("overall_score", "structured_only_score", "answer_words", "pipeline_calls",
                             "input_tokens", "output_tokens", *ab.CATEGORIES)} for arm in ARMS}
    comparisons = {}
    for baseline in ab.ARMS:
        differences = [arms["coordinated"]["overall_score"] - arms[baseline]["overall_score"] for arms in complete.values()]
        comparisons[baseline] = {"mean_difference": statistics.mean(differences) if differences else None,
            "wins": sum(d > 1e-9 for d in differences), "ties": sum(abs(d) <= 1e-9 for d in differences),
            "losses": sum(d < -1e-9 for d in differences)}
    selection_counts = {key: sum(ab.read(args.out / "runs" / sid / "evaluation.json")["selection_provenance"][key]
                                for sid in complete) for key in ("generic_only", "gapelicit_only", "mixed")}
    summary = {"protocol": PROTOCOL, "expected_scenarios": len(scenarios), "complete_scenarios": len(complete),
               "means_complete_cases": means, "coordinated_vs": comparisons,
               "selected_question_sources": selection_counts, "errors": errors}
    ab.save(args.out / "summary.json", summary)
    lines = ["# Coordinated Question Pilot", "", f"Complete scenarios: {len(complete)}/{len(scenarios)}", "",
             "| Scenario | Generic | Taxonomy | Coordinated |", "|---|---:|---:|---:|"]
    for sid, arms in sorted(complete.items()):
        lines.append("| " + sid + " | " + " | ".join(f"{arms[a]['overall_score']:.3f}" for a in ARMS) + " |")
    if complete:
        lines.append("| Mean | " + " | ".join(f"{means[a]['overall_score']:.3f}" for a in ARMS) + " |")
        lines += ["", "| Metric | Generic | Taxonomy | Coordinated |", "|---|---:|---:|---:|"]
        for key in ("structured_only_score", "answer_words", "pipeline_calls", "input_tokens", "output_tokens", *ab.CATEGORIES):
            lines.append("| " + key + " | " + " | ".join(f"{means[a][key]:.3f}" for a in ARMS) + " |")
    lines += ["", "## Protocol and Limits", "",
              "Two independent, cached proposal agents (generic and taxonomy-guided) provide six candidates each. "
              "A third coordinator selects/refines six final questions; there is no iterative debate. "
              "All roles use the same LLM. They do not represent actual laypeople and experts.", "",
              "The coordinator receives only initial description and candidate texts. It has no reference, score, "
              "baseline outcome, or candidate source labels. Provenance is reconstructed after selection.", "",
              "Answer and reconstruction prompts/settings are unchanged from the matched pilot. "
              "Question budgets match, but coordination uses three question-generation calls instead of one. "
              "Pipeline token counts include both cached proposal calls: five calls versus three per baseline. "
              "This execution adds only three fresh calls per scenario because proposals are reused.", "",
              "This is an adaptive exploratory experiment on the same eight scenarios after observing baseline results. "
              "There is no held-out test, repeated-generation estimate, human correctness evaluation, or compute-matched "
              "single-agent refinement control. A higher mean cannot establish general superiority or unique multi-agent value.", "",
              "Legacy coverage is lexical and may count unknown facts in remaining_gaps. Structured-only excludes that field "
              "but still does not establish semantic correctness or automation feasibility. Oracle answers may overinfer facts.", "",
              f"Coordinator candidate-source counts: {ab.dump(selection_counts)}", "",
              "No historical paper tables or manuscript text were changed."]
    (args.out / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(ab.dump(summary), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, default=ab.ROOT / "data/ablation/generic_questions_v1")
    parser.add_argument("--out", type=Path, default=ab.ROOT / "data/ablation/coordinated_questions_v1")
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--report-only", action="store_true")
    args = parser.parse_args()
    if args.workers < 1:
        parser.error("workers must be positive")
    source = ab.read(args.baseline / "manifest.json")
    if source["repeats"] != 1 or source["protocol"] != ab.PROTOCOL:
        parser.error("Expected the one-repeat matched question pilot")
    dataset = ab.ROOT / "data/scenarios.json"
    if fingerprint(dataset) != source["dataset_sha256"] or fingerprint(ab.ROOT / "scripts/score_runs.py") != source["scorer_sha256"]:
        parser.error("Dataset or scorer changed since baseline")
    for key in ("model", "questions", "temperature", "max_tokens"):
        setattr(args, key, source[key])
    scenarios = list(ab.load_scenarios(dataset).values())
    source_hashes = {}
    for s in scenarios:
        candidates_for(s, args.baseline, args)
        for arm in ab.ARMS:
            for stage in ("questions", "oracle_answers", "update"):
                f = args.baseline / "runs" / "r01" / s["id"] / arm / f"{stage}.json"
                record = ab.read(f)
                ab.validate(stage, payload(record), args.questions)
                source_hashes[str(f.relative_to(args.baseline))] = fingerprint(f)
    config = {"protocol": PROTOCOL, "source_manifest": source, "source_response_hashes": source_hashes,
              "script_sha256": fingerprint(Path(__file__)), "helper_sha256": fingerprint(Path(ab.__file__))}
    print(f"{len(scenarios)} scenarios; {len(scenarios)*2} cached proposal calls; {len(scenarios)*3} new API calls before retries.", flush=True)
    if args.dry_run:
        print("Source prompts, reference/scorer hashes, response validity and settings verified.")
        return 0
    manifest = args.out / "manifest.json"
    if manifest.exists() and ab.read(manifest) != config:
        parser.error("Experiment implementation or inputs changed; use a new output directory")
    errors, rows = [], []
    if args.report_only:
        for s in scenarios:
            file = args.out / "runs" / s["id"] / "evaluation.json"
            if file.exists():
                rows.append(ab.read(file)["row"])
            else:
                errors.append({"scenario_id": s["id"], "error": "Missing evaluation"})
    else:
        key = ab.load_key()
        if not key:
            parser.error("ANTHROPIC_API_KEY is missing")
        ab.save(manifest, config)
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = {pool.submit(run_scenario, s, args, key): s["id"] for s in scenarios}
            for future in as_completed(futures):
                sid = futures[future]
                try:
                    rows.append(future.result())
                except (ValueError, RuntimeError, KeyError, TypeError, OSError) as exc:
                    error = {"scenario_id": sid, "error": str(exc)}
                    errors.append(error)
                    ab.save(args.out / "runs" / sid / "failure.json", error)
                    print(f"{sid}: FAILED ({exc})", flush=True)
    report(args, scenarios, rows, errors)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
