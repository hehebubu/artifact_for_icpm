#!/usr/bin/env python3
"""Two-domain pilot: generic, common taxonomy, and contextualized taxonomy."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import statistics

import run_question_ablation as ab

ROOT = ab.ROOT
PROTOCOL = "domain-ablation-v1"
ARMS = ("generic", "common", "domain")
PROCESS_CATEGORIES = [c for c in ab.CATEGORIES if c != "automation_opportunities"]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def question_prompt(scenario, arm, domain, profiles, count):
    prompt = ab.question_prompt(scenario, "generic" if arm == "generic" else "gapelicit", count)
    if arm == "domain":
        prompt += "\nInterpret the same gap categories in this domain using the following contextual explanations. "
        prompt += "These are questioning lenses, not facts about this scenario or mandatory topics.\n"
        prompt += ab.dump(profiles["domains"][domain])
    return prompt


def pointer(document, path):
    value = document
    for part in path.strip("/").split("/"):
        value = value[int(part)] if isinstance(value, list) else value[part]
    return value


def validate_childcare(scenarios):
    if len(scenarios) != 8 or len({s["id"] for s in scenarios}) != 8:
        raise ValueError("Expected eight unique childcare scenarios")
    for s in scenarios:
        r = s["reference_workflow"]
        ids = {a["id"] for a in r["activities"]}
        if len(ids) != 8 or len(r["decisions"]) != 2:
            raise ValueError("Unexpected activity/decision design")
        if any(a["actor"] not in r["actors"] for a in r["activities"]):
            raise ValueError("Unknown activity actor")
        if any(e["from"] not in ids or e["to"] not in ids for e in r["dependencies"]):
            raise ValueError("Dangling dependency")
        if any(a["target"] not in ids for a in r["automation_opportunities"]):
            raise ValueError("Dangling automation target")
        for omission in s["omission_grounding"]:
            if not pointer(s, omission["reference_path"]):
                raise ValueError("Omission lacks reference support")
        if not s["initial_description"] or not r["operating_context"]:
            raise ValueError("Missing description or operating context")


def make_row(scenario, domain, arm, workflow, answers, paths, cached):
    legacy = ab.score_result(scenario, workflow)
    structured = ab.score_result(scenario, {k: workflow[k] for k in ("workflow", "automation_opportunities")})
    # Primary descriptive endpoint excludes gap declarations and ID-only opportunity matching.
    process = statistics.mean(structured[c]["score"] for c in PROCESS_CATEGORIES)
    row = {"domain": domain, "scenario_id": scenario["id"], "arm": arm,
           "process_coverage": process, "legacy_coverage": legacy["overall_score"],
           "structured_coverage": structured["overall_score"],
           **{c: structured[c]["score"] for c in PROCESS_CATEGORIES},
           "answer_words": sum(len(a["answer"].split()) for a in answers["answers"]),
           "cached_baseline": cached,
           **{k: sum(ab.read(p)["response"].get("usage", {}).get(k, 0) for p in paths)
              for k in ("input_tokens", "output_tokens")}}
    return row, legacy, structured


def run_scenario(domain, scenario, args, profiles, key):
    rows, errors = [], []
    offset = int(scenario["id"][1:]) % len(ARMS)
    for arm in ARMS[offset:] + ARMS[:offset]:
        out = args.out / "runs" / domain / scenario["id"] / arm
        cached = domain == "semiconductor_work" and arm in ("generic", "common")
        directory = (args.baseline / "runs" / "r01" / scenario["id"] /
                     ("generic" if arm == "generic" else "gapelicit")) if cached else out
        try:
            if cached and any(not (directory / f"{stage}.json").exists() for stage in ("questions", "oracle_answers", "update")):
                raise ValueError("Required cached baseline is missing")
            q = ab.run_stage(directory, "questions", question_prompt(scenario, arm, domain, profiles, args.questions), args, key)
            texts = [{"id": x["id"], "question": x["question"]} for x in q["clarification_questions"]]
            answers = ab.run_stage(directory, "oracle_answers", ab.oracle_prompt(scenario, texts), args, key)
            workflow = ab.run_stage(directory, "update", ab.update_prompt(scenario, answers), args, key)
            paths = [directory / f"{stage}.json" for stage in ("questions", "oracle_answers", "update")]
            row, legacy, structured = make_row(scenario, domain, arm, workflow, answers, paths, cached)
            ab.save(out / "evaluation.json", {"row": row, "legacy": legacy, "structured": structured,
                    "source_files": [str(p.relative_to(ROOT)) for p in paths]})
            rows.append(row)
            print(f"{scenario['id']} {arm}: process={row['process_coverage']:.4f}, legacy={row['legacy_coverage']:.3f}" +
                  (" [cached]" if cached else ""), flush=True)
        except (ValueError, RuntimeError, KeyError, TypeError, AttributeError, OSError) as exc:
            error = {"domain": domain, "scenario_id": scenario["id"], "arm": arm, "error": str(exc)}
            errors.append(error)
            ab.save(out / "failure.json", error)
            print(f"{scenario['id']} {arm}: FAILED ({exc})", flush=True)
    return rows, errors


def summarize(out, rows, errors):
    rows.sort(key=lambda r: (r["domain"], r["scenario_id"], ARMS.index(r["arm"])))
    ab.write_scores(out / "scores.csv", rows)
    groups = {}
    for row in rows:
        groups.setdefault(row["domain"], {}).setdefault(row["scenario_id"], {})[row["arm"]] = row
    summary = {"protocol": PROTOCOL, "primary_endpoint": "process_coverage", "domains": {}, "errors": errors}
    lines = ["# Domain Taxonomy Ablation", "", "Primary endpoint: structured seven-category lexical process coverage.", "",
             "Remaining-gap text and ID-only automation-opportunity matching are excluded; semantic correctness is not established."]
    for domain in ("semiconductor_work", "childcare"):
        complete = {sid: arms for sid, arms in groups.get(domain, {}).items() if all(a in arms for a in ARMS)}
        means = {arm: {k: statistics.mean(arms[arm][k] for arms in complete.values()) if complete else None
                       for k in ("process_coverage", "legacy_coverage", "structured_coverage", "answer_words",
                                 "input_tokens", "output_tokens", *PROCESS_CATEGORIES)} for arm in ARMS}
        contrasts = {}
        for lhs, rhs in (("common", "generic"), ("domain", "common"), ("domain", "generic")):
            deltas = [arms[lhs]["process_coverage"] - arms[rhs]["process_coverage"] for arms in complete.values()]
            contrasts[f"{lhs}_minus_{rhs}"] = {"mean_difference": statistics.mean(deltas) if deltas else None,
                "wins": sum(d > 1e-9 for d in deltas), "ties": sum(abs(d) <= 1e-9 for d in deltas),
                "losses": sum(d < -1e-9 for d in deltas)}
        summary["domains"][domain] = {"expected_scenarios": 8, "complete_scenarios": len(complete),
                                      "means": means, "contrasts": contrasts}
        lines += ["", f"## {domain}", "", f"Complete scenarios: {len(complete)}/8", "",
                  "| Scenario | Generic | Common | Domain |", "|---|---:|---:|---:|"]
        for sid, arms in sorted(complete.items()):
            lines.append("| " + sid + " | " + " | ".join(f"{arms[a]['process_coverage']:.4f}" for a in ARMS) + " |")
        if complete:
            lines.append("| Mean | " + " | ".join(f"{means[a]['process_coverage']:.4f}" for a in ARMS) + " |")
            lines += ["", "| Metric | Generic | Common | Domain |", "|---|---:|---:|---:|"]
            for k in ("legacy_coverage", "structured_coverage", "answer_words", *PROCESS_CATEGORIES):
                lines.append("| " + k + " | " + " | ".join(f"{means[a][k]:.4f}" for a in ARMS) + " |")
    lines += ["", "## Interpretation Limits", "",
              "One repeat, eight synthetic cases per domain. Semiconductor-work includes engineering documentation "
              "and office coordination, not only verification. Its generic/common outputs are reused exactly from the "
              "previous development pilot; domain-conditioned outputs and all childcare outputs are newly generated.", "",
              "Childcare data and all prompts were frozen before these new API outcomes, but were AI-assisted designs "
              "made after inspecting previous experiments. This is not an independent human-authored or population-representative benchmark.", "",
              "Domain prompts append contextual explanations to the same 12 common categories. They add prompt tokens "
              "and domain vocabulary, not category count. There is no length-matched irrelevant-context control.", "",
              "Childcare references explicitly contain fictional frequency/effort/access constraints; older engineering "
              "references often lack them. Structural counts and reference construction also differ. Compare methods "
              "within domains; do not interpret cross-domain absolute scores as task difficulty or a causal domain effect.", "",
              "Primary process coverage excludes remaining_gaps and the legacy automation-opportunity category because "
              "that matcher can match an activity ID anywhere in JSON. It still uses a lexical matcher over the retained "
              "workflow/opportunity text, can count unsupported facts, and does not measure precision or automation quality. "
              "Legacy scores are retained for transparency, not substituted silently into paper tables.", "",
              "Question count is six and oracle answers are limited to 80 words each in all conditions, but actual "
              "information content and question breadth can vary. Oracle factuality and real caregiver experience are not validated.", "",
              "No manuscript, historical result table, or published anonymous repository was modified."]
    ab.save(out / "summary.json", summary)
    (out / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(ab.dump(summary), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "data/ablation/domain_taxonomy_v1")
    parser.add_argument("--baseline", type=Path, default=ROOT / "data/ablation/generic_questions_v1")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--report-only", action="store_true")
    args = parser.parse_args()
    if args.workers < 1:
        parser.error("workers must be positive")
    base = ab.read(args.baseline / "manifest.json")
    if base["protocol"] != ab.PROTOCOL or base["repeats"] != 1:
        parser.error("Expected the one-repeat baseline protocol")
    paths = [ROOT / "data/scenarios.json", ROOT / "data/scenarios_childcare.json", ROOT / "data/domain_taxonomies.json"]
    if sha(paths[0]) != base["dataset_sha256"] or sha(ROOT / "scripts/score_runs.py") != base["scorer_sha256"]:
        parser.error("Original dataset or scorer differs from the baseline")
    for key in ("model", "questions", "temperature", "max_tokens"):
        setattr(args, key, base[key])
    semi = list(ab.load_scenarios(paths[0]).values())
    child = list(ab.load_scenarios(paths[1]).values())
    validate_childcare(child)
    profiles = ab.read(paths[2])
    if profiles["common_categories"] != ab.TAXONOMY.split(", "):
        parser.error("Common categories differ from original prototype")
    for profile in profiles["domains"].values():
        if set(profile) != set(profiles["common_categories"]):
            parser.error("Domain profile changes the category set")
    source_files = [args.baseline / "runs" / "r01" / s["id"] / arm / f"{stage}.json"
                    for s in semi for arm in ab.ARMS for stage in ("questions", "oracle_answers", "update")]
    config = {"protocol": PROTOCOL, "primary_endpoint": "structured_process_coverage_seven_categories",
              "repeats": 1, "source_manifest": base,
              "input_hashes": {str(p.relative_to(ROOT)): sha(p) for p in paths + source_files},
              "implementation": {p.name: sha(p) for p in (Path(__file__), Path(ab.__file__), ROOT / "scripts/score_runs.py")}}
    print("16 scenarios x 3 arms x 3 stages = 144 responses; 48 baseline responses reused, 96 new calls before retries.", flush=True)
    if args.dry_run:
        print("Datasets, omission pointers, IDs, taxonomies, baseline fingerprints and settings verified.")
        return 0
    manifest = args.out / "manifest.json"
    if manifest.exists() and ab.read(manifest)["config"] != config:
        parser.error("Experiment changed; use a new output directory")
    rows, errors = [], []
    if args.report_only:
        for domain, scenarios in (("semiconductor_work", semi), ("childcare", child)):
            for s in scenarios:
                for arm in ARMS:
                    f = args.out / "runs" / domain / s["id"] / arm / "evaluation.json"
                    if f.exists():
                        rows.append(ab.read(f)["row"])
                    else:
                        errors.append({"domain": domain, "scenario_id": s["id"], "arm": arm, "error": "Missing evaluation"})
    else:
        key = ab.load_key()
        if not key:
            parser.error("ANTHROPIC_API_KEY is missing")
        if not manifest.exists():
            ab.save(manifest, {"frozen_at": datetime.now(timezone.utc).isoformat(), "config": config})
        tasks = [(domain, s) for pair in zip(semi, child) for domain, s in zip(("semiconductor_work", "childcare"), pair)]
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = [pool.submit(run_scenario, domain, s, args, profiles, key) for domain, s in tasks]
            for future in as_completed(futures):
                new_rows, new_errors = future.result()
                rows.extend(new_rows)
                errors.extend(new_errors)
    summarize(args.out, rows, errors)
    return 1 if errors or len(rows) != 48 else 0


if __name__ == "__main__":
    raise SystemExit(main())
