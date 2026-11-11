#!/usr/bin/env python3
"""Build a blinded bilingual rating sheet from the sampled items."""
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


def run_payload(corpus, domain, scenario, arm):
    paths, _ = rp.resolve(run_directory(corpus, domain, scenario, arm))
    if not paths:
        raise FileNotFoundError(f"{corpus}/{domain}/{scenario}/{arm}")
    answers = rp.payload(ab.read(paths["oracle_answers"]))
    workflow = rp.payload(ab.read(paths["update"]))["workflow"]
    return {
        "activities": [{"id": a.get("id", ""), "name": a.get("name", ""), "actor": a.get("actor", ""),
                        "system": a.get("system", "")}
                       for a in workflow.get("activities", []) if isinstance(a, dict)],
        "decisions": [{"id": d.get("id", ""), "condition": d.get("condition", "")}
                      for d in workflow.get("decisions", []) if isinstance(d, dict)],
        "exceptions": [e.get("description", "") if isinstance(e, dict) else str(e)
                       for e in workflow.get("exceptions", [])],
        "answers": [{"q": a.get("question", ""), "a": a.get("answer", "")}
                    for a in answers.get("answers", []) if isinstance(a, dict)],
    }


TEMPLATE = """<!doctype html><html lang="ko"><head><meta charset="utf-8">
<title>도출 결과 채점 시트</title><style>
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
.run{background:#fff;border:1px solid #e2e2dc;border-radius:8px;margin-bottom:26px;overflow:hidden}
.run>summary{padding:12px 18px;cursor:pointer;background:#eef1ef;font-weight:600;font-size:14px}
.ctx{padding:14px 18px;border-bottom:1px solid #eee;font-size:13.5px}
.ctx h3{font-size:13px;margin:14px 0 6px;color:#555;letter-spacing:.02em}
.ctx h3:first-child{margin-top:0}
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
legend{font-size:13.5px;font-weight:600;padding:0 5px}
label.opt{display:block;padding:3px 0;cursor:pointer}
.done{outline:3px solid #cfe3d8}
footer{max-width:1000px;margin:0 auto 60px;padding:0 22px;color:#6a6a63;font-size:13px}
</style></head><body>
<header><h1>도출 결과 채점 시트</h1>
<label>채점자 ID <input type="text" id="rater" placeholder="예: R1" size="8"></label>
<span id="prog"></span>
<button onclick="save()">CSV 내려받기</button>
<button class="ghost" onclick="copyCsv()">CSV 복사</button>
<label style="font-size:13px"><input type="checkbox" id="nk" onchange="document.body.classList.toggle('nk',this.checked)"> 국문 숨기기</label></header>
<main>
<div class="intro">
<h2>무엇을 하는 작업인가</h2>
<p>LLM이 담당자와의 문답을 통해 업무 프로세스를 재구성했습니다. 이 시트는 <b>레퍼런스 항목 하나하나가
재구성 결과에 실제로 반영되었는지</b>를 사람이 판정하는 것입니다. 자동 채점기가 판정하지 못하는
구간을 확인하는 것이 목적입니다.</p>
<h2>진행 방법</h2>
<ul>
<li>항목마다 <b>재구성 결과</b>와 <b>담당자 답변</b>이 위에 함께 제시됩니다. 읽고 세 문항에 답하세요.</li>
<li>W1~W3은 <b>연습 문항</b>입니다. 기준을 잡는 용도이며 분석에 쓰지 않습니다.</li>
<li><b>다른 채점자와 상의하지 마세요.</b> 독립 채점이어야 일치도를 계산할 수 있습니다.</li>
<li>판정 기준은 <b>영문 원문</b>입니다. 회색 국문은 <b>기계 번역된 참고용</b>이며 판정 근거가 아닙니다.
번역이 원문과 어긋나 보이면 영문을 따르세요. 오른쪽 위에서 국문을 숨길 수 있습니다.</li>
<li>중간에 닫아도 브라우저에 자동 저장됩니다. 끝나면 CSV를 내려받아 전달해 주세요.</li>
</ul>
<h2>판정 요령</h2>
<ul>
<li><b>문항 1</b>이 이 조사의 핵심입니다. 표현이 달라도 같은 뜻이면 두 번째 선택지를 고르세요.
예: "Check result validity" vs "Verify Test Output" → 표현만 다름.</li>
<li><b>문항 2</b>는 그 사실이 엉뚱한 활동이나 담당자에게 붙어 있지 않은지 봅니다.</li>
<li><b>문항 3</b>은 담당자 답변에 근거가 있는지만 봅니다. 사실인지 여부가 아니라 <b>답변에 나오는지</b>입니다.</li>
<li>애매하면 "판단 불가"를 고르세요. 억지로 고르지 않는 편이 낫습니다.</li>
</ul>
</div>
<div id="sheet"></div>
</main>
<footer>문항 수 __N__ (연습 3 포함). 자동 저장 위치: 이 브라우저.</footer>
<script id="data" type="application/json">__DATA__</script>
<script>
const DATA = JSON.parse(document.getElementById('data').textContent);
const KEY = 'rating_v1';
const Q = [
 {id:'q1', text:'문항 1. 이 사실이 재구성 결과에 표현되어 있습니까?',
  opts:[['present','있음 — 거의 같은 표현으로 나온다'],['paraphrase','표현만 다르고 같은 뜻이다'],['absent','없음 — 어디에도 없다']]},
 {id:'q2', text:'문항 2. 올바른 활동·담당자에 붙어 있습니까? (문항 1이 "없음"이면 건너뛰세요)',
  opts:[['correct','맞게 붙어 있다'],['wrong','엉뚱한 곳에 붙어 있다'],['unclear','판단 불가']]},
 {id:'q3', text:'문항 3. 이 내용이 담당자 답변으로 뒷받침됩니까?',
  opts:[['supported','답변에 나온다'],['unsupported','답변에 없다'],['unclear','판단 불가']]}
];
let state = JSON.parse(localStorage.getItem(KEY) || '{}');
const esc = s => (s||'').replace(/[&<>]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
const KO = DATA.gloss || {};
const bi = s => { const k = KO[(s||'').trim()];
  return esc(s) + (k ? `<span class="ko">${esc(k)}</span>` : ''); };

function ctxHtml(r){
  let h = '<div class="ctx"><h3>재구성된 프로세스 · Reconstructed process</h3><table><tr><th>ID</th><th>활동 Activity</th><th>담당 Actor</th><th>시스템 System</th></tr>';
  r.activities.forEach(a => h += `<tr><td>${esc(a.id)}</td><td>${bi(a.name)}</td><td>${bi(a.actor)}</td><td>${bi(a.system)}</td></tr>`);
  h += '</table>';
  if (r.decisions.length){ h += '<h3>분기 조건 · Decisions</h3><table>';
    r.decisions.forEach(d => h += `<tr><td>${esc(d.id)}</td><td>${bi(d.condition)}</td></tr>`); h += '</table>'; }
  if (r.exceptions.length){ h += '<h3>예외 · Exceptions</h3><table>';
    r.exceptions.forEach(e => h += `<tr><td>${bi(e)}</td></tr>`); h += '</table>'; }
  h += '<h3>담당자 답변 · Expert answers</h3>';
  r.answers.forEach(qa => h += `<div class="qa"><b>Q.</b> ${bi(qa.q)}<b>A.</b> ${bi(qa.a)}</div>`);
  return h + '</div>';
}

function itemHtml(it){
  let h = `<div class="item" id="box_${it.item_no}"><span class="no">${it.item_no}</span>`;
  h += `<span style="color:#6a6a63;font-size:13px">${esc(it.category)}</span>`;
  h += `<div class="target">${esc(it.item)}</div><div class="gloss">${esc(it.gloss)}</div>`;
  Q.forEach(q => {
    h += `<fieldset><legend>${q.text}</legend>`;
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
function mark(no, q, v){
  state[no] = state[no] || {}; state[no][q] = v;
  localStorage.setItem(KEY, JSON.stringify(state)); paint(no); progress();
}
function paint(no){
  const a = state[no] || {};
  const complete = a.q1 && a.q3 && (a.q1 === 'absent' || a.q2);
  document.getElementById('box_' + no).classList.toggle('done', !!complete);
}
function progress(){
  const items = DATA.runs.flatMap(r => r.items).filter(i => !i.item_no.startsWith('W'));
  const done = items.filter(i => { const a = state[i.item_no]||{};
    return a.q1 && a.q3 && (a.q1==='absent' || a.q2); }).length;
  document.getElementById('prog').textContent = `진행 ${done} / ${items.length}`;
}
function csv(){
  const rater = (document.getElementById('rater').value || 'unknown').trim();
  const lines = ['rater,item_no,q1_present,q2_attachment,q3_support'];
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
  a.download = `ratings_${(document.getElementById('rater').value||'unknown').trim()}.csv`;
  a.click();
}
function copyCsv(){ navigator.clipboard.writeText(csv()).then(() => alert('CSV를 클립보드에 복사했습니다.')); }
render();
</script></body></html>"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dir", type=Path, default=ROOT / "data/ablation/human_eval_v1")
    parser.add_argument("--seed", type=int, default=20261002)
    args = parser.parse_args()

    rows = list(csv.DictReader((args.dir / "sample.csv").open(encoding="utf-8")))
    gloss_file = args.dir / "item_gloss_ko.json"
    gloss = json.loads(gloss_file.read_text(encoding="utf-8")) if gloss_file.exists() else {}
    generator = random.Random(args.seed)

    grouped = {}
    for row in rows:
        key = (row["corpus"], row["domain"], row["scenario_id"], row["arm"])
        grouped.setdefault(key, []).append(row)

    warmup_runs, scored_runs = [], []
    for key, members in grouped.items():
        payload = run_payload(*key)
        items = [{"item_no": m["item_no"], "category": m["category"], "item": m["item"],
                  "gloss": gloss.get(m["item"], "")} for m in members]
        generator.shuffle(items)
        # The rater sees an opaque title: no scenario name, arm or label.
        block = {"title": "묶음 " + members[0]["item_no"][0] + str(len(scored_runs) + len(warmup_runs) + 1),
                 **payload, "items": items}
        (warmup_runs if any(i["item_no"].startswith("W") for i in items) else scored_runs).append(block)
    generator.shuffle(scored_runs)
    runs = warmup_runs + scored_runs
    for index, block in enumerate(runs, start=1):
        block["title"] = f"묶음 {index:02d}"

    gloss_path = args.dir / "content_gloss_ko.json"
    content_gloss = json.loads(gloss_path.read_text(encoding="utf-8")) if gloss_path.exists() else {}
    html = TEMPLATE.replace("__DATA__", json.dumps({"runs": runs, "gloss": content_gloss}, ensure_ascii=False)) \
                   .replace("__N__", str(len(rows)))
    out = args.dir / "sheet_ko.html"
    out.write_text(html, encoding="utf-8")
    print(f"{out}  ({len(runs)} blocks, {len(rows)} items)")


if __name__ == "__main__":
    main()
