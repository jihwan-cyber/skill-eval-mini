"""스킬 선택 평가 v2.

스킬 목록은 load_skills()로 skills/*/SKILL.md 에서 읽고,
선택기(selector)를 바꿔 끼워 같은 테스트셋으로 비교한다.

  python3 eval.py --selector keyword   # API 없이 도는 기준선
  python3 eval.py --selector api       # Claude API 사용 (ANTHROPIC_API_KEY 필요)
"""
import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

from load_skills import load_skills

NONE = "none"
INVALID = "invalid"  # 스킬 목록에 없는 이름을 답한 경우
EMPTY = "empty"  # 텍스트 답이 없는 경우 (예: 생각하다가 max_tokens에 걸림)

# 라우터 모델에게 주는 기본 지시문. improve.py 가 이 문장을 개선 대상으로 삼는다.
DEFAULT_INSTRUCTION = (
    "가장 알맞은 스킬 이름 하나만 답하세요. "
    "맞는 스킬이 없으면 none 이라고만 답하세요."
)

# ---------------------------------------------------------------- 선택기

# 키 없이 파이프라인을 검증하고, 모델 결과와 비교할 기준선용 키워드.
KEYWORDS = {
    "translate": ["번역", "영어로", "한국어로", "옮겨", "바꿔"],
    "summarize": ["요약", "줄여", "핵심", "요점", "정리"],
    "code_help": ["코드", "에러", "오류", "버그", "파이썬", "python"],
    "data_analysis": ["계산", "평균", "표준편차", "증가율", "늘었", "표 "],
    "write_email": ["메일", "메시지", "초안"],
    "report_write": ["보고서를 써", "보고서를 작성", "기획서"],
    "proofread": ["맞춤법", "문법", "다듬", "어색한"],
}


def keyword_selector(request, skills):
    text = request.lower()
    scores = {
        name: sum(kw in text for kw in KEYWORDS.get(name, []))
        for name in skills
    }
    best = max(scores, key=scores.get)
    return (best if scores[best] > 0 else NONE), {}


def make_api_selector(model, effort, instruction=DEFAULT_INSTRUCTION):
    import anthropic  # API 모드에서만 필요

    client = anthropic.Anthropic()

    def api_selector(request, skills):
        skill_text = "\n".join(f"- {n}: {d}" for n, d in skills.items())
        prompt = (
            f"사용 가능한 스킬 목록:\n{skill_text}\n\n"
            f"사용자 요청: {request}\n\n"
            f"{instruction}"
        )
        resp = client.messages.create(
            model=model,
            # Haiku 5.5는 기본으로 생각(thinking)을 먼저 하므로, 생각할 여유를 둔다.
            max_tokens=1024,
            output_config={"effort": effort},
            messages=[{"role": "user", "content": prompt}],
        )
        raw = "".join(b.text for b in resp.content if b.type == "text")
        usage = {
            "raw": raw,
            "stop_reason": resp.stop_reason,
            "input_tokens": resp.usage.input_tokens,
            "output_tokens": resp.usage.output_tokens,
        }
        return raw, usage

    return api_selector


def normalize(raw, skills):
    """모델 답을 스킬 이름 / none / invalid 중 하나로 정리한다."""
    if not (raw or "").strip():
        return EMPTY
    token = re.sub(r"[`'\".\s]", "", raw.strip().lower())
    if token in skills or token == NONE:
        return token
    return INVALID


# ---------------------------------------------------------------- 지표

def compute_metrics(rows, labels):
    total = len(rows)
    correct = sum(r["correct"] for r in rows)

    confusion = defaultdict(Counter)  # confusion[정답][예측]
    for r in rows:
        confusion[r["expected"]][r["picked"]] += 1

    per_skill = {}
    for name in labels:
        tp = confusion[name][name]
        fp = sum(confusion[e][name] for e in confusion if e != name)
        fn = sum(c for p, c in confusion[name].items() if p != name)
        per_skill[name] = {
            "precision": round(tp / (tp + fp), 3) if tp + fp else None,
            "recall": round(tp / (tp + fn), 3) if tp + fn else None,
            "support": tp + fn,
        }

    by_tag = defaultdict(lambda: [0, 0])
    for r in rows:
        by_tag[r["tag"]][0] += r["correct"]
        by_tag[r["tag"]][1] += 1

    # 같은 요청을 여러 번 돌렸을 때 매번 같은 답을 했는지 (반복 실행 시에만)
    picks_by_id = defaultdict(list)
    for r in rows:
        picks_by_id[r["id"]].append(r["picked"])
    repeated = {i: p for i, p in picks_by_id.items() if len(p) > 1}
    unstable = sorted(i for i, p in repeated.items() if len(set(p)) > 1)
    consistency = round(1 - len(unstable) / len(repeated), 3) if repeated else None

    none_rows = [r for r in rows if r["expected"] == NONE]
    skill_rows = [r for r in rows if r["expected"] != NONE]
    return {
        "accuracy": round(correct / total, 3) if total else 0,
        "correct": correct,
        "total": total,
        "accuracy_by_tag": {t: f"{c}/{n}" for t, (c, n) in by_tag.items()},
        # 스킬이 필요 없는데 스킬을 고른 비율 (오발동)
        # (목록 밖 답변은 따로 센다)
        "false_trigger_rate": round(
            # 정답 후보(acceptable)에 든 스킬을 고른 경우는 정답이므로 오발동으로 세지 않는다
            sum(r["picked"] not in (NONE, INVALID, EMPTY) and not r["correct"] for r in none_rows)
            / len(none_rows), 3
        ) if none_rows else None,
        # 스킬이 필요한데 none 을 고른 비율 (누락)
        "miss_rate": round(
            sum(r["picked"] == NONE and not r["correct"] for r in skill_rows) / len(skill_rows), 3
        ) if skill_rows else None,
        "invalid_count": sum(r["picked"] == INVALID for r in rows),
        "empty_count": sum(r["picked"] == EMPTY for r in rows),
        "consistency": consistency,
        "unstable_case_ids": unstable,
        "per_skill": per_skill,
        "confusion": {e: dict(c) for e, c in confusion.items()},
    }


