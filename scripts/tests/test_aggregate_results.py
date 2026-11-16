import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from aggregate_results import aggregate


def manifest(task="t1", skill="unicode", track="B"):
    return {"task_id": task, "family_id": task, "primary_skill": skill, "track": track, "languages": ["en", "vi"]}


def row(task="t1", repeat=1, reward=1, language="vi", **changes):
    result = {"trial_id": f"{task}-{language}-{repeat}", "attempt": 1, "task_id": task, "family_id": task, "track": "B", "skill": "unicode", "language": language, "configuration": "fixture-only", "repeat": repeat, "status": "completed", "reward": reward, "duration_sec": 1.0, "cost_usd": None}
    result.update(changes)
    return result


class AggregateTests(unittest.TestCase):
    def group(self, result, language="vi"):
        return next(group for group in result["groups"] if group["language"] == language)

    def test_three_repeats_are_not_best_of_three(self):
        result = aggregate([row(repeat=i, reward=value) for i, value in enumerate([1, 0, 0], 1)], [manifest()])
        self.assertAlmostEqual(self.group(result)["score"], 1 / 3)
        self.assertFalse(self.group(result)["provisional"])
        self.assertTrue(self.group(result, "en")["provisional"])

    def test_retry_infra_preserves_attempts(self):
        first = row(status="infra_error", reward=None)
        second = row(attempt=2)
        result = aggregate([second, first], [manifest()])
        self.assertEqual(len(result["attempts"]), 2)
        self.assertEqual(result["final_trials"][0]["attempt"], 2)
        self.assertEqual(self.group(result)["unresolved_infrastructure_errors"], 0)

    def test_retry_after_failure_is_rejected(self):
        with self.assertRaises(ValueError):
            aggregate([row(reward=0), row(attempt=2)], [manifest()])

    def test_invalid_rewards_and_costs(self):
        for change in [{"reward": True}, {"reward": 0.5}, {"cost_usd": float("nan")}, {"status": "infra_error", "reward": 0}, {"status": "agent_timeout", "reward": 1}]:
            with self.subTest(change=change), self.assertRaises(ValueError):
                aggregate([row(**change)], [manifest()])

    def test_duplicate_or_gapped_attempts(self):
        for rows in [[row(), row()], [row(attempt=2)], [row(), row(trial_id="another")]]:
            with self.assertRaises(ValueError):
                aggregate(rows, [manifest()])

    def test_macro_task_weight_not_trial_weight(self):
        rows = [row(repeat=1), row(repeat=2), row(repeat=3), row(task="t2", reward=0)]
        result = aggregate(rows, [manifest(), manifest("t2")])
        self.assertEqual(self.group(result)["score"], 0.5)
        self.assertTrue(self.group(result)["provisional"])

    def test_macro_skill_weight(self):
        rows = [row(), row(task="t2"), row(task="t3", reward=0, skill="date")]
        result = aggregate(rows, [manifest(), manifest("t2"), manifest("t3", "date")], expected_repeats=1)
        self.assertEqual(self.group(result)["score"], 0.5)

    def test_missing_and_unresolved_are_explicit(self):
        result = aggregate([row(status="verifier_error", reward=None)], [manifest()])
        group = self.group(result)
        self.assertIsNone(group["score"])
        self.assertEqual(group["valid_trials"], 0)
        self.assertEqual(group["unresolved_infrastructure_errors"], 1)
        self.assertEqual(len(group["missing_trials"]), 2)

    def test_paired_a_delta(self):
        rows = [row(language="en", track="A", reward=1), row(language="vi", track="A", reward=0)]
        result = aggregate(rows, [manifest(track="A")], expected_repeats=1)
        self.assertEqual(result["language_deltas"][0]["delta_vs_en_pp"], -100)
        result = aggregate(rows[:1], [manifest(track="A")], expected_repeats=1)
        self.assertEqual(result["language_deltas"], [])


if __name__ == "__main__":
    unittest.main()
