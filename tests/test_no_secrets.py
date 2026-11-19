"""커밋된 파일에 API 키 형태의 문자열이나 .env 파일이 있으면 실패한다."""
import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KEY_PATTERN = re.compile("sk-" + "ant")  # 이 파일 자체가 걸리지 않도록 나눠서 쓴다


def tracked_files():
    try:
        out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
        return [ROOT / p for p in out.splitlines() if p]
    except (OSError, subprocess.CalledProcessError):
        skip = {".git", ".venv", "__pycache__"}
        return [p for p in ROOT.rglob("*") if p.is_file() and not skip & set(p.parts)]


class TestNoSecrets(unittest.TestCase):
    def test_no_env_files(self):
        bad = [str(p.relative_to(ROOT)) for p in tracked_files()
               if p.name == ".env" or (p.name.startswith(".env.") and p.name != ".env.example")]
        self.assertEqual(bad, [], f".env 파일이 커밋돼 있습니다: {bad}")

    def test_no_api_key_strings(self):
        bad = []
        for p in tracked_files():
            if not p.is_file():
                continue
            try:
                text = p.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            if KEY_PATTERN.search(text):
                bad.append(str(p.relative_to(ROOT)))
        self.assertEqual(bad, [], f"API 키 형태의 문자열이 있습니다: {bad}")


if __name__ == "__main__":
    unittest.main()
