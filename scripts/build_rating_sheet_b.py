#!/usr/bin/env python3
"""Build the blinded rating sheet for the OUTPUT-side sample.

The forward sheet (build_rating_sheet.py) shows a reference item and asks whether the
reconstruction expresses it. That question is meaningless here: every item in this
sample is in the reconstruction by construction. What is in doubt is what it rests on,
so the questions change.

The rater sees the initial description, the questions and answers, and the
reconstruction -- and NOT the reference workflow. The reference is what the item is
being judged independently of: the question is whether the run's own inputs support
the element, not whether it happens to match a gold model.

Writes a single self-contained HTML file. No install, no network; answers are kept in
the browser and exported as CSV.
"""
import argparse
import csv
import json
import random
from pathlib import Path

import run_provenance as rp
import run_question_ablation as ab

ROOT = ab.ROOT
LAYOUT = {
    "generic_questions_v1": "runs/r01/{sid}/{arm}",
    "coordinated_questions_v1": "runs/{sid}",
    "domain_taxonomy_v1": "runs/{dom}/{sid}/{arm}",
}


def run_directory(corpus, domain, scenario, arm):
    return ROOT / "data/ablation" / corpus / LAYOUT[corpus].format(sid=scenario, arm=arm, dom=domain)


def run_payload(corpus, domain, scenario, arm, scenarios):
    paths, _ = rp.resolve(run_directory(corpus, domain, scenario, arm))
    if not paths:
        raise FileNotFoundError(f"{corpus}/{domain}/{scenario}/{arm}")
    answers = rp.payload(ab.read(paths["oracle_answers"]))
    workflow = rp.payload(ab.read(paths["update"]))["workflow"]
    return {
        "description": scenarios[domain][scenario]["initial_description"],
        "activities": [{"id": a.get("id", ""), "name": a.get("name", ""), "actor": a.get("actor", ""),
                        "system": a.get("system", ""),
                        "inputs": ", ".join(a.get("inputs") or []),
                        "outputs": ", ".join(a.get("outputs") or [])}
                       for a in workflow.get("activities", []) if isinstance(a, dict)],
        "decisions": [{"id": d.get("id", ""), "condition": d.get("condition", "")}
                      for d in workflow.get("decisions", []) if isinstance(d, dict)],
        "exceptions": [e.get("description", "") if isinstance(e, dict) else str(e)
                       for e in workflow.get("exceptions", [])],
        "answers": [{"q": a.get("question", ""), "a": a.get("answer", "")}
                    for a in answers.get("answers", []) if isinstance(a, dict)],
    }


