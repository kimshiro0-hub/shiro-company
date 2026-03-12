# 시로 컴퍼니 v2.4 — API 예산 트래커

> v2.3(자율 태스크 + --auto) 이후, API 호출마다 토큰 비용을 추적하는 예산 시스템 추가.
> 이전 문서: ARCHITECTURE_V2.3.md

---

## v2.3 → v2.4 변경 요약

| 항목 | v2.3 (이전) | v2.4 (현재) |
|------|-------------|-------------|
| API 비용 추적 | 없음 | 매 호출마다 budget.json에 기록 |
| 예산 경고 | 없음 | 잔액 10% 이하 → 콘솔 경고 |
| --auto 예산 차단 | 없음 | 잔액 5% 이하 → 실행 안 하고 종료 |
| 태스크 비용 출력 | 없음 | 완료 시 "💰 비용: $x \| 잔액: $y" |
| 예산 뷰어 | 없음 | budget_view.bat 더블클릭 |

---

## 신규 파일

### budget_tracker.py — 예산 관리 모듈

**위치:** `shiro_company/budget_tracker.py`
**의존:** filelock (board.py와 동일 패턴)

```python
# 핵심 함수
load_budget() -> dict      # budget.json 로드, 없으면 초기화, 월 바뀌면 리셋
save_budget(data)           # lock 잡고 저장
record_call(agent, model, input_tokens, output_tokens, task) -> dict
                            # 호출 기록 + 비용 차감 + 경고 출력
get_remaining() -> float    # 잔액 반환
get_task_cost(task) -> float # 특정 태스크의 총 비용
```

**비용 계산:**
- Claude Sonnet 4: input $3.00/1M + output $15.00/1M
- Gemini Flash: $0.00 (무료, 호출 횟수만 기록)

**budget.json 구조:**
```json
{
  "month": "2026-03",
  "budget_usd": 5.00,
  "spent_usd": 0.0234,
  "remaining_usd": 4.9766,
  "calls": [
    {
      "time": "2026-03-12 14:23:01",
      "agent": "sora",
      "model": "claude-sonnet-4-20250514",
      "input_tokens": 1200,
      "output_tokens": 350,
      "cost_usd": 0.0087,
      "task": "편의점 재고 체크리스트"
    },
    {
      "time": "2026-03-12 14:23:15",
      "agent": "teo",
      "model": "gemini-2.5-flash",
      "input_tokens": 2400,
      "output_tokens": 1800,
      "cost_usd": 0.0,
      "task": "편의점 재고 체크리스트"
    }
  ]
}
```

**자동 리셋:** 월이 바뀌면 (예: 2026-03 → 2026-04) calls 초기화, spent/remaining 리셋.

---

### budget_view.py + budget_view.bat — 예산 뷰어

누나가 더블클릭으로 예산 현황을 확인하는 도구.

```
==================================================
  💰 시로 컴퍼니 예산 현황 (2026-03)
==================================================
  월 예산:  $5.00
  사용액:   $0.0234
  잔액:     $4.9766
  API 호출: 8회

  소라: 4회 ($0.0234)
  테오: 4회 ($0.0000, 무료)

  ── 최근 호출 ──
  2026-03-12 14:23:01 | sora | $0.0087 | 편의점 재고 체크리스트
  ...
```

---

## 수정된 파일

### sora_manager.py

**think() 수정:**
```python
resp = client.messages.create(...)
text = resp.content[0].text
# 예산 기록 추가
record_call(
    agent="sora", model=model,
    input_tokens=resp.usage.input_tokens,
    output_tokens=resp.usage.output_tokens,
    task=_current_task(),
)
```

**decide_task() 수정:**
```python
# [AUTO] 태스크 결정 호출도 별도 기록
record_call(
    agent="sora", model=model,
    input_tokens=resp.usage.input_tokens,
    output_tokens=resp.usage.output_tokens,
    task="[AUTO] 태스크 결정",
)
```

**안전장치:** `try/except`로 감싸서 예산 기록 실패해도 대화는 계속.

---

### teo_dev.py

