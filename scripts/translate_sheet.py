#!/usr/bin/env python3
"""Translate the rating sheet's English content into Korean for comprehension support.

The English text stays the judged material; the Korean is a reading aid rendered
beneath it. Every string is translated once and cached, so re-runs cost nothing.
"""
import argparse
import json
import re
from pathlib import Path

import run_question_ablation as ab

ROOT = ab.ROOT
BATCH = 25
PROMPT = """Translate each numbered English string into Korean for a process-analysis rating sheet.

Rules:
- Keep the translation literal and compact; this is a reading aid, not a rewrite.
- Preserve identifiers, system names and acronyms as they appear.
- Activity names read as actions ("~한다"); nouns stay nouns.
- Return JSON only: {"translations": [{"n": 1, "ko": "..."}]}
- Return exactly one entry per input number, in order.

Strings:
"""


def collect(data):
    strings = []
    for run in data["runs"]:
        for activity in run["activities"]:
            strings += [activity["name"], activity["actor"], activity["system"]]
        strings += [d["condition"] for d in run["decisions"]]
        strings += run["exceptions"]
        for qa in run["answers"]:
            strings += [qa["q"], qa["a"]]
    seen, unique = set(), []
    for text in strings:
        text = (text or "").strip()
        if text and text not in seen:
            seen.add(text)
            unique.append(text)
    return unique


def translate(batch, args, api_key):
    listing = "\n".join(f"{index + 1}. {text}" for index, text in enumerate(batch))
    request = {"model": args.model, "max_tokens": 8000, "temperature": 0,
               "messages": [{"role": "user", "content": PROMPT + listing}]}
    payload = ab.call_api(request, api_key)
    raw = "\n".join(b.get("text", "") for b in payload.get("content", []) if b.get("type") == "text")
    parsed = ab.parse_response(raw)
    out = {}
    for entry in parsed["translations"]:
        index = int(entry["n"]) - 1
        if 0 <= index < len(batch):
            out[batch[index]] = str(entry["ko"]).strip()
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dir", type=Path, default=ROOT / "data/ablation/human_eval_v1")
    parser.add_argument("--model", default="claude-sonnet-4-6")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    html = (args.dir / "sheet_ko.html").read_text(encoding="utf-8")
    data = json.loads(re.search(r'<script id="data" type="application/json">(.*?)</script>', html, re.S).group(1))
    unique = collect(data)

    cache_path = args.dir / "content_gloss_ko.json"
    cache = json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.exists() else {}
    todo = [text for text in unique if text not in cache]
    print(f"{len(unique)} unique strings, {len(todo)} to translate, {len(unique) - len(todo)} cached.")
    if args.dry_run or not todo:
        return

    api_key = ab.load_key()
    if not api_key:
        parser.error("ANTHROPIC_API_KEY is missing")
    for start in range(0, len(todo), BATCH):
        batch = todo[start:start + BATCH]
        try:
            cache.update(translate(batch, args, api_key))
        except (RuntimeError, ValueError, KeyError, TypeError) as exc:
            print(f"  batch at {start} failed: {exc}", flush=True)
            continue
        cache_path.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"  {min(start + BATCH, len(todo))}/{len(todo)}", flush=True)
    missing = [text for text in unique if text not in cache]
    print(f"Done. {len(cache)} cached, {len(missing)} still missing.")


if __name__ == "__main__":
    main()