TEMPLATE = """<!doctype html><html lang="ko"><head><meta charset="utf-8">
<title>생성 요소 근거 채점 시트</title><style>
*{box-sizing:border-box}body{margin:0;font:15px/1.65 -apple-system,"Apple SD Gothic Neo",sans-serif;color:#1b1b1b;background:#f6f6f4}
header{position:sticky;top:0;background:#fff;border-bottom:1px solid #d8d8d3;padding:12px 20px;z-index:5;display:flex;gap:16px;align-items:center;flex-wrap:wrap}
header h1{font-size:16px;margin:0;font-weight:600}
input[type=text]{padding:6px 9px;border:1px solid #c9c9c3;border-radius:5px;font:inherit}
button{padding:7px 13px;border:1px solid #2f5d50;background:#2f5d50;color:#fff;border-radius:5px;font:inherit;cursor:pointer}
button.ghost{background:#fff;color:#2f5d50}
main{max-width:1000px;margin:0 auto;padding:22px}
.intro{background:#fff;border:1px solid #e2e2dc;border-radius:8px;padding:18px 22px;margin-bottom:26px}
.intro h2{font-size:15px;margin:18px 0 6px}.intro h2:first-child{margin-top:0}
.intro li{margin:3px 0}
.intro .warn{background:#fbf6ec;border-left:3px solid #c9a227;padding:9px 13px;margin:10px 0}
.run{background:#fff;border:1px solid #e2e2dc;border-radius:8px;margin-bottom:26px;overflow:hidden}
.run>summary{padding:12px 18px;cursor:pointer;background:#eef1ef;font-weight:600;font-size:14px}
.ctx{padding:14px 18px;border-bottom:1px solid #eee;font-size:13.5px}
.ctx h3{font-size:13px;margin:14px 0 6px;color:#555;letter-spacing:.02em}
.ctx h3:first-child{margin-top:0}
.desc{background:#f7f7f4;border-left:3px solid #cfd6d2;padding:9px 13px}
table{border-collapse:collapse;width:100%;font-size:13px}
td,th{border:1px solid #e6e6e0;padding:5px 8px;text-align:left;vertical-align:top}
th{background:#f4f4f0;font-weight:600}
.qa{margin:9px 0;padding-left:11px;border-left:3px solid #dfe5e2}
.qa b{font-weight:600;color:#444}
.ko{color:#7a7a72;font-size:12.5px;display:block;margin-top:2px}
body.nk .ko{display:none}
.item{padding:16px 18px;border-top:2px solid #2f5d50}
.item .no{display:inline-block;background:#2f5d50;color:#fff;border-radius:4px;padding:1px 8px;font-size:12px;margin-right:8px}
.target{font-size:17px;font-weight:600;margin:9px 0 2px}
.gloss{color:#6a6a63;font-size:13.5px;margin-bottom:12px}
fieldset{border:1px solid #e2e2dc;border-radius:6px;margin:10px 0;padding:10px 13px}
fieldset.off{opacity:.42}
legend{font-size:13.5px;font-weight:600;padding:0 5px}
label.opt{display:block;padding:3px 0;cursor:pointer}
label.opt .hint{color:#6a6a63;font-size:13px}
.done{outline:3px solid #cfe3d8}
footer{max-width:1000px;margin:0 auto 60px;padding:0 22px;color:#6a6a63;font-size:13px}
</style></head><body>
<header><h1>생성 요소 근거 채점 시트</h1>
<label>채점자 ID <input type="text" id="rater" placeholder="예: R4" size="8"></label>
<span id="prog"></span>
<button onclick="save()">CSV 내려받기</button>
<button class="ghost" onclick="copyCsv()">CSV 복사</button>
<label style="font-size:13px"><input type="checkbox" id="nk" onchange="document.body.classList.toggle('nk',this.checked)"> 국문 숨기기</label></header>
<main>
<div class="intro">
<h2>무엇을 하는 작업인가</h2>
<p>LLM이 담당자와의 문답을 통해 업무 프로세스를 재구성했습니다. 이 시트는 <b>재구성 결과에 적혀 있는
요소 하나하나가 무엇에 근거한 것인지</b>를 사람이 판정합니다. 항목은 모두 재구성 결과에 들어 있습니다.
들어 있는지가 아니라 <b>무엇을 근거로 들어왔는지</b>가 질문입니다.</p>
<div class="warn"><b>판정하지 말아야 할 것 세 가지.</b> ① 현실에서 맞는 내용인지 ② 정답 모델과
일치하는지 ③ 표현이 좋은지. 셋 다 다른 질문이며, 섞이면 채점이 무너집니다. 오직
<b>위에 주어진 초기 설명과 답변만</b>을 근거로 보세요.</div>
<h2>진행 방법</h2>
<ul>
<li>묶음마다 <b>초기 설명</b>, <b>담당자 질문·답변</b>, <b>재구성 결과</b>가 위에 제시됩니다.</li>
<li>W1~W3은 <b>연습 문항</b>입니다. 기준을 잡는 용도이며 분석에 쓰지 않습니다.</li>
<li><b>다른 채점자와 상의하지 마세요.</b> 독립 채점이어야 일치도를 계산할 수 있습니다.</li>
<li>판정 기준은 <b>영문 원문</b>입니다. 회색 국문이 있다면 기계 번역된 참고용이며 판정 근거가 아닙니다.</li>
<li>중간에 닫아도 브라우저에 자동 저장됩니다. 끝나면 CSV를 내려받아 전달해 주세요.</li>
</ul>
<h2>문항 2가 헷갈릴 때</h2>
<ul>
<li><b>(a) 다른 표현</b> vs <b>(b) 구체화</b>: 답변에 "테스트 결과를 확인한다"가 있고 요소가
"Verify test output"이면 <b>(a)</b>. 답변에 없지만 "Pack the bag" 활동이 있어서 그 산출물로
"packed bag"이 생겼다면 <b>(b)</b> — 주어진 것에서 기계적으로 따라옵니다.</li>
<li><b>(b) 구체화</b> vs <b>(e) 새 내용</b>: 주어진 내용만 보고 <b>당연히 그렇게 되는가</b>를
물으세요. "승인 단계가 있다"는 말이 어디에도 없는데 승인 활동이 생겼다면 <b>(e)</b>입니다.</li>
<li>모델이 "Unknown", "Unspecified"처럼 <b>모른다고 밝힌</b> 자리표시자는 <b>(c)</b>,
"~에 대한 경로가 정의되어 있지 않다"처럼 <b>공백을 신고</b>한 것은 <b>(d)</b>입니다.</li>
<li>애매하면 문항 1에서 "판단 불가"를 고르세요. 억지로 고르지 않는 편이 낫습니다.</li>
</ul>
</div>
<div id="sheet"></div>
</main>
<footer>채점 항목 __N__ (연습 3 포함). 자동 저장 위치: 이 브라우저.</footer>
<script id="data" type="application/json">__DATA__</script>
<script>
const DATA = JSON.parse(document.getElementById('data').textContent);
const KEY = 'rating_output_v1';
const Q = [
 {id:'q1', text:'문항 1. 근거 — 이 요소가 초기 설명이나 담당자 답변으로 뒷받침됩니까?',
  opts:[['supported','뒷받침됨 — 설명이나 답변에 내용이 있다'],
        ['partial','일부만 — 비슷한 내용은 있으나 이 요소까지는 아니다'],
        ['unsupported','뒷받침 안 됨 — 설명에도 답변에도 없다'],
        ['unclear','판단 불가']]},
 {id:'q2', text:'문항 2. 성격 — 이것은 무엇입니까?',
  opts:[['paraphrase','(a) 설명·답변에 있는 것을 다르게 표현한 것'],
        ['derivation','(b) 주어진 내용에서 당연히 따라오는 구체화'],
        ['abstention','(c) 모델이 모른다고 밝힌 자리표시자'],
        ['declared_gap','(d) 모델이 "정의되어 있지 않다"고 신고한 공백'],
        ['addition','(e) 주어진 어디에도 없는 새 내용']]},
 {id:'q3', text:'문항 3. (문항 2가 (e)일 때만) 분석가가 이것을 담당자에게서 도출된 사실로 오해할 수 있습니까?',
  opts:[['mistakable','예 — 도출된 사실처럼 읽힌다'],
        ['evident','아니오 — 모델의 제안임이 드러난다']]}
];
let state = JSON.parse(localStorage.getItem(KEY) || '{}');
const esc = s => (s||'').replace(/[&<>]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
const KO = DATA.gloss || {};
const bi = s => { const k = KO[(s||'').trim()];
  return esc(s) + (k ? `<span class="ko">${esc(k)}</span>` : ''); };

function ctxHtml(r){
  let h = '<div class="ctx"><h3>초기 설명 · Initial description</h3>'
        + `<div class="desc">${bi(r.description)}</div>`;
  h += '<h3>담당자 질문·답변 · Questions and answers</h3>';
  r.answers.forEach(qa => h += `<div class="qa"><b>Q.</b> ${bi(qa.q)}<b>A.</b> ${bi(qa.a)}</div>`);
  h += '<h3>재구성된 프로세스 · Reconstructed process</h3><table>'
     + '<tr><th>ID</th><th>활동 Activity</th><th>담당 Actor</th><th>시스템 System</th>'
     + '<th>입력 Inputs</th><th>산출 Outputs</th></tr>';
  r.activities.forEach(a => h += `<tr><td>${esc(a.id)}</td><td>${bi(a.name)}</td><td>${bi(a.actor)}</td>`
     + `<td>${bi(a.system)}</td><td>${bi(a.inputs)}</td><td>${bi(a.outputs)}</td></tr>`);
  h += '</table>';
  if (r.decisions.length){ h += '<h3>분기 조건 · Decisions</h3><table>';
    r.decisions.forEach(d => h += `<tr><td>${esc(d.id)}</td><td>${bi(d.condition)}</td></tr>`); h += '</table>'; }
  if (r.exceptions.length){ h += '<h3>예외 · Exceptions</h3><table>';
    r.exceptions.forEach(e => h += `<tr><td>${bi(e)}</td></tr>`); h += '</table>'; }
  return h + '</div>';
}

function itemHtml(it){
  let h = `<div class="item" id="box_${it.item_no}"><span class="no">${it.item_no}</span>`;
  h += `<span style="color:#6a6a63;font-size:13px">${esc(it.category)}</span>`;
  h += `<div class="target">${esc(it.item)}</div><div class="gloss">${esc(it.gloss)}</div>`;
  Q.forEach(q => {
    const off = q.id === 'q3' && (state[it.item_no]||{}).q2 !== 'addition';
    h += `<fieldset id="fs_${it.item_no}_${q.id}"${off ? ' class="off"' : ''}><legend>${q.text}</legend>`;
    q.opts.forEach(([v, label]) => {
      const on = (state[it.item_no]||{})[q.id] === v ? ' checked' : '';
      h += `<label class="opt"><input type="radio" name="${it.item_no}_${q.id}" value="${v}"${on}
            onchange="mark('${it.item_no}','${q.id}',this.value)"> ${label}</label>`;
    });
    h += '</fieldset>';
  });
  return h + '</div>';
}

function render(){
  document.getElementById('sheet').innerHTML = DATA.runs.map((r, i) =>
    `<details class="run"${i===0?' open':''}><summary>${esc(r.title)} — 채점 항목 ${r.items.length}개</summary>`
    + ctxHtml(r) + r.items.map(itemHtml).join('') + '</details>').join('');
  DATA.runs.flatMap(r => r.items).forEach(it => paint(it.item_no));
  progress();
}
function complete(a){ return a && a.q1 && a.q2 && (a.q2 !== 'addition' || a.q3); }
function mark(no, q, v){
  state[no] = state[no] || {}; state[no][q] = v;
  if (q === 'q2' && v !== 'addition') delete state[no].q3;
  localStorage.setItem(KEY, JSON.stringify(state));
  const fs = document.getElementById('fs_' + no + '_q3');
  if (fs) fs.classList.toggle('off', (state[no]||{}).q2 !== 'addition');
  paint(no); progress();
}
function paint(no){
  document.getElementById('box_' + no).classList.toggle('done', complete(state[no]));
}
function progress(){
  const items = DATA.runs.flatMap(r => r.items).filter(i => !i.item_no.startsWith('W'));
  const done = items.filter(i => complete(state[i.item_no])).length;
  document.getElementById('prog').textContent = `진행 ${done} / ${items.length}`;
}
function csv(){
  const rater = (document.getElementById('rater').value || 'unknown').trim();
  const lines = ['rater,item_no,q1_support,q2_nature,q3_mistakable'];
  DATA.runs.flatMap(r => r.items).forEach(it => {
    const a = state[it.item_no] || {};
    lines.push([rater, it.item_no, a.q1||'', a.q2||'', a.q3||''].join(','));
  });
  return lines.join('\\n');
}
function save(){
  const blob = new Blob([csv()], {type:'text/csv;charset=utf-8'});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `ratings_output_${(document.getElementById('rater').value||'unknown').trim()}.csv`;
  a.click();
}
function copyCsv(){ navigator.clipboard.writeText(csv()).then(() => alert('CSV를 클립보드에 복사했습니다.')); }
render();
</script></body></html>"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dir", type=Path, default=ROOT / "data/ablation/human_eval_output_v1")
    parser.add_argument("--seed", type=int, default=20261111)
    args = parser.parse_args()

    rows = list(csv.DictReader((args.dir / "sample.csv").open(encoding="utf-8")))
    scenarios = {domain: ab.load_scenarios(ROOT / path) for domain, path in rp.DATASETS.items()}
    item_gloss_path = args.dir / "item_gloss_ko.json"
    item_gloss = json.loads(item_gloss_path.read_text(encoding="utf-8")) if item_gloss_path.exists() else {}
    generator = random.Random(args.seed)

    grouped = {}
    for row in rows:
        grouped.setdefault((row["corpus"], row["domain"], row["scenario_id"], row["arm"]), []).append(row)

    warmup_runs, scored_runs = [], []
    for key, members in grouped.items():
        payload = run_payload(*key, scenarios)
        items = [{"item_no": m["item_no"], "category": m["category"], "item": m["item"],
                  "gloss": item_gloss.get(m["item"], "")} for m in members]
        generator.shuffle(items)
        # The rater sees an opaque title: no scenario name, arm, stratum or label.
        block = {"title": "묶음", **payload, "items": items}
        (warmup_runs if any(i["item_no"].startswith("W") for i in items) else scored_runs).append(block)
    generator.shuffle(scored_runs)
    runs = warmup_runs + scored_runs
    for index, block in enumerate(runs, start=1):
        block["title"] = f"묶음 {index:02d}"

    content_gloss_path = args.dir / "content_gloss_ko.json"
    content_gloss = json.loads(content_gloss_path.read_text(encoding="utf-8")) if content_gloss_path.exists() else {}
    html = (TEMPLATE.replace("__DATA__", json.dumps({"runs": runs, "gloss": content_gloss}, ensure_ascii=False))
                    .replace("__N__", str(len(rows))))
    out = args.dir / "sheet_b_ko.html"
    out.write_text(html, encoding="utf-8")
    print(f"{out}  ({len(runs)} blocks, {len(rows)} items)")


if __name__ == "__main__":
    main()