def print_report(rows, metrics):
    print(f"정확도: {metrics['correct']}/{metrics['total']} ({metrics['accuracy']:.1%})")
    print("태그별:", metrics["accuracy_by_tag"])
    print("오발동률(none인데 스킬 선택):", metrics["false_trigger_rate"])
    print("누락률(스킬 필요한데 none):", metrics["miss_rate"])
    print("목록 밖 답변 수:", metrics["invalid_count"])
    print("빈 답변 수:", metrics["empty_count"])
    if metrics["consistency"] is not None:
        print("일관성(반복해도 같은 답):", metrics["consistency"],
              "/ 흔들린 케이스:", metrics["unstable_case_ids"])
    print("\n스킬별 정밀도 / 재현율")
    for name, m in metrics["per_skill"].items():
        print(f"  {name:14s} P={m['precision']}  R={m['recall']}  (n={m['support']})")
    print("\n틀린 케이스")
    for r in rows:
        if not r["correct"]:
            trial = f" (시도 {r['trial']})" if r.get("repeats", 1) > 1 else ""
            print(f"  #{r['id']}{trial} [{r['tag']}] {r['expected']} -> {r['picked']} : {r['request']}")
            if r["picked"] in (INVALID, EMPTY) and "raw" in r:
                print(f"      모델 원문: {r['raw'][:80]!r}  (stop_reason={r.get('stop_reason')})")


# ---------------------------------------------------------------- 실행

def run(selector, skills, cases, repeats=1):
    rows = []
    for trial in range(1, repeats + 1):
        for case in cases:
            raw, extra = selector(case["request"], skills)
            picked = normalize(raw, skills)
            # 정답이 둘 이상 가능한 애매한 요청은 acceptable 목록 중 하나면 정답
            acceptable = case.get("acceptable", [case["expected"]])
            rows.append({
                "id": case["id"],
                "trial": trial,
                "repeats": repeats,
                "request": case["request"],
                "tag": case.get("tag", "clear"),
                "expected": case["expected"],
                "picked": picked,
                "correct": picked in acceptable,
                **extra,
            })
    return rows


def load_cases(path):
    """케이스 파일을 읽는다.

    - 리스트 형식: 케이스 목록만 있고 스킬은 skills/ 에서 읽는다 (v2).
    - 딕셔너리 형식: {"skills_dirs": [...], "cases": [...]} (v3).
    """
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return ["skills"], data
    return data.get("skills_dirs", ["skills"]), data["cases"]


def load_all_skills(dirs):
    base = Path(__file__).resolve().parent
    skills = {}
    for d in dirs:
        for name, desc in load_skills(base / d).items():
            if name in skills:
                print(f"[경고] 스킬 이름 중복: {name} ({d}) - 먼저 읽은 것을 사용", file=sys.stderr)
                continue
            skills[name] = desc
    return skills


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selector", choices=["keyword", "api"], default="keyword")
    ap.add_argument("--model", default="claude-haiku-5-5")
    ap.add_argument("--effort", default="low", choices=["low", "medium", "high"])
    ap.add_argument("--cases", default="cases_v2.json")
    ap.add_argument("--repeats", type=int, default=1, help="같은 케이스를 반복 실행할 횟수")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    skills_dirs, cases = load_cases(args.cases)
    skills = load_all_skills(skills_dirs)
    print(f"스킬 {len(skills)}개: {', '.join(skills)} / 케이스 {len(cases)}개 x {args.repeats}회\n")

    selector = keyword_selector if args.selector == "keyword" else make_api_selector(args.model, args.effort)
    rows = run(selector, skills, cases, args.repeats)
    metrics = compute_metrics(rows, list(skills) + [NONE])
    print_report(rows, metrics)

    version = Path(args.cases).stem.replace("cases_", "")
    out = args.out or f"results_{version}_{args.selector}.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"selector": args.selector, "model": args.model, "effort": args.effort,
                   "cases": args.cases, "repeats": args.repeats,
                   "metrics": metrics, "rows": rows},
                  f, ensure_ascii=False, indent=2)
    print(f"\n저장: {out}")


if __name__ == "__main__":
    main()
