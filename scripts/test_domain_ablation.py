import copy
import unittest

import run_domain_ablation as d


class DomainTests(unittest.TestCase):
    def setUp(self):
        self.child = list(d.ab.load_scenarios(d.ROOT / "data/scenarios_childcare.json").values())
        self.profiles = d.ab.read(d.ROOT / "data/domain_taxonomies.json")

    def test_dataset_references_and_omission_grounding(self):
        d.validate_childcare(self.child)
        broken = copy.deepcopy(self.child)
        broken[0]["reference_workflow"]["activities"][0]["actor"] = "missing actor"
        with self.assertRaises(ValueError):
            d.validate_childcare(broken)

    def test_common_and_generic_are_exact_original_prompts(self):
        s = self.child[0]
        for arm, old in (("generic", "generic"), ("common", "gapelicit")):
            self.assertEqual(d.question_prompt(s, arm, "childcare", self.profiles, 6), d.ab.question_prompt(s, old, 6))

    def test_domain_prompt_only_adds_context_and_never_reference(self):
        s = copy.deepcopy(self.child[0])
        s["reference_workflow"]["test_secret"] = "REFERENCE_SENTINEL"
        common = d.question_prompt(s, "common", "childcare", self.profiles, 6)
        contextual = d.question_prompt(s, "domain", "childcare", self.profiles, 6)
        self.assertTrue(contextual.startswith(common))
        self.assertNotIn("REFERENCE_SENTINEL", contextual)
        self.assertNotIn("omission_grounding", contextual)
        self.assertNotIn("operating_context", contextual)
        self.assertEqual(set(self.profiles["domains"]["childcare"]), set(self.profiles["common_categories"]))


if __name__ == "__main__":
    unittest.main()
