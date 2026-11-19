"""dashboard.py 가 집계만 표에 넣고, 본문은 넣지 않으며, 결과 파일을 바꾸지 않는지 확인한다."""
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dashboard import NO_RECORD, NOT_APPLICABLE, build_table  # noqa: E402

SECRET_REQUEST = "비밀요청문장_가나다"
SECRET_RAW = "모델응답본문_라마바"


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


class TestDashboardFake(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        (root / "skills" / "summarize").mkdir(parents=True)
        (root / "skills" / "summarize" / "SKILL.md").write_text("---\nname: summarize\ndescription: x\n---\n")
        rows = [
            {"id": 1, "request": SECRET_REQUEST, "raw": SECRET_RAW, "picked": "summarize",
             "input_tokens": 100, "output_tokens": 10},
            {"id": 2, "request": SECRET_REQUEST, "raw": SECRET_RAW, "picked": "none",
             "input_tokens": 200, "output_tokens": 20},
            {"id": 3, "request": SECRET_REQUEST, "raw": "", "picked": "empty",
             "input_tokens": 300, "output_tokens": 30},
        ]
        write(root / "results_api.json", {"model": "m-1", "selector": "api", "rows": rows})
        write(root / "results_kw.json", {"selector": "keyword", "rows": [{"id": 1, "request": SECRET_REQUEST, "picked": "none"}]})
        write(root / "improve_runs" / "summary.json", {
            "args": {"model": "m-1", "improver_model": "m-2"},
            "history": [{"iter": 0, "metrics": {"total": 8, "invalid_count": 1, "empty_count": 1}},
                        {"iter": 1, "metrics": {"total": 8, "invalid_count": 0, "empty_count": 0}}],
            "test_rows": {"원본": rows[:2]},
        })
        write(root / "improve_runs" / "ablation_cases_history.json",
              {"model": "m-1", "results": [{"variant": "v", "split": "cases_history", "rows": rows}]})
        self.root = root
        self.files = sorted(p for p in root.rglob("*.json"))
        self.before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in self.files}

    def tearDown(self):
        self.tmp.cleanup()

    def test_aggregates_and_no_body_text(self):
        table = build_table(self.root)
        api_line = next(l for l in table.splitlines() if "results_api.json" in l)
        self.assertIn("| 3 | 66.7% |", api_line)          # 호출 3, 빈 답 1개는 실패
        self.assertIn("| 600 | 60 | 200 / 20 |", api_line)  # 토큰 합계와 호출당 평균
        self.assertIn(NO_RECORD, api_line)                 # 응답 시간은 기록 없음
        kw_line = next(l for l in table.splitlines() if "results_kw.json" in l)
        self.assertIn(NOT_APPLICABLE, kw_line)
        self.assertIn("학습셋 평가 / 0회차", table)
        self.assertIn("| 8 | 75.0% |", table)             # 집계만 남은 평가: 8회 중 2회 실패
        self.assertIn("개선 모델 호출", table)
        self.assertNotIn(SECRET_REQUEST, table)
        self.assertNotIn(SECRET_RAW, table)

    def test_private_history_excluded_by_default(self):
        self.assertNotIn("cases_history", build_table(self.root))
        self.assertIn("cases_history", build_table(self.root, include_private=True))

    def test_result_files_unchanged(self):
        out = Path(self.tmp.name) / "out.md"
        subprocess.run([sys.executable, str(ROOT / "dashboard.py"), "--root", str(self.root), "--out", str(out)],
                       check=True, capture_output=True, text=True)
        self.assertTrue(out.exists())
        after = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in self.files}
        self.assertEqual(self.before, after)


class TestDashboardRepo(unittest.TestCase):
    def test_repo_table_has_no_request_text(self):
        table = build_table(ROOT)
        self.assertIn("합계 (API 호출)", table)
        requests = set()
        for f in ROOT.glob("cases*.json"):
            data = json.loads(f.read_text(encoding="utf-8"))
            for c in data if isinstance(data, list) else data["cases"]:
                if len(c["request"]) >= 6:
                    requests.add(c["request"])
        leaked = [r for r in requests if r in table]
        self.assertEqual(leaked, [], f"요청 원문이 표에 들어갔습니다: {leaked[:3]}")


if __name__ == "__main__":
    unittest.main()
