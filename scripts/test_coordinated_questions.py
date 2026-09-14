import unittest

import run_coordinated_questions as co


class CoordinationTests(unittest.TestCase):
    def test_reference_and_arm_labels_not_in_coordinator_input(self):
        scenario = {"id": "S01", "title": "Synthetic", "initial_description": "A worker writes.",
                    "reference_workflow": {"secret": "REFERENCE_SENTINEL"}}
        prompt = co.coordinator_prompt(scenario, [{"candidate_id": "C1", "question": "Who writes?"}], 6)
        for hidden in ("REFERENCE_SENTINEL", "gapelicit", "overall_score"):
            self.assertNotIn(hidden, prompt)
        self.assertIn("Who writes?", prompt)

    def test_selection_rejects_invalid_and_repeated_provenance(self):
        candidates = [{"candidate_id": "C1"}, {"candidate_id": "C2"}]
        co.validate_selection({"clarification_questions": [{"source_ids": ["C1", "C2"]}]}, candidates)
        for questions in ([{"source_ids": []}], [{"source_ids": ["C3"]}],
                          [{"source_ids": ["C1"]}, {"source_ids": ["C1"]}],
                          [{"source_ids": ["C1", "C1"]}]):
            with self.assertRaises(ValueError):
                co.validate_selection({"clarification_questions": questions}, candidates)

    def test_cost_includes_cached_proposers(self):
        scenario = {"reference_workflow": {}}
        workflow = {"workflow": {"activities": []}, "automation_opportunities": [], "remaining_gaps": []}
        records = [{"response": {"usage": {"input_tokens": 10, "output_tokens": 20}}}] * 5
        row, _, _ = co.row_for({"id": "S01", **scenario}, "coordinated", workflow, {"answers": []}, records)
        self.assertEqual(row["pipeline_calls"], 5)
        self.assertEqual(row["input_tokens"], 50)
        self.assertEqual(row["output_tokens"], 100)


if __name__ == "__main__":
    unittest.main()
