"""여러 라우터 설정을 여러 케이스 파일에서 한 번에 비교한다.

설정은 JSON 파일에 미리 적어 두고(실행 전에 커밋), 이 스크립트는 그대로 평가만 한다.
  python3 compare_configs.py configs_web_boundary.json cases_a.json cases_b.json --repeats 3
  python3 compare_configs.py configs_web_boundary.json cases_a.json --dry-run

설정 형식 (configs 의 각 항목):
  instruction : null 이면 기본 지시문, 문자열이면 그 지시문
  descriptions: {스킬: 설명} / improve.py 결과 파일 경로(best_config 의 description) / 위 둘의 목록(차례로 덮어씀)
"""
import argparse
import json
from pathlib import Path

from ablation import cost_stats, fmt_rate, to_markdown
from eval import (DEFAULT_INSTRUCTION, NONE, compute_metrics, keyword_selector, load_all_skills,
                  load_cases, make_api_selector)
from improve import evaluate


def resolve_descriptions(spec):
    if spec is None:
        return {}
    if isinstance(spec, dict):
        return dict(spec)
    if isinstance(spec, str):
        with open(spec, encoding="utf-8") as f:
            return dict(json.load(f)["best_config"]["descriptions"])
    merged = {}
    for part in spec:
        merged.update(resolve_descriptions(part))
    return merged


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("configs")
    ap.add_argument("cases", nargs="+")
    ap.add_argument("--model", default="claude-haiku-5-5")
    ap.add_argument("--effort", default="low", choices=["low", "medium", "high"])
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--outdir", default="improve_runs_web")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    with open(args.configs, encoding="utf-8") as f:
        spec = json.load(f)
    configs = [{"name": c["name"],
                "instruction": c.get("instruction") or DEFAULT_INSTRUCTION,
                "descriptions": resolve_descriptions(c.get("descriptions"))} for c in spec["configs"]]

    datasets = []
    for p in args.cases:
        dirs, cases = load_cases(p)
        datasets.append((Path(p).stem, dirs, cases))

    if args.dry_run:
        factory = lambda instruction: keyword_selector  # noqa: E731
    else:
        factory = lambda instruction: make_api_selector(args.model, args.effort, instruction)  # noqa: E731

    results = []
    for cfg in configs:
        for name, dirs, cases in datasets:
            base_skills = load_all_skills(dirs)
            unknown = set(cfg["descriptions"]) - set(base_skills)
            if unknown:
                raise SystemExit(f"{name}: 스킬 목록에 없는 description 이 있습니다: {unknown}")
            rows, m = evaluate(factory, base_skills, cfg, cases, args.repeats)
            c = cost_stats(rows, args.model)
            results.append({"variant": cfg["name"], "split": name, "config": cfg,
                            "metrics": m, "cost": c, "rows": rows})
            print(f"{cfg['name']:22s} {name:28s} 정확도 {m['accuracy']:.1%}  오발동 {fmt_rate(m['false_trigger_rate'])}  "
                  f"누락 {fmt_rate(m['miss_rate'])}  출력 {c['avg_output_tokens']}")
            first_ids = {x["id"] for x in cases if not x.get("followup")}
            if 0 < len(first_ids) < len(cases):
                sub = [r for r in rows if r["id"] in first_ids]
                sm = compute_metrics(sub, list(base_skills) + [NONE])
                results.append({"variant": cfg["name"], "split": f"{name}[첫 메시지]", "config": cfg,
                                "metrics": sm, "cost": cost_stats(sub, args.model), "rows_ref": name})

    md = to_markdown(results, args.model, args.effort, args.repeats).replace(
        "# 원인 분리 실험과 비용", "# 설정 비교")
    print("\n" + md)

    # 개인 기록(cases_history*)이 섞이면 원문이 담긴 결과를 따로 저장해 공개 저장소에 올라가지 않게 한다
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    groups = {"public": [r for r in results if not r["split"].startswith("cases_history")],
              "history": [r for r in results if r["split"].startswith("cases_history")]}
    stem = Path(args.configs).stem + ("_dry_run" if args.dry_run else "")
    for kind, rs in groups.items():
        if not rs:
            continue
        base = f"{stem}_cases_history" if kind == "history" else stem
        out, n = outdir / f"{base}.json", 2
        while out.exists():
            out, n = outdir / f"{base}_{n}.json", n + 1
        with open(out, "w", encoding="utf-8") as f:
            json.dump({"model": args.model, "effort": args.effort, "repeats": args.repeats,
                       "configs_file": args.configs, "results": rs}, f, ensure_ascii=False, indent=2)
        with open(out.with_suffix(".md"), "w", encoding="utf-8") as f:
            f.write(to_markdown(rs, args.model, args.effort, args.repeats).replace("# 원인 분리 실험과 비용", "# 설정 비교"))
        print(f"저장: {out}")


if __name__ == "__main__":
    main()