**think() 수정:**
```python
resp = gemini.models.generate_content(...)
# Gemini usage_metadata에서 토큰 추출
usage = getattr(resp, "usage_metadata", None)
in_tok = getattr(usage, "prompt_token_count", 0) if usage else 0
out_tok = getattr(usage, "candidates_token_count", 0) if usage else 0
record_call(
    agent="teo", model=model,
    input_tokens=in_tok, output_tokens=out_tok,
    task=_current_task(),
)
```

Gemini Flash는 무료 → cost_usd=0.0으로 기록, 호출 횟수만 트래킹.

---

### run_task.py

**태스크 완료 시 비용 출력:**
```python
# monitor_task() 직후
done_data = read_board()
actual_task = done_data.get("task", task)
task_cost = get_task_cost(actual_task)
remaining = get_remaining()
print(f"💰 이번 태스크 비용: ${task_cost:.4f} | 월 잔액: ${remaining:.4f}")
```

**--auto 예산 차단:**
```python
# args.auto일 때 실행 전 체크
budget = load_budget()
remaining = budget["remaining_usd"]
threshold = budget["budget_usd"] * 0.05  # 5%
if remaining <= threshold:
    print("💸 예산 부족. 이번 달 운영 종료.")
    return  # 에이전트 실행 안 함
```

---

## 예산 경고 체계

| 잔액 비율 | 동작 |
|-----------|------|
| > 10% | 정상 운영 |
| ≤ 10% | `⚠️ 예산 경고: 잔액 $x.xx` 콘솔 출력 (매 API 호출 시) |
| ≤ 5% | --auto 모드에서 태스크 시작 안 함, `💸 예산 부족` 출력 후 종료 |
| ≤ 5% | 수동 모드는 정상 실행 (누나가 직접 판단) |

---

## 현재 파일 상태 (v2.4)

```
shiro_company/
├── board.py              # 변경 없음
├── budget_tracker.py     # 신규 — 예산 관리 모듈
├── budget_view.py        # 신규 — 예산 뷰어
├── budget_view.bat       # 신규 — 더블클릭 실행
├── budget.json           # 자동 생성 — 호출 기록 + 잔액
├── budget.lock           # 자동 생성 — filelock
├── run_task.py           # 비용 출력, --auto 예산 차단
├── sora_manager.py       # think() + decide_task() 예산 기록
├── teo_dev.py            # think() 예산 기록 (cost=0)
├── context.md            # 변경 없음
├── task_board.json
├── output/
│   ├── {target}.py
│   ├── {target}.bat
│   └── test_{target}.py
└── logs/
```

---

## 알려진 제약 + 향후 개선점

### 해결됨 (v2.4)
1. ~~API 비용 추적 없음~~ → budget.json에 매 호출 기록
2. ~~예산 초과 방지 없음~~ → 10% 경고 + 5% 차단 (--auto)
3. ~~budget.json 열 수 없음~~ → budget_view.bat 더블클릭

### 남은 이슈
1. **budget.json calls 배열 무한 증가** — 한 달 내내 돌리면 수천 건. 요약/압축 필요
2. **Claude 가격 하드코딩** — 가격 변경 시 budget_tracker.py 수정 필요
3. **Gemini 유료 전환 시** — cost 계산 로직 추가 필요
4. **태스크 비용 매칭** — task 문자열 기반이라 같은 이름의 태스크가 있으면 합산됨
5. **Gemini 잘림 (데이터 heavy)** — v2.2부터 이어지는 이슈
6. **[FILE:] 파싱 실패** — fallback 없음

### 다음 단계 후보
1. budget.json 월말 요약 (일별 비용 집계)
2. 예산 설정 CLI (`python budget_view.py --set 10.00`)
3. cron/Windows 작업 스케줄러로 --auto 매일 실행
4. Level 2: 3인 이상 에이전트, 동적 발언자, 태스크 분해

---

*문서 작성일: 2026-03-12*
*시로 컴퍼니 v2.4 기준*
*이전 문서: ARCHITECTURE_V2.3.md*
