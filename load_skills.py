"""skills/*/SKILL.md 의 frontmatter에서 name과 description을 읽는다."""
import sys
from pathlib import Path

SKILLS_DIR = Path(__file__).resolve().parent / "skills"


def _warn(msg):
    print(f"[경고] {msg}", file=sys.stderr)


def _parse_frontmatter(text):
    """맨 위 --- 사이의 "키: 값" 줄을 딕셔너리로 돌려준다. 없으면 None."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    meta = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return meta
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        meta[key.strip()] = value.strip()
    return None  # 닫는 --- 가 없음


def load_skills(skills_dir=SKILLS_DIR):
    """{name: description} 딕셔너리를 돌려준다. 잘못된 파일은 경고 후 건너뛴다."""
    skills = {}
    for path in sorted(Path(skills_dir).glob("*/SKILL.md")):
        folder = path.parent.name
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            _warn(f"{path}: 읽을 수 없음 ({e})")
            continue
        meta = _parse_frontmatter(text)
        if meta is None:
            _warn(f"{path}: frontmatter가 없음")
            continue
        name = meta.get("name")
        desc = meta.get("description")
        if not name or not desc:
            _warn(f"{path}: name 또는 description이 없음")
            continue
        if name != folder:
            _warn(f"{path}: 폴더 이름({folder})과 name({name})이 다름")
            continue
        skills[name] = desc
    return skills


if __name__ == "__main__":
    for n, d in load_skills().items():
        print(f"{n}: {d}")
