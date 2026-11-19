"""web_research 스킬을 넣은 평가용 케이스 파일을 만든다.

기존 케이스 파일을 읽어 skills_dirs 에 skills_search 를 더하고,
labels_search.json 에 있는 번호는 새 정답 기준(LABELING.md)으로 덮어쓴다.
결과는 <원래이름>_search.json 으로 저장한다. 원본 파일은 바꾸지 않는다.

  python3 make_search_cases.py                 # 기본 파일 4개 (없는 파일은 건너뜀)
  python3 make_search_cases.py cases_x.json    # 지정한 파일만
  python3 make_search_cases.py --labels labels_search2.json --suffix _search2   # 라벨 v2
"""
import json
import sys
from pathlib import Path

DEFAULT = ["cases_external.json", "cases_external_task.json", "cases_history.json", "cases_v3.json",
           "cases_test.json"]


def tag_for(case):
    if case.get("acceptable"):
        return "ambiguous"
    return "none" if case["expected"] == "none" else "clear"


def convert(path, labels, suffix="_search", labels_name="labels_search.json"):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):  # v2 형식: 케이스 목록만
        data = {"skills_dirs": ["skills"], "cases": data}
    dirs = list(data.get("skills_dirs", ["skills"]))
    if "skills_search" not in dirs:
        dirs.append("skills_search")
    changed = 0
    cases = []
    for c in data["cases"]:
        c = dict(c)
        new = labels.get(str(c["id"]))
        if new:
            old = (c["expected"], c.get("acceptable"))
            c["expected"] = new["expected"]
            c.pop("acceptable", None)
            if "acceptable" in new:
                c["acceptable"] = new["acceptable"]
            c["tag"] = tag_for(c)
            if old != (c["expected"], c.get("acceptable")):
                changed += 1
        cases.append(c)
    out = Path(path).with_name(Path(path).stem + suffix + ".json")
    note = (data.get("note", "") + " / web_research 스킬 추가 평가용: 정답 기준은 LABELING.md, "
            f"{labels_name} 의 번호별 라벨을 덮어씀.").strip(" /")
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"skills_dirs": dirs, "note": note, "cases": cases}, f, ensure_ascii=False, indent=2)
    print(f"{path} -> {out}  (케이스 {len(cases)}개, 라벨 바뀜 {changed}개)")


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="*")
    ap.add_argument("--labels", default="labels_search.json")
    ap.add_argument("--suffix", default="_search")
    args = ap.parse_args()
    labels = json.load(open(Path(__file__).with_name(args.labels), encoding="utf-8"))["labels"]
    for p in args.files or DEFAULT:
        if not Path(p).exists():
            print(f"{p} 없음, 건너뜀")
            continue
        convert(p, labels, args.suffix, args.labels)


if __name__ == "__main__":
    main()
