"""eval.py --selector keyword 가 API 키 없이 끝까지 돌고 정확도를 출력하는지 확인한다.
결과는 임시 파일에 저장해서 저장소의 결과 파일을 바꾸지 않는다."""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class TestEvalKeyword(unittest.TestCase):
    def run_eval(self, cases):
        env = {k: v for k, v in os.environ.items() if not k.startswith("ANTHROPIC")}
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "out.json"
            proc = subprocess.run(
                [sys.executable, "eval.py", "--selector", "keyword", "--cases", cases, "--out", str(out)],
                cwd=ROOT, env=env, capture_output=True, text=True, timeout=120,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("정확도:", proc.stdout)
            self.assertTrue(out.exists(), "결과 파일이 저장되지 않았습니다")

    def test_v2_without_api_key(self):
        self.run_eval("cases_v2.json")

    def test_v3_without_api_key(self):
        self.run_eval("cases_v3.json")


if __name__ == "__main__":
    unittest.main()
