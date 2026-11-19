"""스킬 선택 자동 개선 루프.

1. 학습셋(train)으로 현재 설정을 평가한다.
2. 틀린 케이스를 개선 모델에 보여 주고 지시문/스킬 description 수정안을 받는다.
3. 수정안으로 학습셋을 다시 평가해 정확도가 오를 때만 채택한다.
4. 2~3을 --iters 번 반복한 뒤, 개선 모델이 본 적 없는 테스트셋(test)으로
   원본 설정과 최종 설정을 비교한다.

원본 skills/*.md 는 수정하지 않는다. 개선된 설정은 --outdir 에 JSON으로 저장된다.

  python3 improve.py                 # 실제 실행 (ANTHROPIC_API_KEY 필요)
  python3 improve.py --dry-run       # API 없이 루프 흐름만 확인
"""
import argparse
import json
import re
from collections import Counter
from pathlib import Path

from eval import (
    DEFAULT_INSTRUCTION,
    NONE,
    compute_metrics,
    keyword_selector,
    load_all_skills,
    load_cases,
    make_api_selector,
    run,
)

MAX_DESC_LEN = 60

IMPROVER_PROMPT = """너는 AI 에이전트의 스킬 라우팅 설정을 개선하는 엔지니어다.
라우터 모델은 아래 '지시문'과 '스킬 목록(name: description)'만 보고, 사용자 요청마다 스킬 하나 또는 none을 고른다.

[현재 지시문]
{instruction}

[현재 스킬 목록]
{skill_text}

[현재 학습셋 성적]
{metrics_text}

[틀린 케이스] 요청 / 정답 / 모델이 고른 답(횟수)
{failure_text}

[이전에 시도했지만 채택되지 않은 수정안]
{rejected_text}

[할 일]
틀린 원인을 짧게 진단하고, 지시문과 스킬 description 중 필요한 것만 고쳐라.
규칙:
- 지금 맞히고 있는 케이스(특히 비슷한 스킬끼리의 구분)를 망치면 안 된다. 수정안은 학습셋 정확도가 올라갈 때만 채택된다.
- 틀린 케이스의 문장을 그대로 옮기거나 특정 단어를 나열하지 말고, 일반 원칙으로 고쳐라. 처음 보는 요청에서도 통해야 한다.
- 지시문은 반드시 "스킬 이름 하나 또는 none 만 답한다"는 출력 규칙을 유지해야 한다.
- description은 한국어 한 줄, {max_len}자 이내.
- 스킬을 추가하거나 삭제하지 마라.

출력: 아래 형식의 JSON 하나만 ```json 블록으로 답하라. descriptions에는 바꿀 스킬만 넣는다(없으면 {{}}).
```json
{{"diagnosis": "원인 진단", "instruction": "새 지시문 전체", "descriptions": {{"스킬이름": "새 description"}}}}
```"""


# ---------------------------------------------------------------- 개선 모델

def make_api_improver(model):
    import anthropic

    client = anthropic.Anthropic()

    def improve(prompt):
        kwargs = dict(
            model=model,
            max_tokens=16000,
            messages=[{"role": "user", "content": prompt}],
        )
        if model == "claude-opus-5-5":
            # 안전 분류기가 요청을 거절하면 서버에서 다른 모델로 이어서 처리한다.
            resp = client.beta.messages.create(
                betas=["server-side-fallback-2026-07-01"],
                fallbacks=[{"model": "claude-opus-4-8"}],
                **kwargs,
            )
        else:
            resp = client.messages.create(**kwargs)
        if resp.stop_reason == "refusal":
            raise RuntimeError("개선 모델이 요청을 거절함")
        return "".join(b.text for b in resp.content if b.type == "text")

    return improve


def dry_run_improver(prompt):
    """API 없이 흐름을 확인하기 위한 가짜 개선 모델."""
    return """```json
{"diagnosis": "(dry-run) 주제만 겹치는 질문에도 스킬을 고른다",
 "instruction": "사용자가 그 작업을 실제로 해 달라고 할 때만 스킬을 고르세요. 가장 알맞은 스킬 이름 하나만 답하고, 맞는 스킬이 없으면 none 이라고만 답하세요.",
 "descriptions": {"summarize": "주어진 긴 글이나 문서를 직접 짧게 요약한다"}}
```"""


def extract_json(text):
    m = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.S)
    if m:
        return json.loads(m.group(1))
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("JSON을 찾을 수 없음")
    return json.loads(text[start:end + 1])


def validate_proposal(p, base_skills):
    errors = []
    if not isinstance(p, dict):
        return ["JSON 객체가 아님"]
    instr = p.get("instruction")
    if not isinstance(instr, str) or not instr.strip():
        errors.append("instruction이 비어 있음")
    elif "none" not in instr.lower():
        errors.append("instruction에 none 출력 규칙이 없음")
    descs = p.get("descriptions") or {}
    if not isinstance(descs, dict):
        errors.append("descriptions가 객체가 아님")
        descs = {}
    for name, d in descs.items():
        if name not in base_skills:
            errors.append(f"없는 스킬: {name}")
        elif not isinstance(d, str) or not d.strip() or "\n" in d or len(d) > MAX_DESC_LEN:
            errors.append(f"{name}: description 형식 위반 (한 줄, {MAX_DESC_LEN}자 이내)")
    return errors


