#!/usr/bin/env python3
"""Convert an elicited workflow JSON into BPMN 2.0 XML and an automation register.

The elicited JSON stays the source of truth; both outputs are regenerated from it.
Layout is computed here so the diagram opens directly in bpmn.io or Camunda Modeler
without a separate auto-layout step. Standard library only.
"""
import argparse
import csv
import json
import re
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr

NS = {
    "bpmn": "http://www.omg.org/spec/BPMN/20100524/MODEL",
    "bpmndi": "http://www.omg.org/spec/BPMN/20100524/DI",
    "dc": "http://www.omg.org/spec/DD/20100524/DC",
    "di": "http://www.omg.org/spec/DD/20100524/DI",
}
START, END = "StartEvent_1", "EndEvent_1"
TASK_W, TASK_H, GATE, EVENT = 150, 80, 50, 36
COL, ROW, LANE_PAD = 200, 120, 60
DATA_W, DATA_H = 36, 50


def load_workflow(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    # Accept either a raw workflow, a pipeline output, or a stored API record.
    if "response" in data:
        text = "\n".join(b.get("text", "") for b in data["response"].get("content", []) if b.get("type") == "text")
        fenced = re.fullmatch(r"\s*```(?:json)?\s*\n(.*?)\n```\s*", text, flags=re.DOTALL)
        data = json.loads(fenced.group(1) if fenced else text)
    return data.get("workflow", data), data.get("automation_opportunities", []), data.get("remaining_gaps", [])


def build_graph(workflow):
    nodes = {}
    for activity in workflow.get("activities", []):
        if not isinstance(activity, dict) or not activity.get("id"):
            continue
        actor = (activity.get("actor") or "Unassigned").strip()
        system = (activity.get("system") or "").strip()
        kind = "serviceTask" if system and system.lower() not in ("unknown", "none", "n/a") else "userTask"
        nodes[activity["id"]] = {"id": activity["id"], "name": activity.get("name", activity["id"]),
                                 "kind": kind, "lane": actor, "system": system,
                                 "inputs": activity.get("inputs", []), "outputs": activity.get("outputs", [])}
    for decision in workflow.get("decisions", []):
        if not isinstance(decision, dict) or not decision.get("id"):
            continue
        nodes[decision["id"]] = {"id": decision["id"], "name": decision.get("condition", decision["id"]),
                                 "kind": "exclusiveGateway", "lane": None, "system": "",
                                 "inputs": [], "outputs": []}

    labels = {}
    for decision in workflow.get("decisions", []):
        # Branches appear either as {"outcome", "next"} objects or as bare outcome strings.
        for branch in decision.get("branches", []) or []:
            if not isinstance(branch, dict):
                continue
            target = branch.get("next") or branch.get("to") or branch.get("target")
            if target:
                labels[(decision["id"], str(target))] = str(branch.get("outcome") or branch.get("condition") or "")

    edges = []
    for dependency in workflow.get("dependencies", []):
        if not isinstance(dependency, dict):
            continue
        source, target = dependency.get("from"), dependency.get("to")
        if source in nodes and target in nodes:
            edges.append({"from": source, "to": target, "label": labels.get((source, target), "")})
    # Branches that name a terminal outcome instead of an activity.
    for (source, target), label in labels.items():
        if source in nodes and target not in nodes and not any(e["from"] == source and e["to"] == END for e in edges):
            edges.append({"from": source, "to": END, "label": label})
    return nodes, edges


def add_events(nodes, edges):
    targets = {e["to"] for e in edges}
    sources = {e["from"] for e in edges}
    entries = [n for n in nodes if n not in targets]
    exits = [n for n in nodes if n not in sources]
    lane = next((nodes[n]["lane"] for n in entries if nodes[n]["lane"]), "Unassigned")
    nodes[START] = {"id": START, "name": "Start", "kind": "startEvent", "lane": lane,
                    "system": "", "inputs": [], "outputs": []}
    nodes[END] = {"id": END, "name": "End", "kind": "endEvent", "lane": lane,
                  "system": "", "inputs": [], "outputs": []}
    for entry in entries:
        edges.insert(0, {"from": START, "to": entry, "label": ""})
    for exit_node in exits:
        edges.append({"from": exit_node, "to": END, "label": ""})
    return nodes, edges


def layer_nodes(nodes, edges):
    outgoing = {}
    incoming = {node: 0 for node in nodes}
    for edge in edges:
        outgoing.setdefault(edge["from"], []).append(edge["to"])
        incoming[edge["to"]] = incoming.get(edge["to"], 0) + 1
    layer = {node: 0 for node in nodes}
    queue, seen = [n for n, c in incoming.items() if c == 0], set()
    while queue:
        node = queue.pop(0)
        if node in seen:
            continue
        seen.add(node)
        for target in outgoing.get(node, []):
            if layer[target] <= layer[node]:          # keep back edges from collapsing the layout
                layer[target] = layer[node] + 1
            queue.append(target)
    return layer


def assign_lanes(nodes, edges, layer):
    predecessors = {}
    for edge in edges:
        predecessors.setdefault(edge["to"], []).append(edge["from"])
    for node in sorted(nodes, key=lambda n: layer[n]):
        if nodes[node]["lane"] is None:
            upstream = [nodes[p]["lane"] for p in predecessors.get(node, []) if nodes[p]["lane"]]
            nodes[node]["lane"] = upstream[0] if upstream else "Unassigned"
    order, lanes = [], []
    for node in sorted(nodes, key=lambda n: layer[n]):
        if nodes[node]["lane"] not in lanes:
            lanes.append(nodes[node]["lane"])
    return lanes


def place(nodes, layer, lanes):
    # Slot each node within its (column, lane) cell, then size every lane to its busiest column
    # so that a crowded lane never spills into the next one.
    slots, used = {}, {}
    for node in sorted(nodes, key=lambda n: (layer[n], nodes[n]["lane"])):
        cell = (layer[node], nodes[node]["lane"])
        slots[node] = used.get(cell, 0)
        used[cell] = slots[node] + 1
    depth = {lane: max([count for (_, lane_name), count in used.items() if lane_name == lane] or [1])
             for lane in lanes}
    geometry, top = {}, LANE_PAD
    for lane in lanes:
        height = depth[lane] * ROW + ROW / 2
        geometry[lane] = (top, height)
        top += height
    for node, info in nodes.items():
        column = layer[node]
        width = {"startEvent": EVENT, "endEvent": EVENT, "exclusiveGateway": GATE}.get(info["kind"], TASK_W)
        height = {"startEvent": EVENT, "endEvent": EVENT, "exclusiveGateway": GATE}.get(info["kind"], TASK_H)
        lane_top, _ = geometry[info["lane"]]
        centre_y = lane_top + ROW / 2 + slots[node] * ROW
        info.update({"x": 80 + column * COL + (TASK_W - width) / 2, "y": centre_y - height / 2,
                     "w": width, "h": height, "cx": 80 + column * COL + TASK_W / 2, "cy": centre_y})
    return geometry


def data_shapes(nodes, flows, geometry, lanes):
    """Position one data object per artifact next to the activity that produces or first uses it."""
    shapes, used = {}, {}
    for index, row in enumerate(flows):
        anchor = (row["produced_by"] or row["consumed_by"]).split(";")[0].strip()
        if anchor not in nodes:
            continue
        host = nodes[anchor]
        slot = used.get(anchor, 0)
        used[anchor] = slot + 1
        shapes[row["key"]] = {"id": f"Data_{index + 1}", "name": row["artifact"], "status": row["status"],
                              "x": host["x"] + slot * (DATA_W + 8), "y": host["y"] - DATA_H - 18,
                              "w": DATA_W, "h": DATA_H}
    return shapes


def xml_for(name, nodes, edges, lanes, exceptions, geometry, data=None, flows=None):
    total_w = max(n["x"] + n["w"] for n in nodes.values()) + 120
    total_h = sum(height for _, height in geometry.values()) + 40
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           f'<bpmn:definitions xmlns:bpmn={quoteattr(NS["bpmn"])} xmlns:bpmndi={quoteattr(NS["bpmndi"])} '
           f'xmlns:dc={quoteattr(NS["dc"])} xmlns:di={quoteattr(NS["di"])} id="Definitions_1" '
           'targetNamespace="http://example.org/gapelicit">',
           '  <bpmn:collaboration id="Collaboration_1">',
           f'    <bpmn:participant id="Participant_1" name={quoteattr(name)} processRef="Process_1" />',
           '  </bpmn:collaboration>',
           '  <bpmn:process id="Process_1" isExecutable="false">',
           '    <bpmn:laneSet id="LaneSet_1">']
    for index, lane in enumerate(lanes):
        members = [n for n in nodes.values() if n["lane"] == lane]
        out.append(f'      <bpmn:lane id="Lane_{index}" name={quoteattr(lane)}>')
        out += [f'        <bpmn:flowNodeRef>{escape(m["id"])}</bpmn:flowNodeRef>' for m in members]
        out.append('      </bpmn:lane>')
    out.append('    </bpmn:laneSet>')

    incoming, outgoing = {}, {}
    for index, edge in enumerate(edges):
        edge["id"] = f"Flow_{index + 1}"
        outgoing.setdefault(edge["from"], []).append(edge["id"])
        incoming.setdefault(edge["to"], []).append(edge["id"])
    produces, requires = {}, {}
    if data and flows:
        for row in flows:
            shape = data.get(row["key"])
            if not shape:
                continue
            for activity in filter(None, (a.strip() for a in row["produced_by"].split(";"))):
                produces.setdefault(activity, []).append(shape["id"])
            for activity in filter(None, (a.strip() for a in row["consumed_by"].split(";"))):
                requires.setdefault(activity, []).append(shape["id"])
    associations = []
    for node in nodes.values():
        tag = f'bpmn:{node["kind"]}'
        out.append(f'    <{tag} id="{escape(node["id"])}" name={quoteattr(node["name"])}>')
        if node["system"] and node["system"].lower() not in ("unknown", "none", "n/a"):
            out.append(f'      <bpmn:documentation>System: {escape(node["system"])}</bpmn:documentation>')
        out += [f'      <bpmn:incoming>{ref}</bpmn:incoming>' for ref in incoming.get(node["id"], [])]
        out += [f'      <bpmn:outgoing>{ref}</bpmn:outgoing>' for ref in outgoing.get(node["id"], [])]
        for ref in requires.get(node["id"], []):
            aid = f'DataIn_{len(associations) + 1}'
            associations.append((aid, ref, node["id"]))
            out += [f'      <bpmn:dataInputAssociation id="{aid}">',
                    f'        <bpmn:sourceRef>{ref}</bpmn:sourceRef>', '      </bpmn:dataInputAssociation>']
        for ref in produces.get(node["id"], []):
            aid = f'DataOut_{len(associations) + 1}'
            associations.append((aid, node["id"], ref))
            out += [f'      <bpmn:dataOutputAssociation id="{aid}">',
                    f'        <bpmn:targetRef>{ref}</bpmn:targetRef>', '      </bpmn:dataOutputAssociation>']
        out.append(f'    </{tag}>')
    for shape in (data or {}).values():
        out.append(f'    <bpmn:dataObjectReference id="{shape["id"]}" name={quoteattr(shape["name"])} '
                   f'dataObjectRef="{shape["id"]}_obj" />')
        out.append(f'    <bpmn:dataObject id="{shape["id"]}_obj" />')
    for edge in edges:
        attrs = f'id="{edge["id"]}" sourceRef="{escape(edge["from"])}" targetRef="{escape(edge["to"])}"'
        if edge["label"]:
            attrs += f' name={quoteattr(edge["label"])}'
        out.append(f'    <bpmn:sequenceFlow {attrs} />')
    for index, exception in enumerate(exceptions):
        text = exception.get("description", str(exception)) if isinstance(exception, dict) else str(exception)
        out.append(f'    <bpmn:textAnnotation id="Note_{index}"><bpmn:text>{escape(text)}</bpmn:text></bpmn:textAnnotation>')
        target = exception.get("handling_activity") if isinstance(exception, dict) else None
        if target in nodes:
            out.append(f'    <bpmn:association id="Assoc_{index}" sourceRef="Note_{index}" targetRef="{escape(target)}" />')
    out.append('  </bpmn:process>')

    out += ['  <bpmndi:BPMNDiagram id="Diagram_1">',
            '    <bpmndi:BPMNPlane id="Plane_1" bpmnElement="Collaboration_1">',
            f'      <bpmndi:BPMNShape id="Participant_1_di" bpmnElement="Participant_1" isHorizontal="true">',
            f'        <dc:Bounds x="20" y="20" width="{total_w}" height="{total_h:.0f}" />',
            '      </bpmndi:BPMNShape>']
    for index, lane in enumerate(lanes):
        lane_top, lane_height = geometry[lane]
        out += [f'      <bpmndi:BPMNShape id="Lane_{index}_di" bpmnElement="Lane_{index}" isHorizontal="true">',
                f'        <dc:Bounds x="50" y="{lane_top - ROW / 4:.0f}" width="{total_w - 30}" height="{lane_height:.0f}" />',
                '      </bpmndi:BPMNShape>']
    for node in nodes.values():
        out += [f'      <bpmndi:BPMNShape id="{escape(node["id"])}_di" bpmnElement="{escape(node["id"])}">',
                f'        <dc:Bounds x="{node["x"]:.0f}" y="{node["y"]:.0f}" width="{node["w"]}" height="{node["h"]}" />',
                '      </bpmndi:BPMNShape>']
    for shape in (data or {}).values():
        out += [f'      <bpmndi:BPMNShape id="{shape["id"]}_di" bpmnElement="{shape["id"]}">',
                f'        <dc:Bounds x="{shape["x"]:.0f}" y="{shape["y"]:.0f}" width="{shape["w"]}" height="{shape["h"]}" />',
                '      </bpmndi:BPMNShape>']
    for aid, source, target in associations:
        a = nodes.get(source) or next(s for s in data.values() if s["id"] == source)
        b = nodes.get(target) or next(s for s in data.values() if s["id"] == target)
        out += [f'      <bpmndi:BPMNEdge id="{aid}_di" bpmnElement="{aid}">',
                f'        <di:waypoint x="{a["x"] + a["w"] / 2:.0f}" y="{a["y"] + a["h"] / 2:.0f}" />',
                f'        <di:waypoint x="{b["x"] + b["w"] / 2:.0f}" y="{b["y"] + b["h"] / 2:.0f}" />',
                '      </bpmndi:BPMNEdge>']
    for index, exception in enumerate(exceptions):
        out += [f'      <bpmndi:BPMNShape id="Note_{index}_di" bpmnElement="Note_{index}">',
                f'        <dc:Bounds x="{80 + index * 260}" y="{total_h + 40:.0f}" width="240" height="60" />',
                '      </bpmndi:BPMNShape>']
    for edge in edges:
        source, target = nodes[edge["from"]], nodes[edge["to"]]
        x1, y1 = source["x"] + source["w"], source["cy"]
        x2, y2 = target["x"], target["cy"]
        points = [(x1, y1), (x2, y2)] if abs(y1 - y2) < 1 else [(x1, y1), ((x1 + x2) / 2, y1), ((x1 + x2) / 2, y2), (x2, y2)]
        out.append(f'      <bpmndi:BPMNEdge id="{edge["id"]}_di" bpmnElement="{edge["id"]}">')
        out += [f'        <di:waypoint x="{px:.0f}" y="{py:.0f}" />' for px, py in points]
        out.append('      </bpmndi:BPMNEdge>')
    out += ['    </bpmndi:BPMNPlane>', '  </bpmndi:BPMNDiagram>', '</bpmn:definitions>', '']
    return "\n".join(out)


