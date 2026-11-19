# 사용 현황

`dashboard.py`가 결과 파일에서 집계만 뽑아 만든 표입니다. 요청 원문과 모델 응답 본문은 넣지 않았습니다.
- 호출 수: 라우터 모델을 부른 횟수(결과 파일의 행 하나 = 호출 하나)
- 성공률: 스킬 이름 또는 none을 제대로 답한 호출의 비율(정답 여부와 다름)
- 응답 시간: 결과 파일에 기록하지 않아 모두 "기록 없음"
- keyword 선택기는 API를 부르지 않아 토큰이 "해당 없음"
- 학습셋·검증셋 평가 중 일부와 개선 모델 호출은 집계만 남아 토큰이 "기록 없음"
- 본인 기록(cases_history*) 결과는 공개하지 않으므로 기본으로 제외

| 파일 | 구분 | 모델 | 선택기 | 호출 수 | 성공률 | 응답 시간 | 입력 토큰 합계 | 출력 토큰 합계 | 호출당 입력 / 출력 |
|---|---|---|---|---|---|---|---|---|---|
| `improve_runs/ablation.json` | 원본 / train | claude-haiku-5-5 | api | 64 | 100.0% | 기록 없음 | 19,200 | 1,636 | 300 / 26 |
| `improve_runs/ablation.json` | 원본 / test | claude-haiku-5-5 | api | 48 | 100.0% | 기록 없음 | 14,300 | 1,710 | 298 / 36 |
| `improve_runs/ablation.json` | 지시문만 / train | claude-haiku-5-5 | api | 64 | 100.0% | 기록 없음 | 34,816 | 2,355 | 544 / 37 |
| `improve_runs/ablation.json` | 지시문만 / test | claude-haiku-5-5 | api | 48 | 100.0% | 기록 없음 | 26,012 | 338 | 542 / 7 |
| `improve_runs/ablation.json` | description만 / train | claude-haiku-5-5 | api | 64 | 100.0% | 기록 없음 | 21,568 | 2,299 | 337 / 36 |
| `improve_runs/ablation.json` | description만 / test | claude-haiku-5-5 | api | 48 | 100.0% | 기록 없음 | 16,076 | 486 | 335 / 10 |
| `improve_runs/ablation.json` | 둘 다 / train | claude-haiku-5-5 | api | 64 | 100.0% | 기록 없음 | 37,184 | 2,395 | 581 / 37 |
| `improve_runs/ablation.json` | 둘 다 / test | claude-haiku-5-5 | api | 48 | 100.0% | 기록 없음 | 27,788 | 395 | 579 / 8 |
| `improve_runs/ablation_cases_external.json` | 원본 / cases_external | claude-haiku-5-5 | api | 90 | 100.0% | 기록 없음 | 28,344 | 3,091 | 315 / 34 |
| `improve_runs/ablation_cases_external.json` | 지시문만 / cases_external | claude-haiku-5-5 | api | 90 | 100.0% | 기록 없음 | 50,304 | 9,818 | 559 / 109 |
| `improve_runs/ablation_cases_external.json` | description만 / cases_external | claude-haiku-5-5 | api | 90 | 100.0% | 기록 없음 | 31,674 | 5,264 | 352 / 58 |
| `improve_runs/ablation_cases_external.json` | 둘 다 / cases_external | claude-haiku-5-5 | api | 90 | 100.0% | 기록 없음 | 53,634 | 10,549 | 596 / 117 |
| `improve_runs/ablation_cases_external_round1.json` | 원본 / cases_external | claude-haiku-5-5 | api | 30 | 100.0% | 기록 없음 | 8,946 | 978 | 298 / 33 |
| `improve_runs/ablation_cases_external_round1.json` | 지시문만 / cases_external | claude-haiku-5-5 | api | 30 | 100.0% | 기록 없음 | 16,266 | 3,637 | 542 / 121 |
| `improve_runs/ablation_cases_external_round1.json` | description만 / cases_external | claude-haiku-5-5 | api | 30 | 100.0% | 기록 없음 | 10,056 | 2,150 | 335 / 72 |
| `improve_runs/ablation_cases_external_round1.json` | 둘 다 / cases_external | claude-haiku-5-5 | api | 30 | 100.0% | 기록 없음 | 17,376 | 4,251 | 579 / 142 |
| `improve_runs/ablation_cases_external_search.json` | 원본 / cases_external_search | claude-haiku-5-5 | api | 90 | 100.0% | 기록 없음 | 31,584 | 5,412 | 351 / 60 |
| `improve_runs/ablation_cases_external_search.json` | 지시문만 / cases_external_search | claude-haiku-5-5 | api | 90 | 100.0% | 기록 없음 | 53,544 | 9,941 | 595 / 110 |
| `improve_runs/ablation_cases_external_search.json` | description만 / cases_external_search | claude-haiku-5-5 | api | 90 | 100.0% | 기록 없음 | 34,914 | 6,508 | 388 / 72 |
| `improve_runs/ablation_cases_external_search.json` | 둘 다 / cases_external_search | claude-haiku-5-5 | api | 90 | 100.0% | 기록 없음 | 56,874 | 9,486 | 632 / 105 |
| `improve_runs/ablation_cases_external_task.json` | 원본 / cases_external_task | claude-haiku-5-5 | api | 60 | 100.0% | 기록 없음 | 18,978 | 1,705 | 316 / 28 |
| `improve_runs/ablation_cases_external_task.json` | 지시문만 / cases_external_task | claude-haiku-5-5 | api | 60 | 100.0% | 기록 없음 | 33,618 | 5,328 | 560 / 89 |
| `improve_runs/ablation_cases_external_task.json` | description만 / cases_external_task | claude-haiku-5-5 | api | 60 | 100.0% | 기록 없음 | 21,198 | 2,807 | 353 / 47 |
| `improve_runs/ablation_cases_external_task.json` | 둘 다 / cases_external_task | claude-haiku-5-5 | api | 60 | 100.0% | 기록 없음 | 35,838 | 6,324 | 597 / 105 |
| `improve_runs/ablation_cases_external_task_search.json` | 원본 / cases_external_task_search | claude-haiku-5-5 | api | 60 | 100.0% | 기록 없음 | 21,138 | 1,293 | 352 / 22 |
| `improve_runs/ablation_cases_external_task_search.json` | 지시문만 / cases_external_task_search | claude-haiku-5-5 | api | 60 | 100.0% | 기록 없음 | 35,778 | 5,005 | 596 / 83 |
| `improve_runs/ablation_cases_external_task_search.json` | description만 / cases_external_task_search | claude-haiku-5-5 | api | 60 | 100.0% | 기록 없음 | 23,358 | 2,016 | 389 / 34 |
| `improve_runs/ablation_cases_external_task_search.json` | 둘 다 / cases_external_task_search | claude-haiku-5-5 | api | 60 | 100.0% | 기록 없음 | 37,998 | 5,309 | 633 / 88 |
| `improve_runs/ablation_cases_v3_search.json` | 원본 / cases_v3_search | claude-haiku-5-5 | api | 96 | 100.0% | 기록 없음 | 32,256 | 3,129 | 336 / 33 |
| `improve_runs/ablation_cases_v3_search.json` | 지시문만 / cases_v3_search | claude-haiku-5-5 | api | 96 | 100.0% | 기록 없음 | 55,680 | 3,367 | 580 / 35 |
| `improve_runs/ablation_cases_v3_search.json` | description만 / cases_v3_search | claude-haiku-5-5 | api | 96 | 100.0% | 기록 없음 | 35,808 | 4,614 | 373 / 48 |
| `improve_runs/ablation_cases_v3_search.json` | 둘 다 / cases_v3_search | claude-haiku-5-5 | api | 96 | 100.0% | 기록 없음 | 59,232 | 3,133 | 617 / 33 |
| `improve_runs/summary.json` | 테스트셋 / 원본 | claude-haiku-5-5 | api | 48 | 100.0% | 기록 없음 | 14,300 | 1,783 | 298 / 37 |
| `improve_runs/summary.json` | 테스트셋 / 개선 | claude-haiku-5-5 | api | 48 | 100.0% | 기록 없음 | 27,788 | 290 | 579 / 6 |
| `improve_runs/summary.json` | 학습셋 평가 / 0회차 | claude-haiku-5-5 | api | 64 | 100.0% | 기록 없음 | 기록 없음 | 기록 없음 | 기록 없음 |
| `improve_runs/summary.json` | 학습셋 평가 / 1회차 | claude-haiku-5-5 | api | 64 | 100.0% | 기록 없음 | 기록 없음 | 기록 없음 | 기록 없음 |
| `improve_runs/summary.json` | 개선 모델 호출 (수정안 생성) | claude-opus-5-5 | api | 1 | 기록 없음 | 기록 없음 | 기록 없음 | 기록 없음 | 기록 없음 |
| `improve_runs_val/ablation_cases_external_task.json` | 원본 / cases_external_task | claude-haiku-5-5 | api | 60 | 100.0% | 기록 없음 | 18,978 | 1,486 | 316 / 25 |
| `improve_runs_val/ablation_cases_external_task.json` | 지시문만 / cases_external_task | claude-haiku-5-5 | api | 60 | 100.0% | 기록 없음 | 41,838 | 3,418 | 697 / 57 |
| `improve_runs_val/ablation_cases_external_task.json` | description만 / cases_external_task | claude-haiku-5-5 | api | 60 | 100.0% | 기록 없음 | 18,978 | 1,442 | 316 / 24 |
| `improve_runs_val/ablation_cases_external_task.json` | 둘 다 / cases_external_task | claude-haiku-5-5 | api | 60 | 100.0% | 기록 없음 | 41,838 | 3,240 | 697 / 54 |
| `improve_runs_val/summary.json` | 테스트셋 / 원본 | claude-haiku-5-5 | api | 48 | 100.0% | 기록 없음 | 14,300 | 1,707 | 298 / 36 |
| `improve_runs_val/summary.json` | 테스트셋 / 개선 | claude-haiku-5-5 | api | 48 | 100.0% | 기록 없음 | 32,588 | 510 | 679 / 11 |
| `improve_runs_val/summary.json` | 보류셋 / 원본 | claude-haiku-5-5 | api | 28 | 100.0% | 기록 없음 | 8,866 | 1,098 | 317 / 39 |
| `improve_runs_val/summary.json` | 보류셋 / 개선 | claude-haiku-5-5 | api | 28 | 100.0% | 기록 없음 | 19,534 | 2,531 | 698 / 90 |
| `improve_runs_val/summary.json` | 학습셋 평가 / 0회차 | claude-haiku-5-5 | api | 64 | 100.0% | 기록 없음 | 기록 없음 | 기록 없음 | 기록 없음 |
| `improve_runs_val/summary.json` | 검증셋 평가 / 0회차 | claude-haiku-5-5 | api | 32 | 100.0% | 기록 없음 | 기록 없음 | 기록 없음 | 기록 없음 |
| `improve_runs_val/summary.json` | 학습셋 평가 / 1회차 | claude-haiku-5-5 | api | 64 | 100.0% | 기록 없음 | 기록 없음 | 기록 없음 | 기록 없음 |
| `improve_runs_val/summary.json` | 검증셋 평가 / 1회차 | claude-haiku-5-5 | api | 32 | 100.0% | 기록 없음 | 기록 없음 | 기록 없음 | 기록 없음 |
| `improve_runs_val/summary.json` | 학습셋 평가 / 2회차 | claude-haiku-5-5 | api | 64 | 100.0% | 기록 없음 | 기록 없음 | 기록 없음 | 기록 없음 |
| `improve_runs_val/summary.json` | 검증셋 평가 / 2회차 | claude-haiku-5-5 | api | 32 | 100.0% | 기록 없음 | 기록 없음 | 기록 없음 | 기록 없음 |
| `improve_runs_val/summary.json` | 개선 모델 호출 (수정안 생성) | claude-opus-5-5 | api | 2 | 기록 없음 | 기록 없음 | 기록 없음 | 기록 없음 | 기록 없음 |
| `improve_runs_web/configs_web_boundary.json` | A 원본 / cases_external_search2 | claude-haiku-5-5 | api | 90 | 100.0% | 기록 없음 | 31,584 | 5,064 | 351 / 56 |
| `improve_runs_web/configs_web_boundary.json` | A 원본 / cases_external_task_search2 | claude-haiku-5-5 | api | 60 | 100.0% | 기록 없음 | 21,138 | 1,332 | 352 / 22 |
| `improve_runs_web/configs_web_boundary.json` | A 원본 / cases_v3_search2 | claude-haiku-5-5 | api | 96 | 100.0% | 기록 없음 | 32,256 | 3,399 | 336 / 35 |
| `improve_runs_web/configs_web_boundary.json` | A 원본 / cases_test_search2 | claude-haiku-5-5 | api | 72 | 100.0% | 기록 없음 | 24,042 | 2,991 | 334 / 42 |
| `improve_runs_web/configs_web_boundary.json` | B description 개선 / cases_external_search2 | claude-haiku-5-5 | api | 90 | 100.0% | 기록 없음 | 34,914 | 6,477 | 388 / 72 |
| `improve_runs_web/configs_web_boundary.json` | B description 개선 / cases_external_task_search2 | claude-haiku-5-5 | api | 60 | 100.0% | 기록 없음 | 23,358 | 2,349 | 389 / 39 |
| `improve_runs_web/configs_web_boundary.json` | B description 개선 / cases_v3_search2 | claude-haiku-5-5 | api | 96 | 100.0% | 기록 없음 | 35,808 | 3,976 | 373 / 41 |
| `improve_runs_web/configs_web_boundary.json` | B description 개선 / cases_test_search2 | claude-haiku-5-5 | api | 72 | 100.0% | 기록 없음 | 26,706 | 3,184 | 371 / 44 |
| `improve_runs_web/configs_web_boundary.json` | C 원본 + 경계 문장 / cases_external_search2 | claude-haiku-5-5 | api | 90 | 100.0% | 기록 없음 | 35,274 | 5,530 | 392 / 61 |
| `improve_runs_web/configs_web_boundary.json` | C 원본 + 경계 문장 / cases_external_task_search2 | claude-haiku-5-5 | api | 60 | 100.0% | 기록 없음 | 23,598 | 1,702 | 393 / 28 |
| `improve_runs_web/configs_web_boundary.json` | C 원본 + 경계 문장 / cases_v3_search2 | claude-haiku-5-5 | api | 96 | 100.0% | 기록 없음 | 36,192 | 3,377 | 377 / 35 |
| `improve_runs_web/configs_web_boundary.json` | C 원본 + 경계 문장 / cases_test_search2 | claude-haiku-5-5 | api | 72 | 100.0% | 기록 없음 | 26,994 | 2,697 | 375 / 37 |
| `improve_runs_web/configs_web_boundary.json` | D description 개선 + 경계 문장 / cases_external_search2 | claude-haiku-5-5 | api | 90 | 100.0% | 기록 없음 | 38,604 | 7,196 | 429 / 80 |
| `improve_runs_web/configs_web_boundary.json` | D description 개선 + 경계 문장 / cases_external_task_search2 | claude-haiku-5-5 | api | 60 | 100.0% | 기록 없음 | 25,818 | 2,838 | 430 / 47 |
| `improve_runs_web/configs_web_boundary.json` | D description 개선 + 경계 문장 / cases_v3_search2 | claude-haiku-5-5 | api | 96 | 100.0% | 기록 없음 | 39,744 | 3,213 | 414 / 33 |
| `improve_runs_web/configs_web_boundary.json` | D description 개선 + 경계 문장 / cases_test_search2 | claude-haiku-5-5 | api | 72 | 100.0% | 기록 없음 | 29,658 | 2,578 | 412 / 36 |
| `results.json` | 전체 | 기록 없음 | api | 9 | 100.0% | 기록 없음 | 1,541 | 107 | 171 / 12 |
| `results_basic.json` | 전체 | 기록 없음 | api | 5 | 100.0% | 기록 없음 | 860 | 22 | 172 / 4 |
| `results_v2_api.json` | 전체 | 기록 없음 | api | 20 | 100.0% | 기록 없음 | 4,709 | 158 | 235 / 8 |
| `results_v2_api_medium.json` | 전체 | 기록 없음 | api | 20 | 100.0% | 기록 없음 | 4,709 | 432 | 235 / 22 |
| `results_v2_keyword.json` | 전체 | 해당 없음 | keyword | 20 | 100.0% | 기록 없음 | 해당 없음 | 해당 없음 | 해당 없음 |
| `results_v3_api.json` | 전체 | claude-haiku-5-5 | api | 96 | 100.0% | 기록 없음 | 28,800 | 2,813 | 300 / 29 |
| `results_v3_keyword.json` | 전체 | 해당 없음 | keyword | 32 | 100.0% | 기록 없음 | 해당 없음 | 해당 없음 | 해당 없음 |
| **합계 (API 호출)** |  |  | api | **4,481** |  | 기록 없음 | 1,766,655 (토큰 기록이 있는 4,062회) | 205,669 |  |
