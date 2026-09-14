import unittest

import run_provenance as p
import score_runs as sr


class ProvenanceTests(unittest.TestCase):
    def test_label_covers_every_combination(self):
        cases = {(True, True, True): "carried", (True, True, False): "lost", (True, False, True): "carried",
                 (True, False, False): "lost", (False, True, True): "recovered", (False, True, False): "dropped",
                 (False, False, True): "unsupported", (False, False, False): "missed"}
        for flags, label in cases.items():
            self.assertEqual(p.label_for(*flags), label)

    def test_match_levels_separate_phrase_field_and_document(self):
        document = p.source({"a": "collect result files", "b": "incomplete", "c": "vendor", "d": "proposal"})
        self.assertEqual(p.match_level(document, "Collect result files"), "exact")
        self.assertEqual(p.match_level(p.source(["collect the result files today"]), "collect result files"), "field")
        self.assertEqual(p.match_level(document, "vendor proposal incomplete"), "scatter")
        self.assertEqual(p.match_level(document, "audit trail"), "none")

    def test_leaves_keep_only_field_strings(self):
        self.assertEqual(p.leaves({"x": ["A B", {"y": "c"}], "z": 3, "w": ""}), ["a b", "c"])

    def test_stored_criterion_reproduces_the_saved_scorer(self):
        field = p.source({"workflow": {"activities": [{"name": "Share Report For Internal Review"}]}})
        for item in ("Share report for review", "vendor proposal incomplete", "audit trail"):
            self.assertEqual(p.match_level(field, item) != "none", sr.soft_contains(field["text"], item))

    def test_discovery_reads_every_corpus_and_resolves_cached_arms(self):
        runs = list(p.discover(p.ROOT / "data/ablation"))
        arms = {(run["corpus"], run["arm"]) for run in runs}
        self.assertEqual(len(runs), 72)
        self.assertEqual(len(arms), 6)
        cached = [run for run in runs if run["cached"]]
        self.assertEqual(len(cached), 16)
        for run in cached:
            self.assertNotIn("domain_taxonomy_v1", str(run["paths"]["update"]))


if __name__ == "__main__":
    unittest.main()
