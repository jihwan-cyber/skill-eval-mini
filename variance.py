"""같은 설정을 여러 번 돌렸을 때 정확도가 얼마나 흔들리는지 계산한다.

결과 파일의 행에는 몇 번째 반복(trial)인지가 적혀 있다. 반복 한 번은 데이터 전체를 한 바퀴 도는
독립된 실행과 같으므로, 반복마다 정확도를 따로 계산해 평균·최소·최대·폭·표준편차를 낸다.
결과 파일은 읽기만 하고, 요청 원문과 모델 응답은 표에 넣지 않는다.

  python3 variance.py improve_runs_web/configs_web_boundary.json
  python3 variance.py 결과파일1.json 결과파일2.json --out variance.md
"""
import argparse
import json
import statistics
from collections import defaultdict
from pathlib import Path


def per_trial_accuracy(rows):
    """{반복 번호: 정확도}. trial 이 없는 행은 1번 반복으로 본다."""
    tally = defaultdict(lambda: [0, 0])
    for r in rows:
        t = r.get("trial", 1)
        tally[t][0] += bool(r.get("correct"))
        tally[t][1] += 1
    return {t: c / n for t, (c, n) in sorted(tally.items()) if n}


def stats(accs):
    vals = list(accs.values())
    return {
        "runs": len(vals),
        "mean": statistics.fmean(vals),
        "min": min(vals),
        "max": max(vals),
        "range": max(vals) - min(vals),
        "stdev": statistics.pstdev(vals) if len(vals) > 1 else 0.0,
    }


def entries(path):
    """결과 파일에서 (설정, 데이터, 행) 묶음을 꺼낸다."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, list):
        yield "전체", Path(path).stem, data
        return
    if "rows" in data:
        yield data.get("selector", "전체"), Path(path).stem, data["rows"]
    for r in data.get("results", []):
        if "rows" in r:
            yield r.get("variant"), r.get("split"), r["rows"]


def build_table(paths):
    lines = ["| 결과 파일 | 설정 | 데이터 | 실행 수 | 평균 | 최소 | 최대 | 폭 (최대-최소) | 표준편차 |",
             "|---|---|---|---|---|---|---|---|---|"]
    for p in paths:
        for variant, split, rows in entries(p):
            s = stats(per_trial_accuracy(rows))
            lines.append(
                f"| `{Path(p).as_posix()}` | {variant} | {split} | {s['runs']} | {s['mean']:.1%} | {s['min']:.1%} | "
                f"{s['max']:.1%} | {s['range'] * 100:.1f}%p | {s['stdev'] * 100:.1f}%p |")
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--out", default=None, help="표를 저장할 md 파일 (생략하면 터미널에만 출력)")
    args = ap.parse_args()
    table = build_table(args.files)
    print(table)
    if args.out:
        Path(args.out).write_text(
            "# 같은 설정의 반복 실행 흔들림\n\n`variance.py`가 결과 파일의 반복(trial)마다 정확도를 따로 계산한 표입니다.\n\n" + table,
            encoding="utf-8")
        print(f"저장: {args.out}")


if __name__ == "__main__":
    main()
