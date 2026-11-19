"""내 AI 대화 기록에서 '대화를 시작한 첫 요청'만 뽑는다.

챗GPT 또는 Claude에서 내보낸 conversations.json 을 읽어서,
기준 날짜 이전에 시작한 대화의 첫 요청을 무작위로 골라 텍스트 파일로 저장한다.
기록은 이 컴퓨터 밖으로 나가지 않는다. 결과 파일을 직접 확인한 뒤 필요한 것만 공유한다.

  python3 extract_history.py 경로/conversations.json
  python3 extract_history.py 경로/conversations.json --before 2026-11-18 --limit 40 --seed 1

결과: history_requests.txt (번호 매긴 요청 목록) — .gitignore 에 들어 있어 커밋되지 않는다.
"""
import argparse
import json
import random
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

MAX_CHARS = 300  # 첫 요청에 긴 글·코드를 붙여 넣은 경우 앞부분만 남긴다

MASKS = [
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "[이메일]"),
    (re.compile(r"https?://\S+|www\.\S+"), "[링크]"),
    (re.compile(r"\b01[016789][-\s]?\d{3,4}[-\s]?\d{4}\b"), "[전화번호]"),
    (re.compile(r"\b0\d{1,2}[-\s]?\d{3,4}[-\s]?\d{4}\b"), "[전화번호]"),
    (re.compile(r"\b\d{6}[-\s]?[1-4]\d{6}\b"), "[주민번호]"),
    (re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b"), "[카드번호]"),
]


def mask(text):
    for pattern, repl in MASKS:
        text = pattern.sub(repl, text)
    return text


def clean(text):
    text = " ".join(text.split())  # 줄바꿈·여러 칸 공백을 한 칸으로
    text = mask(text)
    if len(text) > MAX_CHARS:
        text = text[:MAX_CHARS] + " …(이하 생략)"
    return text


def parse_time(value):
    """유닉스 시간(초) 또는 ISO 문자열을 UTC datetime 으로."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc)
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


# ---------------------------------------------------------------- 챗GPT

def chatgpt_first_request(conv):
    """mapping 트리에서 가장 먼저 쓴 사용자 메시지."""
    candidates = []
    for node in (conv.get("mapping") or {}).values():
        msg = (node or {}).get("message") or {}
        if (msg.get("author") or {}).get("role") != "user":
            continue
        content = msg.get("content") or {}
        parts = [p for p in content.get("parts") or [] if isinstance(p, str)]
        text = " ".join(parts).strip()
        if text:
            candidates.append((msg.get("create_time") or 0, text))
    if not candidates:
        return None
    return min(candidates, key=lambda c: c[0])[1]


# ---------------------------------------------------------------- Claude

def claude_first_request(conv):
    for msg in conv.get("chat_messages") or []:
        if msg.get("sender") != "human":
            continue
        text = (msg.get("text") or "").strip()
        if not text:
            text = " ".join(
                c.get("text", "") for c in msg.get("content") or []
                if isinstance(c, dict) and c.get("type") == "text"
            ).strip()
        if text:
            return text
    return None


def detect(conversations):
    sample = next((c for c in conversations if isinstance(c, dict)), {})
    if "mapping" in sample:
        return "chatgpt"
    if "chat_messages" in sample:
        return "claude"
    return None


def extract(conversations):
    kind = detect(conversations)
    if kind is None:
        raise SystemExit(
            "알 수 없는 형식입니다. 챗GPT 또는 Claude에서 내보낸 conversations.json 인지 확인해 주세요. "
            "(파일 내용은 공유하지 말고, 이 오류 문구만 알려 주세요.)"
        )
    items = []
    for conv in conversations:
        if not isinstance(conv, dict):
            continue
        if kind == "chatgpt":
            text, started = chatgpt_first_request(conv), parse_time(conv.get("create_time"))
        else:
            text, started = claude_first_request(conv), parse_time(conv.get("created_at"))
        if text:
            items.append({"started": started, "text": text})
    return kind, items


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path", help="내보낸 conversations.json 경로")
    ap.add_argument("--before", default="2026-11-18", help="이 날짜 이전에 시작한 대화만 (실험 시작일)")
    ap.add_argument("--limit", type=int, default=40, help="무작위로 뽑을 개수")
    ap.add_argument("--seed", type=int, default=1, help="무작위 표본의 시드 (같은 값이면 같은 표본)")
    ap.add_argument("--out", default="history_requests.txt")
    args = ap.parse_args()

    with open(args.path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise SystemExit("conversations.json 의 맨 바깥이 목록이 아닙니다. 내보낸 파일이 맞는지 확인해 주세요.")

    kind, items = extract(data)
    cutoff = datetime.fromisoformat(args.before).replace(tzinfo=timezone.utc)
    before = [it for it in items if it["started"] and it["started"] < cutoff]
    no_date = sum(1 for it in items if not it["started"])

    # 같은 요청이 여러 번 있으면 하나만 남긴다
    seen, unique = set(), []
    for it in before:
        key = clean(it["text"])
        if key not in seen:
            seen.add(key)
            unique.append(key)

    rng = random.Random(args.seed)
    sample = rng.sample(unique, min(args.limit, len(unique)))

    with open(args.out, "w", encoding="utf-8") as f:
        f.write(f"# 출처: {kind} 대화 기록 / {args.before} 이전 시작 / 무작위 {len(sample)}개 (시드 {args.seed})\n")
        f.write("# 공유하기 전에 개인정보·회사 정보가 남아 있는지 직접 확인하고, 그런 줄은 지우거나 고쳐 주세요.\n")
        f.write("# 지운 개수만 알려 주세요. 어떤 요청을 지웠는지는 알려 주지 않아도 됩니다.\n\n")
        for i, text in enumerate(sample, 1):
            f.write(f"{i}. {text}\n")

    print(f"형식: {kind}")
    print(f"대화 {len(data)}개 중 첫 요청이 있는 대화 {len(items)}개, {args.before} 이전 {len(before)}개"
          + (f" (날짜 없음 {no_date}개 제외)" if no_date else ""))
    print(f"중복 제거 후 {len(unique)}개 중 무작위 {len(sample)}개를 저장: {args.out}")
    if len(sample) < args.limit:
        print("참고: 요청이 목표 개수보다 적어서 있는 만큼만 저장했습니다.", file=sys.stderr)


if __name__ == "__main__":
    main()
