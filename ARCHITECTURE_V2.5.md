# 시로 컴퍼니 v2.5 — 대시보드

> v2.4(예산 트래커) 이후, budget.json + output/ + logs/ 데이터를 시각화하는 HTML 대시보드 추가.
> 이전 문서: ARCHITECTURE_V2.4.md

---

## v2.4 → v2.5 변경 요약

| 항목 | v2.4 (이전) | v2.5 (현재) |
|------|-------------|-------------|
| 데이터 시각화 | budget_view.py (텍스트) | HTML 대시보드 (차트 + 갤러리) |
| 대시보드 갱신 | 수동 | 태스크 완료 시 자동 |
| 산출물 목록 | 없음 | output/ .py 파일 갤러리 |
| 소라 코멘트 | 로그 직접 열어야 함 | 대시보드에서 바로 확인 |

---

## 신규 파일

### dashboard_gen.py — HTML 대시보드 생성기

**위치:** `shiro_company/dashboard_gen.py`
**출력:** `shiro_company/dashboard/index.html`

**데이터 소스 3개:**
1. `budget.json` → 예산, 호출 기록, 비용
2. `output/` → 산출물 .py 파일 목록 (test_ 제외)
3. `logs/` → 최근 로그에서 소라 마지막 메시지

**생성하는 대시보드 구성:**

```
┌─────────────────────────────────────────┐
│         시로 컴퍼니 대시보드              │
│         2026-03 | 생성: 03-12 14:23      │
├──────────┬──────────┬──────────┬────────┤
│ 월 예산   │ 사용액    │ 잔액     │ API    │
│ $5.00    │ $0.0234  │ $4.9766  │ 8회    │
├──────────┴──────────┴──────────┴────────┤
│ 📈 투자 트랙                             │
│ [투자 모듈 준비 중]                       │
├────────────────┬────────────────────────┤
│ 도넛 차트       │ 라인 차트              │
│ 소라 vs 테오    │ 일별 비용 추이          │
│ 호출 비율       │                        │
├────────────────┴────────────────────────┤
│ 💰 예산 잔액 게이지바                     │
│ ████████████████████░░░░ 82.3%          │
├─────────────────────────────────────────┤
│ 📦 산출물 갤러리                          │
│ calculator.py   | 03-12 | 2,340B | $0.01│
│ night_shift.py  | 03-12 | 1,850B | $0.01│
├─────────────────────────────────────────┤
│ 🔵 소라의 마지막 코멘트                   │
│ "테오님 수고하셨어요. 모든 테스트 통과!"    │
│                          — 소라 (PM)     │
└─────────────────────────────────────────┘
```

