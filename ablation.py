"""원인 분리 실험(ablation)과 비용 비교.

improve.py 가 찾은 개선 설정(지시문 + description)을 나눠서,
어느 쪽이 효과를 냈는지와 정확도를 얻는 대신 비용이 얼마나 늘었는지를 본다.

  원본          : 기본 지시문 + 원본 description
  지시문만      : 개선 지시문 + 원본 description
  description만 : 기본 지시문 + 개선 description
  둘 다         : 개선 지시문 + 개선 description

  python3 ablation.py            # 실제 실행 (ANTHROPIC_API_KEY 필요)
  python3 ablation.py --dry-run  # API 없이 흐름만 확인
"""
import argparse
import json
from pathlib import Path

from eval import DEFAULT_INSTRUCTION, keyword_selector, load_all_skills, load_cases, make_api_selector
from improve import evaluate

# 1M 토큰당 달러 (claude-haiku-5-5, 프롬프트 100K 토큰 이하 기준).
# 가격은 바뀔 수 있으니 실제 청구서와 다르면 이 값을 고친다.
PRICE_PER_M = {"claude-haiku-5-5": (0.10, 0.50)}


def variants(best):
    base = {"instruction": DEFAULT_INSTRUCTION, "descriptions": {}}
    return [
        ("원본", base),
        ("지시문만", {"instruction": best["instruction"], "descriptions": {}}),
        ("description만", {"instruction": DEFAULT_INSTRUCTION, "descriptions": best["descriptions"]}),
        ("둘 다", best),
    ]


def cost_stats(rows, model):
    n = len(rows) or 1
    inp = sum(r.get("input_tokens", 0) for r in rows) / n
    out = sum(r.get("output_tokens", 0) for r in rows) / n
    pin, pout = PRICE_PER_M.get(model, (None, None))
    usd_per_1k_calls = (inp * pin + out * pout) / 1e6 * 1000 if pin is not None else None
    return {"avg_input_tokens": round(inp, 1), "avg_output_tokens": round(out, 1),
            "usd_per_1k_calls": round(usd_per_1k_calls, 4) if usd_per_1k_calls is not None else None}


def fmt_rate(x):
    return "-" if x is None else f"{x:.1%}"


def to_markdown(results, model, effort, repeats):
    lines = [
        f"# 원인 분리 실험과 비용 ({model}, effort {effort}, 각 케이스 {repeats}회)",
        "",
        "| 조합 | 데이터 | 정확도 | 오발동률 | 누락률 | 일관성 | 호출당 입력 토큰 | 호출당 출력 토큰 | 1천 회당 비용($) |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in results:
        m, c = r["metrics"], r["cost"]
        usd = "-" if c["usd_per_1k_calls"] is None else f"{c['usd_per_1k_calls']:.4f}"
        lines.append(
            f"| {r['variant']} | {r['split']} | {m['correct']}/{m['total']} ({m['accuracy']:.1%}) | "
            f"{fmt_rate(m['false_trigger_rate'])} | {fmt_rate(m['miss_rate'])} | {fmt_rate(m['consistency'])} | "
            f"{c['avg_input_tokens']} | {c['avg_output_tokens']} | {usd} |"
        )
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--summary", default="improve_runs/summary.json", help="improve.py 결과 파일")
    ap.add_argument("--model", default=None, help="기본값: summary 에 기록된 라우터 모델")
    ap.add_argument("--effort", default=None, help="기본값: summary 에 기록된 effort")
    ap.add_argument("--repeats", type=int, default=2)
    ap.add_argument("--cases", default=None,
                    help="학습셋/테스트셋 대신 이 케이스 파일 하나로 네 조합을 평가 (예: 외부 테스트셋)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    with open(args.summary, encoding="utf-8") as f:
        summary = json.load(f)
    run_args = summary["args"]
    model = args.model or run_args["model"]
    effort = args.effort or run_args["effort"]
    best = summary["best_config"]

    splits = []
    if args.cases:
        dirs, cases = load_cases(args.cases)
        splits.append((Path(args.cases).stem, dirs, cases))
    else:
        for name in ("train", "test"):
            dirs, cases = load_cases(run_args[name])
            splits.append((name, dirs, cases))
    base_skills = load_all_skills(splits[0][1])

    if args.dry_run:
        factory = lambda instruction: keyword_selector  # noqa: E731
    else:
        factory = lambda instruction: make_api_selector(model, effort, instruction)  # noqa: E731

    results = []
    for vname, cfg in variants(best):
        for split, _, cases in splits:
            rows, m = evaluate(factory, base_skills, cfg, cases, args.repeats)
            c = cost_stats(rows, model)
            results.append({"variant": vname, "split": split, "config": cfg,
                            "metrics": m, "cost": c, "rows": rows})
            print(f"{vname:14s} {split:5s} 정확도 {m['accuracy']:.1%}  오발동 {fmt_rate(m['false_trigger_rate'])}  "
                  f"누락 {fmt_rate(m['miss_rate'])}  입력 {c['avg_input_tokens']}  출력 {c['avg_output_tokens']}")

    md = to_markdown(results, model, effort, args.repeats)
    print("\n" + md)

    outdir = Path(args.summary).parent
    suffix = (f"_{Path(args.cases).stem}" if args.cases else "") + ("_dry_run" if args.dry_run else "")
    with open(outdir / f"ablation{suffix}.json", "w", encoding="utf-8") as f:
        json.dump({"model": model, "effort": effort, "repeats": args.repeats, "results": results},
                  f, ensure_ascii=False, indent=2)
    with open(outdir / f"ablation{suffix}.md", "w", encoding="utf-8") as f:
        f.write(md)
    print(f"저장: {outdir / f'ablation{suffix}.json'}, {outdir / f'ablation{suffix}.md'}")


if __name__ == "__main__":
    main()
