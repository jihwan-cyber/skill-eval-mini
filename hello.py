import anthropic

client = anthropic.Anthropic()  # 환경변수 ANTHROPIC_API_KEY를 자동으로 읽음

response = client.messages.create(
    model="claude-haiku-5-5",
    max_tokens=100,
    messages=[{"role": "user", "content": "안녕! 한 문장으로 자기소개 해줘."}],
)

print(response.content[0].text)
print("입력 토큰:", response.usage.input_tokens, "/ 출력 토큰:", response.usage.output_tokens)