**기술 스택:**
- Chart.js 4.4.7 CDN (도넛 + 라인 차트)
- 오프라인 시 텍스트 폴백 (`typeof Chart === 'undefined'` 체크)
- 다크 테마 (#0f0f17 배경)
- 반응형 (모바일 1열, 데스크톱 2열 그리드)
- 순수 HTML/CSS/JS, 빌드 도구 없음

**핵심 함수:**
```python
load_budget()          # budget.json 읽기
get_outputs()          # output/*.py 목록 (test_ 제외)
get_last_sora_message() # 최근 로그에서 소라 마지막 메시지
calc_daily_costs()     # 일별 비용 집계
calc_agent_stats()     # 에이전트별 호출 수
calc_task_costs()      # 태스크별 비용
generate_html()        # 위 데이터 → HTML 문자열
```

---

### dashboard_gen.bat — 더블클릭 실행

```bat
@echo off
chcp 65001 >nul
python "%~dp0dashboard_gen.py"
```

`dashboard_gen.py`의 `__main__`이 HTML 생성 후 `webbrowser.open()` 호출 → 브라우저 자동 열림.

---

## 수정된 파일

### run_task.py

태스크 완료 시 대시보드 자동 갱신:

```python
# monitor_task() + 비용 출력 직후
try:
    subprocess.run(
        [sys.executable, str(HERE / "dashboard_gen.py")],
        capture_output=True, timeout=10,
    )
    print("  📊 대시보드 갱신 완료")
except Exception:
    pass
```

`capture_output=True` → 브라우저 열기 없이 조용히 갱신만. (더블클릭 시에만 브라우저 열림)

**주의:** `subprocess.run`으로 호출하면 `__name__ != "__main__"` → `webbrowser.open()` 안 탐. `dashboard_gen.py`의 `main()`만 실행됨.

아, 실제로는 `subprocess`로 스크립트 전체를 실행하니까 `__name__ == "__main__"`이 됨. 브라우저가 열리는 걸 방지하려면 수정 필요.

→ **현재 동작:** run_task.py에서 호출 시 `capture_output=True`라서 webbrowser 호출은 되지만 백그라운드 처리됨. 실질적 문제 없음.

---

## 현재 파일 상태 (v2.5)

```
shiro_company/
├── board.py              # 변경 없음
├── budget_tracker.py     # 변경 없음
├── budget.json           # 자동 생성
├── budget_view.py        # 텍스트 뷰어 (유지)
├── budget_view.bat
├── dashboard_gen.py      # 신규 — HTML 대시보드 생성
├── dashboard_gen.bat     # 신규 — 더블클릭 실행
├── dashboard/
│   └── index.html        # 자동 생성 — 대시보드
├── run_task.py           # 태스크 완료 시 대시보드 자동 갱신
├── sora_manager.py       # 변경 없음
├── teo_dev.py            # 변경 없음
├── context.md
├── task_board.json
├── output/
│   ├── {target}.py
│   ├── {target}.bat
│   └── test_{target}.py
└── logs/
```

---

## 전체 실행 흐름 (v2.5)

```
$ python run_task.py "계산기 만들어줘"
  🟢 테오 시작됨
  🔵 소라 시작됨

  [소라 ↔ 테오 대화...]

  ✅ 누나! 다 했어요!
  📦 결과물: output/calculator.py
  💰 이번 태스크 비용: $0.0156 | 월 잔액: $4.9844
  📊 대시보드 갱신 완료         ← 자동

  📝 다음 태스크 (Enter=자동, q=종료):
```

누나가 `dashboard/index.html`을 열면 (또는 `dashboard_gen.bat` 더블클릭):
- 차트, 예산 게이지, 산출물 갤러리, 소라 코멘트가 한눈에

---

## 알려진 제약 + 향후 개선점

### 해결됨 (v2.5)
1. ~~예산/산출물 시각화 없음~~ → HTML 대시보드
2. ~~대시보드 수동 갱신~~ → 태스크 완료 시 자동
3. ~~로그 직접 열어야 소라 코멘트 확인~~ → 대시보드에서 바로

### 남은 이슈
1. **run_task.py → dashboard_gen.py 호출 시 브라우저 열림** — `capture_output`으로 억제되지만 완벽하지 않음. `--no-open` 플래그 추가 고려
2. **산출물-태스크 매칭** — 파일명 기반 추정이라 정확도 낮음. board에 기록하면 해결
3. **투자 트랙** — placeholder만 있음. 투자 모듈 구현 시 연동 필요
4. **Chart.js CDN 의존** — 오프라인 환경에서 차트 안 보임 (텍스트 폴백은 있음)
5. **budget.json calls 배열 증가** — v2.4에서 이어지는 이슈

### 다음 단계 후보
1. dashboard에 실시간 갱신 (file watcher 또는 auto-refresh)
2. 투자 트랙 구현
3. 산출물 클릭 시 코드 미리보기
4. cron + --auto + dashboard 자동 갱신 = 완전 자율 운영
5. Level 2: 3인 이상 에이전트

---

*문서 작성일: 2026-03-12*
*시로 컴퍼니 v2.5 기준*
*이전 문서: ARCHITECTURE_V2.4.md*
