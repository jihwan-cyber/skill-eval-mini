"""variance.py 가 반복(trial)마다 정확도를 따로 계산하는지 확인한다."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from variance import build_table, per_trial_accuracy, stats  # noqa: E402


class TestVariance(unittest.TestCase):
    def test_per_trial_stats(self):
        rows = ([{"trial": 1, "correct": True}] * 4 + [{"trial": 1, "correct": False}] * 1     # 80%
                + [{"trial": 2, "correct": True}] * 5                                         # 100%
                + [{"trial": 3, "correct": True}] * 3 + [{"trial": 3, "correct": False}] * 2)  # 60%
        accs = per_trial_accuracy(rows)
        self.assertEqual(accs, {1: 0.8, 2: 1.0, 3: 0.6})
        s = stats(accs)
        self.assertEqual(s["runs"], 3)
        self.assertAlmostEqual(s["mean"], 0.8)
        self.assertAlmostEqual(s["range"], 0.4)

    def test_table_has_no_request_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "r.json"
            p.write_text(json.dumps({"results": [{"variant": "v", "split": "s", "rows": [
                {"trial": 1, "correct": True, "request": "비밀요청_가나다", "raw": "응답_라마바"},
                {"trial": 2, "correct": False, "request": "비밀요청_가나다", "raw": "응답_라마바"}]}]},
                ensure_ascii=False), encoding="utf-8")
            table = build_table([str(p)])
        self.assertIn("| v | s | 2 | 50.0% | 0.0% | 100.0% | 100.0%p |", table)
        self.assertNotIn("비밀요청", table)
        self.assertNotIn("응답_라마바", table)


if __name__ == "__main__":
    unittest.main()
