# 작업 규칙 (AI 코딩 에이전트용)
1. API 키, `.env`, 대화 기록 파일(`conversations.json`, `history_requests*.txt`, `cases_history*`)은 절대 커밋하지 않는다.
2. README나 보고서의 결과 숫자를 바꾸기 전에 근거가 되는 결과 파일(`results_*.json`, `improve_runs*/`)을 먼저 확인한다.
3. 결과 파일(`results_*.json`, `improve_runs*/`)은 실행 출력이다. 손으로 고치지 않는다.
4. `skills/`의 name과 description은 정답 기준이므로 바꾸지 않는다.
5. 변경 후 `python3 -m unittest discover -s tests -v`를 실행하고, 실패하면 고친 뒤 다시 실행한다.
6. 테스트와 자동 검사는 API 키 없이 돈다. API를 호출하는 명령은 사람이 직접 실행한다.
7. main에 직접 push하지 않는다. 브랜치에 커밋하고 PR을 연다.
