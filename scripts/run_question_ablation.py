#!/usr/bin/env python3
"""Matched generic-question vs taxonomy-guided pilot; standard library only."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import statistics
import time
import urllib.error
import urllib.request

from score_runs import CATEGORIES, load_scenarios, score_result, write_scores

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = "question-ablation-v1"
ARMS = ("generic", "gapelicit")
TAXONOMY = ("actor, system, input, output, decision, exception, dependency, "
            "frequency, manual_effort, data_availability, integration_constraint, risk_or_approval")
WORKFLOW_SHAPE = {
    "workflow": {
        "activities": [{"id": "A1", "name": "...", "actor": "...", "system": "...", "inputs": [], "outputs": []}],
        "decisions": [{"id": "D1", "condition": "...", "branches": []}],
        "exceptions": [], "dependencies": [{"from": "A1", "to": "A2", "type": "control_flow"}]},
    "automation_opportunities": [{"target": "activity or decision", "rationale": "...",
                                "required_data": [], "constraints": [], "confidence": "low | medium | high"}],
    "remaining_gaps": []}


def dump(value):
    return json.dumps(value, ensure_ascii=False, indent=2)


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(dump(value) + "\n", encoding="utf-8")
    temporary.replace(path)


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def parse_response(raw):
    fenced = re.fullmatch(r"\s*```(?:json)?\s*\n(.*?)\n```\s*", raw, flags=re.DOTALL)
    return json.loads(fenced.group(1) if fenced else raw)


def context(scenario):
    # Whitelist the initial inputs; never serialize the scenario in question/update prompts.
    return ("You are supporting a process mining research prototype.\n"
            "Use only the synthetic scenario information provided below.\n"
            "Do not invent company-specific system names, product names, confidential logs, "
            "internal metrics, or real organizational details.\n"
            "Return valid JSON only. Do not wrap it in Markdown.\n\n"
            f"Scenario ID: {scenario['id']}\nScenario title: {scenario['title']}\n"
            f"Initial workflow description:\n{scenario['initial_description']}\n")


def question_prompt(scenario, arm, count):
    instruction = "Identify missing or ambiguous information and ask useful clarification questions for the domain expert."
    if arm == "gapelicit":
        instruction += (" Use the following automation-critical gap taxonomy to identify gaps and guide question selection: "
                        + TAXONOMY + ". Prioritize gaps relevant to this scenario; do not force every category.")
    return context(scenario) + f"""
Task: Clarify the workflow so that it can be reconstructed and assessed for automation opportunities.
{instruction}
Return JSON with this shape:
{{"missing_information": [{{"category": "short label", "gap": "missing information", "why_it_matters": "reason"}}],
"clarification_questions": [{{"id": "Q1", "question": "question for the domain expert", "targets": ["short label"]}}]}}
Ask exactly {count} questions with unique IDs Q1 through Q{count}.
Each question must have one main information need; avoid bundles of unrelated subquestions.
"""


def oracle_prompt(scenario, questions):
    # The oracle sees question text only, not arm names, taxonomy, or gap rationales.
    return context(scenario) + "\nClarification questions:\n" + dump(questions) + """
Reference workflow for oracle use:
""" + dump(scenario["reference_workflow"]) + """
Task: Simulate a concise domain expert who answers only these questions using the reference workflow.
Do not reveal the full reference workflow. Do not add details not needed by the questions.
If a requested fact is absent, explicitly say it is not specified; do not guess.
Use at most 80 words per answer. Return one answer for each question, with matching ID and question text.
Return JSON: {"answers": [{"question_id": "Q1", "question": "original question", "answer": "grounded answer"}]}
"""


def update_prompt(scenario, answers):
    return context(scenario) + "\nDomain expert answers:\n" + dump(answers) + """