# ---------------------------------------------------------------- 평가

def effective_skills(base_skills, config):
    skills = dict(base_skills)
    skills.update(config["descriptions"])
    return skills


def evaluate(selector_factory, base_skills, config, cases, repeats):
    skills = effective_skills(base_skills, config)
    rows = run(selector_factory(config["instruction"]), skills, cases, repeats)
    return rows, compute_metrics(rows, list(skills) + [NONE])


def collect_failures(rows):
    agg = {}
    for r in rows:
        if r["correct"]:
            continue
        a = agg.setdefault(r["id"], {"request": r["request"], "expected": r["expected"], "picked": Counter()})
        a["picked"][r["picked"]] += 1
    return list(agg.values())


def metrics_line(m):
    return (f"정확도 {m['correct']}/{m['total']} ({m['accuracy']:.1%}), "
            f"태그별 {m['accuracy_by_tag']}, 오발동률 {m['false_trigger_rate']}, "
            f"누락률 {m['miss_rate']}, 목록 밖 {m['invalid_count']}, 빈 답 {m['empty_count']}")


def build_prompt(config, skills, metrics, failures, rejected):
    skill_text = "\n".join(f"- {n}: {d}" for n, d in skills.items())
    failure_text = "\n".join(
        f"- {f['request']} / 정답 {f['expected']} / " + ", ".join(f"{k}({v})" for k, v in f["picked"].items())
        for f in failures
    )
    rejected_text = "\n".join(
        f"- 지시문: {r['instruction']} / description 변경: {r['descriptions']} -> 학습셋 {r['accuracy']:.1%}"
        f" / 거절 이유: {r.get('reason', '학습셋 정확도가 오르지 않음')}"
        for r in rejected
    ) or "(없음)"
    return IMPROVER_PROMPT.format(
        instruction=config["instruction"], skill_text=skill_text,
        metrics_text=metrics_line(metrics), failure_text=failure_text,
        rejected_text=rejected_text, max_len=MAX_DESC_LEN,
    )


# ---------------------------------------------------------------- 루프

