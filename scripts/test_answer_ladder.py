import unittest

import run_answer_ladder as ladder
import run_question_ablation as ab


class LadderTests(unittest.TestCase):
    def setUp(self):
        self.scenario = list(ab.load_scenarios(ladder.ROOT / "data/scenarios.json").values())[0]
        self.questions = [{"id": f"Q{i}", "question": f"question {i}"} for i in range(1, 7)]
        self.frozen = ab.oracle_prompt(self.scenario, self.questions)

    def test_anchor_prompt_is_the_frozen_protocol(self):
        self.assertEqual(ladder.oracle_prompt(self.scenario, self.questions, "L3", 6), self.frozen)
        self.assertEqual(ladder.ANCHOR, "L3")

    def test_other_levels_only_append_to_the_frozen_prompt(self):
        for level in ladder.LEVELS:
            prompt = ladder.oracle_prompt(self.scenario, self.questions, level, 6)
            self.assertTrue(prompt.startswith(self.frozen))
            self.assertEqual(prompt == self.frozen, level == "L3")

    def test_partial_level_names_the_first_half_of_the_questions(self):
        self.assertIn("Q1 through Q3", ladder.oracle_prompt(self.scenario, self.questions, "L1", 6))
        self.assertIn("Q1 through Q3", ladder.oracle_prompt(self.scenario, self.questions, "L1", 5))

    def test_reconstruction_prompt_is_shared_across_levels(self):
        answers = {"answers": [{"question_id": "Q1", "question": "q", "answer": "a"}]}
        self.assertEqual(ab.update_prompt(self.scenario, answers), ab.update_prompt(self.scenario, answers))
        self.assertNotIn("Additional constraint", ab.update_prompt(self.scenario, answers))

    def test_every_level_reports_all_three_criteria(self):
        import rescore_criteria as rc
        self.assertEqual(tuple(rc.CRITERIA), ("document", "field", "exact"))
        self.assertTrue(set(ladder.LEVELS) >= {"L0", "L1", "L2", "L3", "L3p"})


if __name__ == "__main__":
    unittest.main()
