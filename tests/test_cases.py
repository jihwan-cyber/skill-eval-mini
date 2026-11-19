"""cases*.json 마다 필수 항목(요청, 정답)이 있고, 정답이 실제 스킬 이름 또는 none 인지 확인한다."""
import contextlib
import io
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from load_skills import load_skills  # noqa: E402


def load(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):  # v1·v2 형식: 케이스 목록만, 스킬은 skills/
        return ["skills"], data
    return data.get("skills_dirs", ["skills"]), data["cases"]


class TestCaseFiles(unittest.TestCase):
    def test_every_case_file(self):
        files = sorted(ROOT.glob("cases*.json"))
        self.assertTrue(files, "cases*.json 이 없습니다")
        for path in files:
            with self.subTest(file=path.name):
                dirs, cases = load(path)
                with contextlib.redirect_stderr(io.StringIO()):
                    names = set()
                    for d in dirs:
                        names |= set(load_skills(ROOT / d))
                allowed = names | {"none"}
                self.assertTrue(cases, "케이스가 비어 있습니다")
                seen_ids = set()
                for c in cases:
                    cid = c.get("id")
                    self.assertNotIn(cid, seen_ids, f"id {cid} 가 중복됩니다")
                    seen_ids.add(cid)
                    self.assertTrue(str(c.get("request", "")).strip(), f"id {cid}: request 가 없습니다")
                    self.assertIn("expected", c, f"id {cid}: expected 가 없습니다")
                    self.assertIn(c["expected"], allowed, f"id {cid}: 없는 스킬 {c['expected']}")
                    for a in c.get("acceptable", []):
                        self.assertIn(a, allowed, f"id {cid}: acceptable 에 없는 스킬 {a}")
                    if "acceptable" in c:
                        self.assertIn(c["expected"], c["acceptable"], f"id {cid}: expected 가 acceptable 에 없습니다")


if __name__ == "__main__":
    unittest.main()
