"""load_skills.py 가 skills/ 안의 SKILL.md 를 빠짐없이, 오류 없이 읽는지 확인한다."""
import contextlib
import io
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from load_skills import load_skills  # noqa: E402


class TestLoadSkills(unittest.TestCase):
    def test_all_skill_files_load_without_warnings(self):
        for folder in ["skills", "skills_extra", "skills_search"]:
            with self.subTest(folder=folder):
                skill_files = sorted((ROOT / folder).glob("*/SKILL.md"))
                self.assertTrue(skill_files, f"{folder}/ 에 SKILL.md 가 없습니다")
                err = io.StringIO()
                with contextlib.redirect_stderr(err):
                    skills = load_skills(ROOT / folder)
                self.assertEqual(err.getvalue(), "", f"경고가 출력됨: {err.getvalue()}")
                self.assertEqual(len(skills), len(skill_files), "건너뛴 SKILL.md 가 있습니다")
                for name, desc in skills.items():
                    self.assertTrue(desc.strip(), f"{name} 의 description 이 비어 있습니다")

    def test_original_five_skills_present(self):
        self.assertEqual(
            set(load_skills(ROOT / "skills")),
            {"summarize", "translate", "code_help", "data_analysis", "write_email"},
        )


if __name__ == "__main__":
    unittest.main()
