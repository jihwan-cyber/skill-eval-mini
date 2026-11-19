"""사용 현황 표: 결과 파일에서 호출 수, 성공률, 응답 시간, 토큰을 집계한다.

요청 원문과 모델 응답 본문은 읽어도 표에 넣지 않는다. 결과 파일은 읽기만 한다.
파일에 없는 값은 "기록 없음"으로 적는다.

  python3 dashboard.py                    # 터미널 출력 + dashboard.md
  python3 dashboard.py --out other.md     # 다른 이름으로 저장
  python3 dashboard.py --include-private  # 커밋하지 않는 본인 기록 결과(cases_history*)도 포함

용어
- 호출 수: 라우터 모델을 부른 횟수. 결과 파일의 행(row) 하나가 호출 하나다.
- 성공률: 스킬 이름 또는 none 을 제대로 답한 호출의 비율 (빈 답, 목록 밖 답은 실패).
  정답 여부와는 다르다.
- keyword 선택기는 API 를 부르지 않으므로 토큰이 없다 ("해당 없음").
"""
import argparse
import json
from pathlib import Path

NO_RECORD = "기록 없음"
NOT_APPLICABLE = "해당 없음"
FAILED_PICKS = {"invalid", "empty"}


def _num(n):
    return f"{n:,}"


def _rate(ok, total):
    return f"{ok / total:.1%}" if total else NO_RECORD


def known_names(root):
    names = {"none"}
    for d in ("skills", "skills_extra", "skills_search"):
        for p in (Path(root) / d).glob("*/SKILL.md"):
            names.add(p.parent.name)
    return names


def summarize_rows(rows, names):
    """행 목록에서 집계만 뽑는다. request·raw 같은 본문은 쓰지 않는다."""
    total = len(rows)
    ok = sum(1 for r in rows if r.get("picked") not in FAILED_PICKS and r.get("picked") in names)
    has_tokens = any("input_tokens" in r for r in rows)
    entry = {"calls": total, "success": _rate(ok, total), "latency": NO_RECORD}
    if has_tokens:
        tin = sum(r.get("input_tokens", 0) for r in rows)
        tout = sum(r.get("output_tokens", 0) for r in rows)
        entry.update(tokens_in=_num(tin), tokens_out=_num(tout),
                     per_call=f"{tin / total:.0f} / {tout / total:.0f}" if total else NO_RECORD)
    return entry, has_tokens


def summarize_metrics(m):
    """행이 저장되지 않고 집계(metrics)만 남은 평가."""
    total = m.get("total", 0)
    bad = m.get("invalid_count", 0) + m.get("empty_count", 0)
    return {"calls": total, "success": _rate(total - bad, total), "latency": NO_RECORD,
            "tokens_in": NO_RECORD, "tokens_out": NO_RECORD, "per_call": NO_RECORD}


