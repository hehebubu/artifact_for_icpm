import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import run_question_ablation as ab


class ProtocolTests(unittest.TestCase):
    def setUp(self):
        self.scenario = {"id": "S01", "title": "Synthetic", "initial_description": "A worker writes a report.",
                         "reference_workflow": {"private_test_marker": "REFERENCE_ONLY_SENTINEL"}}

    def test_reference_is_only_exposed_to_oracle(self):
        for arm in ab.ARMS:
            self.assertNotIn("REFERENCE_ONLY_SENTINEL", ab.question_prompt(self.scenario, arm, 6))
        self.assertNotIn("REFERENCE_ONLY_SENTINEL", ab.update_prompt(self.scenario, {"answers": []}))
        self.assertIn("REFERENCE_ONLY_SENTINEL", ab.oracle_prompt(self.scenario, []))

    def test_taxonomy_is_the_only_arm_specific_instruction(self):
        generic = ab.question_prompt(self.scenario, "generic", 6)
        targeted = ab.question_prompt(self.scenario, "gapelicit", 6)
        guidance = (" Use the following automation-critical gap taxonomy to identify gaps and guide question selection: "
                    + ab.TAXONOMY + ". Prioritize gaps relevant to this scenario; do not force every category.")
        self.assertEqual(generic, targeted.replace(guidance, ""))

    def test_question_budget_and_unique_ids(self):
        parsed = {"clarification_questions": [{"id": "Q1", "question": "Who?"}]}
        ab.validate("questions", parsed, 1)
        with self.assertRaises(ValueError):
            ab.validate("questions", parsed, 6)
        with self.assertRaises(ValueError):
            ab.validate("questions", {"clarification_questions": parsed["clarification_questions"] * 2}, 2)

    def test_json_fences_are_removed_without_repairing_content(self):
        self.assertEqual(ab.parse_response('```json\n{"a": 1}\n```'), {"a": 1})
        self.assertEqual(ab.parse_response('{"a": 1}'), {"a": 1})
        with self.assertRaises(ValueError):
            ab.parse_response('```json\n{"a":\n```')

    def test_answers_require_matching_ids_and_word_budget(self):
        with self.assertRaises(ValueError):
            ab.validate("oracle_answers", {"answers": [{"question_id": "Q2", "answer": "Yes"}]}, 1)
        with self.assertRaises(ValueError):
            ab.validate("oracle_answers", {"answers": [{"question_id": "Q1", "answer": "word " * 81}]}, 1)

    def test_cache_does_not_call_api_and_truncation_is_rejected(self):
        args = SimpleNamespace(model="test", max_tokens=4000, temperature=0, questions=1)
        request = {"model": "test", "max_tokens": 4000, "temperature": 0,
                   "messages": [{"role": "user", "content": "prompt"}]}
        response = {"stop_reason": "end_turn", "content": [{"type": "text", "text":
                    '{"clarification_questions":[{"id":"Q1","question":"Who?"}]}'}]}
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            ab.save(directory / "questions.json", {"request": request, "response": response})
            with patch.object(ab, "call_api", side_effect=AssertionError("must not call API")):
                ab.run_stage(directory, "questions", "prompt", args, "unused")
                with self.assertRaises(ValueError):
                    ab.run_stage(directory, "questions", "changed", args, "unused")
                response["stop_reason"] = "max_tokens"
                ab.save(directory / "questions.json", {"request": request, "response": response})
                with self.assertRaises(ValueError):
                    ab.run_stage(directory, "questions", "prompt", args, "unused")


if __name__ == "__main__":
    unittest.main()