def artifact_key(name):
    # "Exception record (if applicable)" and "exception record" are the same artifact.
    text = re.sub(r"\([^)]*\)", " ", str(name)).lower().replace("_", " ")
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", text).split())


def data_flow(workflow):
    produced, consumed, label = {}, {}, {}
    for activity in workflow.get("activities", []):
        if not isinstance(activity, dict) or not activity.get("id"):
            continue
        for item in activity.get("outputs") or []:
            key = artifact_key(item)
            if key:
                produced.setdefault(key, []).append(activity["id"])
                label.setdefault(key, str(item))
        for item in activity.get("inputs") or []:
            key = artifact_key(item)
            if key:
                consumed.setdefault(key, []).append(activity["id"])
                label.setdefault(key, str(item))
    rows = []
    for key in sorted(set(produced) | set(consumed)):
        status = ("linked" if key in produced and key in consumed else
                  "output only" if key in produced else "input only")
        rows.append({"artifact": label[key], "key": key, "status": status,
                     "produced_by": "; ".join(produced.get(key, [])),
                     "consumed_by": "; ".join(consumed.get(key, []))})
    return rows


def register_rows(workflow, opportunities, gaps):
    candidates = {}
    for item in opportunities:
        if not isinstance(item, dict):
            continue
        target = str(item.get("target", ""))
        key = target.split()[0].strip(":-") if target else ""
        candidates[key] = item
    rows = []
    for activity in workflow.get("activities", []):
        if not isinstance(activity, dict) or not activity.get("id"):
            continue
        candidate = candidates.get(activity["id"], {})
        rows.append({
            "activity_id": activity["id"],
            "activity": activity.get("name", ""),
            "actor": activity.get("actor", ""),
            "system": activity.get("system", ""),
            "inputs": "; ".join(str(x) for x in (activity.get("inputs") or [])),
            "outputs": "; ".join(str(x) for x in (activity.get("outputs") or [])),
            "automation_candidate": "yes" if candidate else "no",
            "rationale": candidate.get("rationale", ""),
            "required_data": "; ".join(str(x) for x in (candidate.get("required_data") or [])),
            "constraints": "; ".join(str(x) for x in (candidate.get("constraints") or [])),
            "model_confidence": candidate.get("confidence", ""),
            "method": "",            # robot | llm | program | human  ← 사람이 채움
            "priority": "",          # 1..n                          ← 사람이 채움
            "owner": "",
            "status": "",            # backlog | building | live
            "evidence_checked": "",  # provenance 확인 여부           ← 사람이 채움
        })
    for index, gap in enumerate(gaps):
        rows.append({"activity_id": f"GAP{index + 1}", "activity": str(gap), "actor": "", "system": "",
                     "inputs": "", "outputs": "", "automation_candidate": "unknown", "rationale": "",
                     "required_data": "", "constraints": "", "model_confidence": "", "method": "",
                     "priority": "", "owner": "", "status": "open gap", "evidence_checked": ""})
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", help="Elicited workflow JSON, pipeline output, or stored API record.")
    parser.add_argument("--name", default="Elicited Process")
    parser.add_argument("--out-dir", type=Path, default=Path("out"))
    parser.add_argument("--stem", default=None)
    parser.add_argument("--data", action="store_true",
                        help="Draw data objects on the diagram. Off by default because they crowd it; "
                             "the data-flow CSV is always written.")
    args = parser.parse_args()

    workflow, opportunities, gaps = load_workflow(args.source)
    nodes, edges = build_graph(workflow)
    if not nodes:
        parser.error("No activities or decisions found in the source file")
    nodes, edges = add_events(nodes, edges)
    layer = layer_nodes(nodes, edges)
    lanes = assign_lanes(nodes, edges, layer)
    geometry = place(nodes, layer, lanes)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    stem = args.stem or Path(args.source).parent.name or "process"
    flows = data_flow(workflow)
    shapes = data_shapes(nodes, flows, geometry, lanes) if args.data else None
    bpmn_path = args.out_dir / f"{stem}.bpmn"
    bpmn_path.write_text(xml_for(args.name, nodes, edges, lanes, workflow.get("exceptions", []), geometry,
                                 shapes, flows), encoding="utf-8")

    rows = register_rows(workflow, opportunities, gaps)
    csv_path = args.out_dir / f"{stem}_automation_register.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    flow_path = args.out_dir / f"{stem}_data_flow.csv"
    with flow_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["artifact", "status", "produced_by", "consumed_by", "key"])
        writer.writeheader()
        writer.writerows(flows)

    linked = sum(1 for row in flows if row["status"] == "linked")
    print(f"{bpmn_path}  ({len(nodes)} nodes, {len(edges)} flows, {len(lanes)} lanes"
          f"{f', {len(shapes)} data objects' if shapes else ''})")
    print(f"{csv_path}  ({len(rows)} rows)")
    print(f"{flow_path}  ({len(flows)} artifacts, {linked} linked producer-to-consumer)")
    if flows and linked / len(flows) < 0.5:
        print(f"  note: only {linked}/{len(flows)} artifacts are named consistently enough to connect "
              "one activity's output to another's input; the rest dangle.")


if __name__ == "__main__":
    main()