def improve_loop(selector_factory, improver, base_skills, train, iters, repeats, val=None, log=print):
    """val 이 주어지면, 학습셋 정확도가 오르고 검증셋 정확도가 떨어지지 않을 때만 채택한다.
    개선 모델에게 검증셋 내용은 보여 주지 않고, 검증셋 때문에 거절됐다는 사실만 알린다."""
    config = {"instruction": DEFAULT_INSTRUCTION, "descriptions": {}}
    rows, metrics = evaluate(selector_factory, base_skills, config, train, repeats)
    log(f"[0] 원본 설정: {metrics_line(metrics)}")
    val_metrics = None
    if val:
        _, val_metrics = evaluate(selector_factory, base_skills, config, val, repeats)
        log(f"    검증셋: {metrics_line(val_metrics)}")
    history = [{"iter": 0, "status": "baseline", "config": config, "metrics": metrics, "val_metrics": val_metrics}]
    rejected = []

    for i in range(1, iters + 1):
        failures = collect_failures(rows)
        if not failures:
            log(f"[{i}] 학습셋을 전부 맞혀서 중단")
            break
        prompt = build_prompt(config, effective_skills(base_skills, config), metrics, failures, rejected)
        try:
            proposal = extract_json(improver(prompt))
        except (ValueError, RuntimeError) as e:  # json.JSONDecodeError 는 ValueError
            log(f"[{i}] 수정안을 받지 못함: {e}")
            history.append({"iter": i, "status": "error", "error": str(e)})
            continue
        errors = validate_proposal(proposal, base_skills)
        if errors:
            log(f"[{i}] 형식 위반으로 거절: {errors}")
            history.append({"iter": i, "status": "invalid", "proposal": proposal, "errors": errors})
            continue

        candidate = {
            "instruction": proposal["instruction"].strip(),
            "descriptions": {**config["descriptions"], **(proposal.get("descriptions") or {})},
        }
        c_rows, c_metrics = evaluate(selector_factory, base_skills, candidate, train, repeats)
        c_val = None
        if c_metrics["accuracy"] <= metrics["accuracy"]:
            accepted, reason = False, "학습셋 정확도가 오르지 않음"
        elif val:
            # 학습셋은 올랐을 때만 검증셋을 돌린다 (호출 절약)
            _, c_val = evaluate(selector_factory, base_skills, candidate, val, repeats)
            if c_val["accuracy"] < val_metrics["accuracy"]:
                accepted = False
                reason = (f"학습셋은 올랐지만 검증셋(내용 비공개) 정확도가 "
                          f"{val_metrics['accuracy']:.1%} -> {c_val['accuracy']:.1%} 로 떨어짐")
            else:
                accepted, reason = True, "학습셋 상승, 검증셋 유지 또는 상승"
        else:
            accepted, reason = True, "학습셋 상승"
        log(f"[{i}] {'채택' if accepted else '거절'} ({reason}): {metrics_line(c_metrics)}")
        if c_val:
            log(f"     검증셋: {metrics_line(c_val)}")
        log(f"     진단: {proposal.get('diagnosis', '')}")
        history.append({
            "iter": i, "status": "accepted" if accepted else "rejected", "reason": reason,
            "diagnosis": proposal.get("diagnosis"), "config": candidate,
            "metrics": c_metrics, "val_metrics": c_val,
        })
        if accepted:
            config, rows, metrics = candidate, c_rows, c_metrics
            if c_val:
                val_metrics = c_val
        else:
            rejected.append({**candidate, "accuracy": c_metrics["accuracy"], "reason": reason})

    return config, history


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--train", default="cases_v3.json")
    ap.add_argument("--test", default="cases_test.json")
    ap.add_argument("--val", default=None, help="채택 여부를 정할 검증셋 (개선 모델에게는 비공개)")
    ap.add_argument("--holdout", default=None, help="마지막 비교에만 쓰는 추가 평가셋")
    ap.add_argument("--model", default="claude-haiku-5-5", help="스킬을 고르는 라우터 모델")
    ap.add_argument("--effort", default="low", choices=["low", "medium", "high"])
    ap.add_argument("--improver-model", default="claude-opus-5-5", help="수정안을 만드는 모델")
    ap.add_argument("--iters", type=int, default=3)
    ap.add_argument("--repeats", type=int, default=2)
    ap.add_argument("--outdir", default="improve_runs")
    ap.add_argument("--dry-run", action="store_true", help="API 없이 키워드 선택기와 가짜 개선 모델로 실행")
    args = ap.parse_args()

    train_dirs, train = load_cases(args.train)
    sets = {"test": load_cases(args.test)}
    if args.val:
        sets["val"] = load_cases(args.val)
    if args.holdout:
        sets["holdout"] = load_cases(args.holdout)
    names = ["train"] + list(sets)
    all_sets = {"train": (train_dirs, train), **sets}
    for a in names:
        if all_sets[a][0] != train_dirs:
            raise SystemExit(f"{a} 의 skills_dirs 가 학습셋과 다릅니다")
        for b in names[names.index(a) + 1:]:
            if {c["request"] for c in all_sets[a][1]} & {c["request"] for c in all_sets[b][1]}:
                raise SystemExit(f"{a} 와 {b} 에 같은 요청이 있습니다")
    test = sets["test"][1]
    val = sets["val"][1] if args.val else None
    holdout = sets["holdout"][1] if args.holdout else None
    base_skills = load_all_skills(train_dirs)

    if args.dry_run:
        selector_factory = lambda instruction: keyword_selector  # noqa: E731
        improver = dry_run_improver
    else:
        selector_factory = lambda instruction: make_api_selector(args.model, args.effort, instruction)  # noqa: E731
        improver = make_api_improver(args.improver_model)

    extra = (f", 검증셋 {len(val)}개" if val else "") + (f", 보류셋 {len(holdout)}개" if holdout else "")
    print(f"학습셋 {len(train)}개 x {args.repeats}회, 테스트셋 {len(test)}개{extra}, 최대 {args.iters}회 개선\n")
    best, history = improve_loop(selector_factory, improver, base_skills, train, args.iters, args.repeats, val=val)

    baseline = {"instruction": DEFAULT_INSTRUCTION, "descriptions": {}}

    def compare(title, cases):
        print(f"\n[{title}] 원본과 최종 설정 비교")
        res = {}
        for label, cfg in [("원본", baseline), ("개선", best)]:
            rows, m = evaluate(selector_factory, base_skills, cfg, cases, args.repeats)
            res[label] = {"config": cfg, "metrics": m, "rows": rows}
            print(f"  {label}: {metrics_line(m)}")
        return res

    results = compare("테스트셋", test)
    holdout_results = compare("보류셋", holdout) if holdout else None

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    out = outdir / ("summary_dry_run.json" if args.dry_run else "summary.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump({
            "args": vars(args), "history": history, "best_config": best,
            "test": {k: {"config": v["config"], "metrics": v["metrics"]} for k, v in results.items()},
            "test_rows": {k: v["rows"] for k, v in results.items()},
            **({"holdout": {k: {"config": v["config"], "metrics": v["metrics"]} for k, v in holdout_results.items()},
                "holdout_rows": {k: v["rows"] for k, v in holdout_results.items()}} if holdout_results else {}),
        }, f, ensure_ascii=False, indent=2)
    print(f"\n최종 지시문: {best['instruction']}")
    if best["descriptions"]:
        print("바뀐 description:")
        for n, d in best["descriptions"].items():
            print(f"  {n}: {base_skills[n]}  ->  {d}")
    print(f"저장: {out}")


if __name__ == "__main__":
    main()