def blocks_from_file(path, names):
    """결과 파일 하나에서 (구분, 모델, 선택기, 집계) 묶음을 만든다."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    out = []

    def add_rows(label, rows, model, selector=None):
        entry, has_tokens = summarize_rows(rows, names)
        sel = selector or ("api" if has_tokens else "keyword")
        if not has_tokens:
            entry.update(tokens_in=NOT_APPLICABLE, tokens_out=NOT_APPLICABLE, per_call=NOT_APPLICABLE)
        if sel == "keyword":  # 모델을 부르지 않는다 (파일의 model 값은 기본 인자일 뿐)
            model = NOT_APPLICABLE
        out.append((label, model, sel, entry))

    if isinstance(data, list):  # v1: 행 목록만
        add_rows("전체", data, NO_RECORD)
        return out

    args = data.get("args", {})
    model = data.get("model") or args.get("model") or NO_RECORD

    if "rows" in data:  # eval.py 결과
        add_rows("전체", data["rows"], model, data.get("selector"))

    for r in data.get("results", []):  # ablation.py / compare_configs.py 결과
        if "rows" in r:  # rows_ref(부분 집합)는 이미 센 호출이라 건너뛴다
            add_rows(f"{r.get('variant')} / {r.get('split')}", r["rows"], model)

    for key, title in (("test_rows", "테스트셋"), ("holdout_rows", "보류셋")):  # improve.py 결과
        for label, rows in data.get(key, {}).items():
            add_rows(f"{title} / {label}", rows, model)

    history = data.get("history", [])
    for h in history:
        if h.get("metrics"):
            out.append((f"학습셋 평가 / {h.get('iter')}회차", model, "api", summarize_metrics(h["metrics"])))
        if h.get("val_rows"):
            add_rows(f"검증셋 평가 / {h.get('iter')}회차", h["val_rows"], model)
        elif h.get("val_metrics"):
            out.append((f"검증셋 평가 / {h.get('iter')}회차", model, "api", summarize_metrics(h["val_metrics"])))
    improver_calls = sum(1 for h in history if h.get("iter", 0) >= 1)
    if improver_calls:
        out.append(("개선 모델 호출 (수정안 생성)", args.get("improver_model", NO_RECORD), "api",
                    {"calls": improver_calls, "success": NO_RECORD, "latency": NO_RECORD,
                     "tokens_in": NO_RECORD, "tokens_out": NO_RECORD, "per_call": NO_RECORD}))
    return out


def find_result_files(root, include_private=False):
    root = Path(root)
    files = set(root.glob("results*.json"))
    for d in root.glob("improve_runs*"):
        if d.is_dir():
            files |= set(d.rglob("*.json"))
    files = [f for f in files if "dry_run" not in f.name]
    if not include_private:
        files = [f for f in files if "cases_history" not in f.name]
    return sorted(files)


def build_table(root, include_private=False):
    names = known_names(root)
    header = ["파일", "구분", "모델", "선택기", "호출 수", "성공률", "응답 시간",
              "입력 토큰 합계", "출력 토큰 합계", "호출당 입력 / 출력"]
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    api_calls = api_known_tokens_calls = tin_total = tout_total = 0
    for f in find_result_files(root, include_private):
        rel = f.relative_to(root).as_posix()
        for label, model, sel, e in blocks_from_file(f, names):
            lines.append("| " + " | ".join([
                f"`{rel}`", label, model, sel, _num(e["calls"]), e["success"], e["latency"],
                e["tokens_in"], e["tokens_out"], e["per_call"]]) + " |")
            if sel == "api":
                api_calls += e["calls"]
                if e["tokens_in"] not in (NO_RECORD, NOT_APPLICABLE):
                    api_known_tokens_calls += e["calls"]
                    tin_total += int(e["tokens_in"].replace(",", ""))
                    tout_total += int(e["tokens_out"].replace(",", ""))
    lines.append("| " + " | ".join([
        "**합계 (API 호출)**", "", "", "api", f"**{_num(api_calls)}**", "", NO_RECORD,
        f"{_num(tin_total)} (토큰 기록이 있는 {_num(api_known_tokens_calls)}회)",
        f"{_num(tout_total)}", ""]) + " |")
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(Path(__file__).resolve().parent))
    ap.add_argument("--out", default="dashboard.md")
    ap.add_argument("--include-private", action="store_true")
    args = ap.parse_args()

    table = build_table(args.root, args.include_private)
    doc = ("# 사용 현황\n\n"
           "`dashboard.py`가 결과 파일에서 집계만 뽑아 만든 표입니다. 요청 원문과 모델 응답 본문은 넣지 않았습니다.\n"
           "- 호출 수: 라우터 모델을 부른 횟수(결과 파일의 행 하나 = 호출 하나)\n"
           "- 성공률: 스킬 이름 또는 none을 제대로 답한 호출의 비율(정답 여부와 다름)\n"
           "- 응답 시간: 결과 파일에 기록하지 않아 모두 \"기록 없음\"\n"
           "- keyword 선택기는 API를 부르지 않아 토큰이 \"해당 없음\"\n"
           "- 학습셋·검증셋 평가 중 일부와 개선 모델 호출은 집계만 남아 토큰이 \"기록 없음\"\n"
           "- 본인 기록(cases_history*) 결과는 공개하지 않으므로 기본으로 제외\n\n" + table)
    print(table)
    out = Path(args.out)
    if not out.is_absolute():
        out = Path.cwd() / out
    out.write_text(doc, encoding="utf-8")
    print(f"저장: {out}")


if __name__ == "__main__":
    main()
