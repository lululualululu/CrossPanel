import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from .answer_parser import score_uniform

ROOT = Path(__file__).resolve().parents[1]


class SampleEvaluationTests(unittest.TestCase):
    def test_explicit_and_conflicting_choices(self):
        self.assertEqual(score_uniform('{"choice": "b"}')["choice"], "B")
        self.assertIsNone(score_uniform('{"choice":"A","choice":"B"}')["choice"])
        self.assertIsNone(score_uniform("Panel A is brighter than D.")["choice"])

    def test_example_predictions(self):
        report = self.run_scorer(ROOT / "samples" / "example-predictions.jsonl")
        self.assertEqual(
            report["scores"]["overall"],
            {"correct": 2, "total": 4, "accuracy_pct": 50.0},
        )
        self.assertEqual(report["unanswered"], 0)

    def test_missing_predictions_stay_in_denominator(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "predictions.jsonl"
            path.write_text('{"id":"CP-000150","text":"A"}\n', encoding="utf-8")
            report = self.run_scorer(path)
        self.assertEqual(report["scores"]["overall"]["accuracy_pct"], 25.0)
        self.assertEqual(report["unanswered"], 3)

    @staticmethod
    def run_scorer(path):
        result = subprocess.check_output(
            [sys.executable, "-m", "evaluation", "score", "--predictions", str(path)],
            cwd=ROOT,
            text=True,
        )
        return json.loads(result)
