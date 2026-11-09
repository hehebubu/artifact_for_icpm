import unittest
import xml.etree.ElementTree as ET

import export_bpmn as ex

B = "{http://www.omg.org/spec/BPMN/20100524/MODEL}"
D = "{http://www.omg.org/spec/BPMN/20100524/DI}"
WORKFLOW = {
    "activities": [{"id": "A1", "name": "Review request", "actor": "Engineer", "system": "Unknown",
                    "inputs": ["Test request"], "outputs": ["Reviewed request"]},
                   {"id": "A2", "name": "Run test", "actor": "Engineer", "system": "Test tool",
                    "inputs": ["Reviewed request"], "outputs": ["Result files"]},
                   {"id": "A3", "name": "Escalate", "actor": "Reviewer", "system": "",
                    "inputs": ["Result files (if any)"], "outputs": []}],
    "decisions": [{"id": "D1", "condition": "Results valid?",
                   "branches": [{"outcome": "Yes", "next": "A3"}, {"outcome": "No", "next": "end"}]}],
    "exceptions": [{"id": "E1", "description": "Tool unavailable", "handling_activity": "A3"}],
    "dependencies": [{"from": "A1", "to": "A2"}, {"from": "A2", "to": "D1"}, {"from": "D1", "to": "A3"}],
}


def render(workflow):
    nodes, edges = ex.build_graph(workflow)
    nodes, edges = ex.add_events(nodes, edges)
    layer = ex.layer_nodes(nodes, edges)
    lanes = ex.assign_lanes(nodes, edges, layer)
    geometry = ex.place(nodes, layer, lanes)
    return ET.fromstring(ex.xml_for("Test", nodes, edges, lanes, workflow.get("exceptions", []), geometry)), nodes, edges


class ExportTests(unittest.TestCase):
    def test_every_flow_points_at_a_declared_node(self):
        root, _, _ = render(WORKFLOW)
        declared = {e.get("id") for e in root.iter() if e.get("id")}
        for flow in root.iter(B + "sequenceFlow"):
            self.assertIn(flow.get("sourceRef"), declared)
            self.assertIn(flow.get("targetRef"), declared)

    def test_every_node_has_a_shape_so_viewers_can_render_it(self):
        root, nodes, _ = render(WORKFLOW)
        shapes = {s.get("bpmnElement") for s in root.iter(D + "BPMNShape")}
        for node in nodes:
            self.assertIn(node, shapes)

    def test_task_kind_follows_whether_a_system_is_known(self):
        _, nodes, _ = render(WORKFLOW)
        self.assertEqual(nodes["A2"]["kind"], "serviceTask")
        self.assertEqual(nodes["A1"]["kind"], "userTask")

    def test_branch_outcomes_label_their_flows_and_terminal_branches_reach_the_end(self):
        root, _, _ = render(WORKFLOW)
        named = {(f.get("sourceRef"), f.get("targetRef")): f.get("name") for f in root.iter(B + "sequenceFlow")}
        self.assertEqual(named[("D1", "A3")], "Yes")
        self.assertEqual(named[("D1", ex.END)], "No")

    def test_decisions_inherit_the_lane_of_their_predecessor(self):
        _, nodes, _ = render(WORKFLOW)
        self.assertEqual(nodes["D1"]["lane"], nodes["A2"]["lane"])

    def test_string_branches_and_malformed_entries_do_not_crash(self):
        workflow = {**WORKFLOW, "decisions": [{"id": "D1", "condition": "?", "branches": ["yes", "no"]}],
                    "activities": WORKFLOW["activities"] + ["junk"], "dependencies": WORKFLOW["dependencies"] + ["junk"]}
        root, nodes, _ = render(workflow)
        self.assertIn("D1", nodes)
        self.assertTrue(len(list(root.iter(B + "sequenceFlow"))) > 0)

    def test_artifact_keys_ignore_parentheticals_and_case(self):
        self.assertEqual(ex.artifact_key("Exception record (if applicable)"), ex.artifact_key("exception record"))
        self.assertNotEqual(ex.artifact_key("Draft report"), ex.artifact_key("Shared report"))

    def test_data_flow_classifies_each_artifact(self):
        workflow = {"activities": [
            {"id": "A1", "name": "a", "outputs": ["Result files"], "inputs": ["Test request"]},
            {"id": "A2", "name": "b", "inputs": ["Result files (if available)"], "outputs": ["Report"]}]}
        by_key = {r["key"]: r for r in ex.data_flow(workflow)}
        self.assertEqual(by_key["result files"]["status"], "linked")
        self.assertEqual(by_key["result files"]["produced_by"], "A1")
        self.assertEqual(by_key["result files"]["consumed_by"], "A2")
        self.assertEqual(by_key["test request"]["status"], "input only")
        self.assertEqual(by_key["report"]["status"], "output only")

    def test_data_objects_are_declared_and_associated_when_requested(self):
        nodes, edges = ex.build_graph(WORKFLOW)
        nodes, edges = ex.add_events(nodes, edges)
        layer = ex.layer_nodes(nodes, edges)
        lanes = ex.assign_lanes(nodes, edges, layer)
        geometry = ex.place(nodes, layer, lanes)
        flows = ex.data_flow(WORKFLOW)
        shapes = ex.data_shapes(nodes, flows, geometry, lanes)
        root = ET.fromstring(ex.xml_for("Test", nodes, edges, lanes, [], geometry, shapes, flows))
        declared = {e.get("id") for e in root.iter() if e.get("id")}
        for ref in root.iter(B + "dataObjectReference"):
            self.assertIn(ref.get("dataObjectRef"), declared)
        for assoc in root.iter(B + "dataInputAssociation"):
            self.assertIn(assoc.find(B + "sourceRef").text, declared)

    def test_register_marks_activities_named_by_an_opportunity(self):
        rows = ex.register_rows(WORKFLOW, [{"target": "A2 - Run test", "rationale": "repetitive",
                                            "confidence": "high"}], ["owner of A3 unknown"])
        by_id = {r["activity_id"]: r for r in rows}
        self.assertEqual(by_id["A2"]["automation_candidate"], "yes")
        self.assertEqual(by_id["A1"]["automation_candidate"], "no")
        self.assertEqual(by_id["GAP1"]["status"], "open gap")
        self.assertEqual(by_id["A2"]["method"], "")


if __name__ == "__main__":
    unittest.main()