Task: Incorporate the answers and produce an updated structured workflow representation plus automation opportunities.
Record unknown facts as remaining gaps, rather than asserting unsupported details.
Return JSON with this shape:
""" + dump(WORKFLOW_SHAPE)


def validate(stage, parsed, count):
    if not isinstance(parsed, dict):
        raise ValueError("Response is not a JSON object")
    if stage == "questions":
        items = parsed.get("clarification_questions", [])
        if len(items) != count or {x.get("id") for x in items} != {f"Q{i}" for i in range(1, count + 1)}:
            raise ValueError("Question count or IDs do not match protocol")
        if not all(isinstance(x.get("question"), str) and x["question"].strip() for x in items):
            raise ValueError("Empty question")
    elif stage == "oracle_answers":
        items = parsed.get("answers", [])
        if len(items) != count or {x.get("question_id") for x in items} != {f"Q{i}" for i in range(1, count + 1)}:
            raise ValueError("Answer count or IDs do not match questions")
        if not all(isinstance(x.get("answer"), str) and x["answer"].strip() for x in items):
            raise ValueError("Empty answer")
        if any(len(x["answer"].split()) > 80 for x in items):
            raise ValueError("Answer exceeds the shared 80-word limit")
    elif not isinstance(parsed.get("workflow", {}).get("activities"), list) or not isinstance(parsed.get("automation_opportunities"), list):
        raise ValueError("Missing workflow or automation opportunities")


def call_api(request, api_key):
    for attempt in range(4):
        req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=dump(request).encode(),
            headers={"content-type": "application/json", "x-api-key": api_key, "anthropic-version": "2023-06-01"})
        try:
            with urllib.request.urlopen(req, timeout=240) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            if exc.code in (429, 500, 502, 503, 504, 529) and attempt < 3:
                time.sleep(min(30, 3 * 2 ** attempt))
                continue
            # Never print headers, environment variables, or credentials.
            raise RuntimeError(f"Anthropic HTTP {exc.code}; response not logged") from None
    raise RuntimeError("API retries exhausted")


def run_stage(directory, stage, prompt, args, api_key):
    request = {"model": args.model, "max_tokens": args.max_tokens, "temperature": args.temperature,
               "messages": [{"role": "user", "content": prompt}]}
    file = directory / f"{stage}.json"
    if file.exists():
        record = read(file)
        if record["request"] != request:
            raise ValueError("Cached request differs; use a new --out directory")
    else:
        started = time.monotonic()
        payload = call_api(request, api_key)
        record = {"created_at": datetime.now(timezone.utc).isoformat(), "request": request,
                  "elapsed_seconds": round(time.monotonic() - started, 2), "response": payload}
        save(file, record)
    response = record["response"]
    if response.get("stop_reason") != "end_turn":
        raise ValueError(f"Incomplete response: {response.get('stop_reason')}; saved for inspection")
    raw = "\n".join(x.get("text", "") for x in response.get("content", []) if x.get("type") == "text")
    parsed = parse_response(raw)
    validate(stage, parsed, args.questions)
    return parsed


def run_pair(scenario, repeat, args, api_key):
    rows, errors = [], []
    # Counterbalance execution order across scenarios and repetitions.
    order = ARMS if (int(scenario["id"][1:]) + repeat) % 2 else ARMS[::-1]
    for arm in order:
        directory = args.out / "runs" / f"r{repeat:02d}" / scenario["id"] / arm
        try:
            questions = run_stage(directory, "questions", question_prompt(scenario, arm, args.questions), args, api_key)
            question_texts = [{"id": q["id"], "question": q["question"]} for q in questions["clarification_questions"]]
            answers = run_stage(directory, "oracle_answers", oracle_prompt(scenario, question_texts), args, api_key)
            workflow = run_stage(directory, "update", update_prompt(scenario, answers), args, api_key)
            scores = score_result(scenario, workflow)
            # Sensitivity analysis: gap text is not recovered workflow information.
            structured = score_result(scenario, {k: workflow[k] for k in ("workflow", "automation_opportunities")})
            tokens = {key: sum(read(directory / f"{stage}.json")["response"].get("usage", {}).get(key, 0)
                               for stage in ("questions", "oracle_answers", "update"))
                      for key in ("input_tokens", "output_tokens")}
            row = {"scenario_id": scenario["id"], "repeat": repeat, "arm": arm,
                   "overall_score": scores["overall_score"], "structured_only_score": structured["overall_score"],
                   **{c: scores[c]["score"] for c in CATEGORIES}, "question_count": len(question_texts),
                   "answer_words": sum(len(a["answer"].split()) for a in answers["answers"]), **tokens}
            save(directory / "evaluation.json", {"row": row, "scores": scores, "structured_only": structured})
            rows.append(row)
            print(f"r{repeat:02d} {scenario['id']} {arm}: coverage={row['overall_score']:.3f}", flush=True)
        except (RuntimeError, ValueError, KeyError, TypeError, OSError) as exc:
            error = {"scenario_id": scenario["id"], "repeat": repeat, "arm": arm, "error": str(exc)}
            errors.append(error)
            save(directory / "failure.json", error)
            print(f"r{repeat:02d} {scenario['id']} {arm}: FAILED ({exc})", flush=True)
    return rows, errors


def report(args, scenarios, rows, errors):
    rows.sort(key=lambda r: (r["scenario_id"], r["repeat"], r["arm"]))
    write_scores(args.out / "scores.csv", rows)
    grouped = {}
    for row in rows:
        grouped.setdefault((row["scenario_id"], row["repeat"]), {})[row["arm"]] = row
    paired = [arms for arms in grouped.values() if all(a in arms for a in ARMS)]
    summary = {"protocol": PROTOCOL, "expected_pairs": len(scenarios) * args.repeats,
               "complete_pairs": len(paired), "errors": errors, "means_paired": {}}
    for arm in ARMS:
        summary["means_paired"][arm] = {
            k: statistics.mean(p[arm][k] for p in paired) if paired else None
            for k in ["overall_score", "structured_only_score", "answer_words", *CATEGORIES]}
    deltas = [p["gapelicit"]["overall_score"] - p["generic"]["overall_score"] for p in paired]
    summary["gapelicit_minus_generic"] = statistics.mean(deltas) if deltas else None
    summary["wins_ties_losses"] = {"wins": sum(d > 1e-9 for d in deltas), "ties": sum(abs(d) <= 1e-9 for d in deltas),
                                    "losses": sum(d < -1e-9 for d in deltas)}
    save(args.out / "summary.json", summary)
    lines = ["# Matched Question Ablation", "", f"Complete pairs: {len(paired)}/{summary['expected_pairs']}.", "",
             "| Scenario | Repeat | Generic | GapElicit | Difference |", "|---|---:|---:|---:|---:|"]
    for key, arms in sorted(grouped.items()):
        if all(a in arms for a in ARMS):
            g, t = (arms[a]["overall_score"] for a in ARMS)
            lines.append(f"| {key[0]} | {key[1]} | {g:.3f} | {t:.3f} | {t-g:+.3f} |")
    if paired:
        g, t = (summary["means_paired"][a]["overall_score"] for a in ARMS)
        lines += [f"| Mean | | {g:.3f} | {t:.3f} | {t-g:+.3f} |", "",
                  "| Category | Generic | GapElicit |", "|---|---:|---:|"]
        for c in [*CATEGORIES, "structured_only_score", "answer_words"]:
            lines.append(f"| {c} | {summary['means_paired']['generic'][c]:.3f} | {summary['means_paired']['gapelicit'][c]:.3f} |")
    lines += ["", "## Interpretation Limits", "",
              "This pilot controls model, question count, answer instructions and workflow reconstruction. "
              "The sole arm-specific prompt text is the taxonomy guidance. Generic questioning still uses "
              "the same process/automation objective and structured question output; it is not an unstructured chat baseline.", "",
              "Oracle answers can differ in length/content because questions differ. Equal question counts do not "
              "guarantee equal information or expert effort. Inspect questions for bundled requests and answers for leakage.", "",
              "The legacy lexical coverage score searches the entire generated JSON and does not establish correctness. "
              "The structured-only sensitivity score excludes remaining_gaps, but is still lexical. "
              "There is no human validation, hallucination penalty, or verified automation feasibility in this score.", "",
              "Historical 0.725/0.753/0.925 results are context, not matched controls: the new protocol fixes "
              "temperature, uses concise oracle answers, and standardizes downstream inputs. "
              "Do not replace the old results table by mixing these runs into it.", "",
              "One repeat per scenario is exploratory. Repeated generations do not increase the number of independent scenarios.", "",
              f"Failures: {len(errors)}. Means include complete pairs only; inspect summary.json for details."]
    (args.out / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(dump(summary), flush=True)


def load_key():
    if os.environ.get("ANTHROPIC_API_KEY"):
        return os.environ["ANTHROPIC_API_KEY"]
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            name, sep, value = line.strip().partition("=")
            if sep and name.strip() == "ANTHROPIC_API_KEY":
                return value.strip().strip("\"'")
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenarios", type=Path, default=ROOT / "data/scenarios.json")
    parser.add_argument("--out", type=Path, default=ROOT / "data/ablation/generic_questions_v1")
    parser.add_argument("--model", default="claude-sonnet-4-6")
    parser.add_argument("--questions", type=int, default=6)
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--temperature", type=float, default=0)
    parser.add_argument("--max-tokens", type=int, default=4000)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--report-only", action="store_true")
    args = parser.parse_args()
    if min(args.questions, args.repeats, args.workers, args.max_tokens) < 1 or not 0 <= args.temperature <= 1:
        parser.error("Counts must be positive; temperature must be between 0 and 1")
    scenarios = list(load_scenarios(args.scenarios).values())
    config = {"protocol": PROTOCOL, "dataset_sha256": hashlib.sha256(args.scenarios.read_bytes()).hexdigest(),
              "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "scorer_sha256": hashlib.sha256((ROOT / "scripts/score_runs.py").read_bytes()).hexdigest(),
              **{k: getattr(args, k) for k in ("model", "questions", "repeats", "temperature", "max_tokens")}}
    print(f"{len(scenarios)} scenarios x {args.repeats} repeats x 2 arms x 3 stages = "
          f"{len(scenarios) * args.repeats * 6} API calls before retries (cached calls skipped).", flush=True)
    if args.dry_run:
        print(dump(config))
        return
    manifest = args.out / "manifest.json"
    if manifest.exists():
        original = read(manifest)
        # Parser/report fixes can reuse exact request-matched API responses.
        if {k: v for k, v in original.items() if k != "script_sha256"} != {k: v for k, v in config.items() if k != "script_sha256"}:
            parser.error("Existing experiment configuration differs; choose a new --out directory")
    if args.report_only:
        rows = [read(p)["row"] for p in (args.out / "runs").glob("*/*/*/evaluation.json")]
        errors = [read(p) for p in (args.out / "runs").glob("*/*/*/failure.json") if not (p.parent / "evaluation.json").exists()]
    else:
        api_key = load_key()
        if not api_key:
            parser.error("ANTHROPIC_API_KEY is missing; set it in the environment or project .env")
        if not manifest.exists():
            save(manifest, config)
        save(args.out / "implementations" / f"{config['script_sha256']}.json", config)
        rows, errors = [], []
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = [pool.submit(run_pair, s, repeat, args, api_key)
                       for repeat in range(1, args.repeats + 1) for s in scenarios]
            for future in as_completed(futures):
                pair_rows, pair_errors = future.result()
                rows.extend(pair_rows)
                errors.extend(pair_errors)
    report(args, scenarios, rows, errors)
    return 1 if errors or len(rows) != len(scenarios) * args.repeats * 2 else 0


if __name__ == "__main__":
    raise SystemExit(main())
