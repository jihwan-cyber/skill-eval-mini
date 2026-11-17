import json
import anthropic

client = anthropic.Anthropic()

SKILLS = {
    "translate": "문장을 다른 언어로 번역한다",
    "summarize": "긴 글이나 자료를 짧게 요약한다",
    "code_help": "코드를 작성하거나 고친다",
}
skill_text = "\n".join(f"- {name}: {desc}" for name, desc in SKILLS.items())

with open("cases.json", encoding="utf-8") as f:
    cases = json.load(f)

results = []
for case in cases:
    prompt = (
        f"사용 가능한 스킬 목록:\n{skill_text}\n\n"
        f"사용자 요청: {case['request']}\n\n"
        "가장 알맞은 스킬 이름 하나만 답하세요. 맞는 스킬이 없으면 none 이라고만 답하세요."
    )
    response = client.messages.create(
        model="claude-haiku-5-5",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )
    texts = [b.text for b in response.content if b.type == "text"]
    picked = (texts[0] if texts else "").strip().lower()
    results.append({
        "id": case["id"],
        "request": case["request"],
        "expected": case["expected"],
        "picked": picked,
        "correct": picked == case["expected"],
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
    })

with open("results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

correct = sum(r["correct"] for r in results)
print(f"정확도: {correct}/{len(results)}")
for r in results:
    print(r["id"], r["expected"], "->", r["picked"], "O" if r["correct"] else "X")
