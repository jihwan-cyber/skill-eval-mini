# skill-eval-mini

AI 에이전트의 **스킬 선택**을 평가하는 축소판입니다.
모델은 각 스킬의 `name`과 `description`만 보고 사용자 요청에 맞는 스킬을 고릅니다.
스킬 설명이 서로 겹칠 때 생기는 오선택·오발동·누락을 측정하는 것이 목적입니다.

## 구성
| 파일 | 역할 |
|---|---|
| `skills/<name>/SKILL.md` | 평가 대상 스킬 5개 (frontmatter: name, description) |
| `skills_extra/<name>/SKILL.md` | v3용 헷갈리는 스킬 2개 (report_write, proofread) |
| `load_skills.py` | SKILL.md 를 읽어 `{name: description}` 으로 반환. 잘못된 파일은 경고 후 건너뜀 |
| `cases_v2.json` | 테스트셋 20개: clear 10 / overlap 6 / none 4 (스킬 5개) |
| `cases_v3.json` | 테스트셋 32개: clear 7 / overlap 13 / ambiguous 4 / none 8 (스킬 7개) |
| `eval.py` | 선택기를 바꿔 끼워 평가하고 지표를 계산 |
| `improve.py` | 자동 개선 루프: 틀린 케이스로 지시문·description 수정안을 받아 좋아질 때만 채택 |
| `cases_test.json` | 개선 루프 채점용 테스트셋 24개 (개선 모델은 보지 않음) |
| `ablation.py` | 개선 결과를 지시문/description으로 나눠 효과와 비용을 비교 |
| `run.py`, `cases.json` | v1 (스킬 3개, 9케이스) |

## 실행
```bash
python3 eval.py --selector keyword   # API 없이 도는 키워드 기준선
python3 eval.py --selector api       # Claude API (ANTHROPIC_API_KEY 필요)
python3 eval.py --selector api --cases cases_v3.json --repeats 3   # v3, 3회 반복
```

옵션: `--effort low|medium|high` (기본 low), `--repeats N`, `--model`, `--out`

## 지표
- 정확도 (전체 / 태그별: clear, overlap, none)
- 스킬별 정밀도·재현율, 혼동 행렬
- 오발동률: 스킬이 필요 없는데 스킬을 고른 비율
- 누락률: 스킬이 필요한데 none 을 고른 비율
- 목록 밖 답변 수 / 빈 답변 수 (빈 답변은 `stop_reason`을 함께 기록)
- 일관성: 같은 요청을 반복했을 때 매번 같은 답을 한 케이스의 비율 (`--repeats` 2 이상)

`overlap` 케이스에는 헷갈리기 쉬운 스킬을 `confusable` 필드로 적어 두었습니다.
예를 들어 "매출 데이터를 3줄로 정리"는 summarize 와 data_analysis 의 경계에 있는 요청입니다.

v3의 `ambiguous` 케이스는 정답이 둘일 수 있어서 `acceptable` 목록에 든 답이면 정답으로 칩니다.
v3 케이스 파일은 `skills_dirs`로 어떤 스킬 폴더를 쓸지 직접 정합니다.

## 지금까지의 결과 (claude-haiku-5-5, v2)
| 설정 | 정확도 | 출력 토큰 합계 |
|---|---|---|
| max_tokens=50 (버그) | 15/20 | - (5건이 생각하다 잘려 빈 답) |
| effort low | 20/20 | 158 |
| effort medium | 20/20 | 432 |

## 자동 개선 루프
```bash
python3 improve.py --dry-run   # API 없이 흐름만 확인
python3 improve.py             # 라우터 haiku-5-5(effort low), 개선 모델 opus-5-5, 3회 반복
```
1. 학습셋(`cases_v3.json`)으로 현재 설정(지시문 + description)을 평가합니다.
2. 틀린 케이스와 이전에 거절된 수정안을 개선 모델에 보여 주고 수정안(JSON)을 받습니다.
3. 형식 검사를 통과하고 학습셋 정확도가 올라갈 때만 채택합니다.
4. 마지막에 개선 모델이 본 적 없는 `cases_test.json`으로 원본과 개선본을 비교합니다.

원본 `skills/`는 수정하지 않습니다. 결과는 `improve_runs/summary.json`에 저장됩니다.
학습셋 점수만 오르고 테스트셋 점수가 그대로라면 과적합으로 봅니다.

### 자동 개선 결과 (claude-haiku-5-5 라우터, claude-opus-5-5 개선 모델, 1회 만에 수렴)
| | 원본 | 개선 후 |
|---|---|---|
| 학습셋 (v3, 32개 x 2회) | 84.4% | 100% |
| 테스트셋 (처음 보는 24개 x 2회) | 91.7% (오발동 16.7%) | 100% (오발동 0%) |
| 호출당 입력 / 출력 토큰 (테스트셋) | 298 / 37 | 579 / 6 |
| 1천 회 호출당 예상 비용 | $0.048 | $0.061 (+26%) |

한계: 케이스 수가 적고(테스트셋 none 12개), 학습셋과 테스트셋을 같은 사람이 만들었습니다.

## 원인 분리 실험
```bash
python3 ablation.py --dry-run  # API 없이 흐름만 확인
python3 ablation.py            # 원본 / 지시문만 / description만 / 둘 다 x 학습셋·테스트셋
```
결과는 `improve_runs/ablation.md` 표로 저장됩니다.
