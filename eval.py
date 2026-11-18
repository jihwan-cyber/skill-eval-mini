"""스킬 선택 평가 v2.

스킬 목록은 load_skills()로 skills/*/SKILL.md 에서 읽고,
선택기(selector)를 바꿔 끼워 같은 테스트셋으로 비교한다.

  python3 eval.py --selector keyword   # API 없이 도는 기준선
  python3 eval.py --selector api       # Claude API 사용 (ANTHROPIC_API_KEY 필요)
"""
import argparse
import json
import re
from collections import Counter, defaultdict

from load_skills import load_skills

NONE = "none"
INVALID = "invalid"  # 스킬 목록에 없는 이름을 답한 경우

# ---------------------------------------------------------------- 선택기

# 키 없이 파이프라인을 검증하고, 모델 결과와 비교할 기준선용 키워드.
KEYWORDS = {
    "translate": ["번역", "영어로", "한국어로", "옮겨", "바꿔"],
    "summarize": ["요약", "줄여", "핵심", "요점", "정리"],
    "code_help": ["코드", "에러", "오류", "버그", "파이썬", "python"],
    "data_analysis": ["계산", "평균", "표준편차", "증가율", "늘었", "표 "],
    "write_email": ["메일", "메시지", "초안"],
}


def keyword_selector(request, skills):
    text = request.lower()
    scores = {
        name: sum(kw in text for kw in KEYWORDS.get(name, []))
        for name in skills
    }
    best = max(scores, key=scores.get)
    return (best if scores[best] > 0 else NONE), {}


def make_api_selector(model):
    import anthropic  # API 모드에서만 필요

    client = anthropic.Anthropic()

    def api_selector(request, skills):
        skill_text = "\n".join(f"- {n}: {d}" for n, d in skills.items())
        prompt = (
            f"사용 가능한 스킬 목록:\n{skill_text}\n\n"
            f"사용자 요청: {request}\n\n"
            "가장 알맞은 스킬 이름 하나만 답하세요. "
            "맞는 스킬이 없으면 none 이라고만 답하세요."
        )
        resp = client.messages.create(
            model=model,
            max_tokens=50,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = "".join(b.text for b in resp.content if b.type == "text")
        usage = {
            "raw": raw,
            "input_tokens": resp.usage.input_tokens,
            "output_tokens": resp.usage.output_tokens,
        }
        return raw, usage

    return api_selector


def normalize(raw, skills):
    """모델 답을 스킬 이름 / none / invalid 중 하나로 정리한다."""
    token = re.sub(r"[`'\".\s]", "", (raw or "").strip().lower())
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
            sum(r["picked"] not in (NONE, INVALID) for r in none_rows) / len(none_rows), 3
        ) if none_rows else None,
        # 스킬이 필요한데 none 을 고른 비율 (누락)
        "miss_rate": round(
            sum(r["picked"] == NONE for r in skill_rows) / len(skill_rows), 3
        ) if skill_rows else None,
        "invalid_count": sum(r["picked"] == INVALID for r in rows),
        "per_skill": per_skill,
        "confusion": {e: dict(c) for e, c in confusion.items()},
    }


def print_report(rows, metrics):
    print(f"정확도: {metrics['correct']}/{metrics['total']} ({metrics['accuracy']:.1%})")
    print("태그별:", metrics["accuracy_by_tag"])
    print("오발동률(none인데 스킬 선택):", metrics["false_trigger_rate"])
    print("누락률(스킬 필요한데 none):", metrics["miss_rate"])
    print("목록 밖 답변 수:", metrics["invalid_count"])
    print("\n스킬별 정밀도 / 재현율")
    for name, m in metrics["per_skill"].items():
        print(f"  {name:14s} P={m['precision']}  R={m['recall']}  (n={m['support']})")
    print("\n틀린 케이스")
    for r in rows:
        if not r["correct"]:
            print(f"  #{r['id']} [{r['tag']}] {r['expected']} -> {r['picked']} : {r['request']}")
            if r["picked"] == INVALID and "raw" in r:
                print(f"      모델 원문: {r['raw'][:80]!r}")


# ---------------------------------------------------------------- 실행

def run(selector, skills, cases):
    rows = []
    for case in cases:
        raw, extra = selector(case["request"], skills)
        picked = normalize(raw, skills)
        rows.append({
            "id": case["id"],
            "request": case["request"],
            "tag": case.get("tag", "clear"),
            "expected": case["expected"],
            "picked": picked,
            "correct": picked == case["expected"],
            **extra,
        })
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selector", choices=["keyword", "api"], default="keyword")
    ap.add_argument("--model", default="claude-haiku-5-5")
    ap.add_argument("--cases", default="cases_v2.json")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    skills = load_skills()
    with open(args.cases, encoding="utf-8") as f:
        cases = json.load(f)

    selector = keyword_selector if args.selector == "keyword" else make_api_selector(args.model)
    rows = run(selector, skills, cases)
    metrics = compute_metrics(rows, list(skills) + [NONE])
    print_report(rows, metrics)

    out = args.out or f"results_v2_{args.selector}.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"selector": args.selector, "metrics": metrics, "rows": rows},
                  f, ensure_ascii=False, indent=2)
    print(f"\n저장: {out}")


if __name__ == "__main__":
    main()
