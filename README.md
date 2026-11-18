# skill-eval-mini

AI 에이전트의 **스킬 선택**을 평가하는 축소판입니다.
모델은 각 스킬의 `name`과 `description`만 보고 사용자 요청에 맞는 스킬을 고릅니다.
스킬 설명이 서로 겹칠 때 생기는 오선택·오발동·누락을 측정하는 것이 목적입니다.

## 구성
| 파일 | 역할 |
|---|---|
| `skills/<name>/SKILL.md` | 평가 대상 스킬 5개 (frontmatter: name, description) |
| `load_skills.py` | SKILL.md 를 읽어 `{name: description}` 으로 반환. 잘못된 파일은 경고 후 건너뜀 |
| `cases_v2.json` | 테스트셋 20개: clear 10 / overlap 6 / none 4 |
| `eval.py` | 선택기를 바꿔 끼워 평가하고 지표를 계산 |
| `run.py`, `cases.json` | v1 (스킬 3개, 9케이스) |

## 실행
```bash
python3 eval.py --selector keyword   # API 없이 도는 키워드 기준선
python3 eval.py --selector api       # Claude API (ANTHROPIC_API_KEY 필요)
```

## 지표
- 정확도 (전체 / 태그별: clear, overlap, none)
- 스킬별 정밀도·재현율, 혼동 행렬
- 오발동률: 스킬이 필요 없는데 스킬을 고른 비율
- 누락률: 스킬이 필요한데 none 을 고른 비율
- 목록 밖 답변 수: 스킬 목록에 없는 이름을 답한 경우

`overlap` 케이스에는 헷갈리기 쉬운 스킬을 `confusable` 필드로 적어 두었습니다.
예를 들어 "매출 데이터를 3줄로 정리"는 summarize 와 data_analysis 의 경계에 있는 요청입니다.
