# 같은 설정의 반복 실행 흔들림

`variance.py`가 결과 파일의 반복(trial)마다 정확도를 따로 계산한 표입니다.

| 결과 파일 | 설정 | 데이터 | 실행 수 | 평균 | 최소 | 최대 | 폭 (최대-최소) | 표준편차 |
|---|---|---|---|---|---|---|---|---|
| `improve_runs_web/configs_final_check.json` | A 원본 | cases_new_external | 5 | 93.3% | 93.3% | 93.3% | 0.0%p | 0.0%p |
| `improve_runs_web/configs_final_check.json` | C 채택 설정 | cases_new_external | 5 | 100.0% | 100.0% | 100.0% | 0.0%p | 0.0%p |
| `improve_runs_web/configs_final_check.json` | E 채택 설정 + proofread 경계 문장 | cases_new_external | 5 | 100.0% | 100.0% | 100.0% | 0.0%p | 0.0%p |
