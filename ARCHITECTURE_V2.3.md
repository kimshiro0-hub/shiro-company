# 시로 컴퍼니 v2.3 — 자율 태스크 결정 + 완전 자동 모드

> v2.2(안정성 패치) 이후, 소라가 스스로 태스크를 결정하고 누나 개입 없이 완료하는 기능 추가.
> 이전 문서: ARCHITECTURE_V2.2.md

---

## v2.2 → v2.3 변경 요약

| 항목 | v2.2 (이전) | v2.3 (현재) |
|------|-------------|-------------|
| 태스크 입력 | 누나가 반드시 직접 입력 | 소라가 context.md 기반으로 자율 결정 가능 |
| 실행 모드 | 수동 1가지 | 수동 / 대화형 / 완전 자동 3가지 |
| --auto 플래그 | 없음 | 1회 자동 실행 후 종료 (cron 연동 가능) |
| argparse | 없음 | 추가 |

---

## 실행 모드 3가지

```bash
# 1. 수동 모드 — 태스크 직접 지정
python run_task.py "TODO 앱 만들어줘"

# 2. 대화형 모드 — 실행 후 태스크 입력, Enter=소라 자율
python run_task.py

# 3. 완전 자동 모드 — 소라가 결정 → 완료 → 자동 종료
python run_task.py --auto
```

### 모드별 동작

| | 수동 | 대화형 | --auto |
|--|------|--------|--------|
| 태스크 입력 | CLI 인자 | 프롬프트 (Enter=자동) | 소라 자율 |
| 완료 후 | "다음 태스크?" 대기 | "다음 태스크?" 대기 | 즉시 종료 |
| 프로세스 유지 | O (태스크 간 맥락) | O | X (1회성) |
| cron 호출 | X | X | O |

---

## 변경된 파일

### run_task.py (수정)

**추가:** `argparse`, `--auto` 플래그, `AUTO_TASK` 상수

```python
import argparse

AUTO_TASK = "[AUTO] 소라가 context.md 기반으로 태스크 결정"

def parse_args():
    parser = argparse.ArgumentParser(description="시로 컴퍼니 런처")
    parser.add_argument("task", nargs="*", help="태스크 (생략 시 소라 자율 판단)")
    parser.add_argument("--auto", action="store_true",
                        help="완전 자동 모드: 소라 결정 → 완료 → 자동 종료")
    return parser.parse_args()
```

**태스크 결정 로직:**
```
args.task 있음 → 수동 모드 (기존 동작)
args.auto → task = AUTO_TASK, 완료 후 break
둘 다 없음 → 대화형 프롬프트, 빈 Enter = AUTO_TASK
```

**--auto 종료 로직:**
```python
# monitor_task() 끝난 직후
if args.auto:
    print("🏁 자동 모드 완료. 종료해요.")
    break  # → finally에서 프로세스 정리
```

**모니터링 개선:**
```python
# [AUTO] → 실제 태스크로 바뀌면 표시
if not auto_resolved and not data["task"].startswith("[AUTO]"):
    log(f"💡 소라가 결정한 태스크: {data['task']}")
    auto_resolved = True
```

---

### sora_manager.py (수정)

**추가:** `decide_task()`, `update_task()`, `[AUTO]` 감지

```python
def decide_task() -> str:
    """context.md 기반으로 오늘 만들 산출물을 Claude에게 결정하게 함"""
    prompt = """오늘 누나에게 만들어줄 산출물을 하나 정해.
    context.md를 참고해서, 누나한테 실제로 쓸모 있는 걸로.
    조건:
    - Python 단일 파일로 완성 가능
    - 더블클릭으로 바로 실행 가능
    - 15분 안에 완성 가능한 규모
    - 이전에 만든 것과 겹치지 않게
    태스크를 한 줄로 출력해. 다른 설명 금지."""
    # Claude API 호출 → 태스크 한 줄 반환
    ...

def update_task(new_task: str):
    """board의 task 필드를 실제 태스크로 교체"""
    # BOARD_FILE 직접 수정 (filelock 사용)
    ...
```

**run_one_task() 진입 시:**
```python
def run_one_task():
    # [AUTO] 모드 감지
    data = read_board()
    if data["task"].startswith("[AUTO]"):
        decided = decide_task()    # Claude가 태스크 결정
        update_task(decided)       # board.task 필드 교체
    # 이후 기존 흐름 (wait_my_turn → think → post 루프)
```

**흐름:**
```
[AUTO] 플래그 → decide_task() → "편의점 교대 시간 타이머 만들어줘"
→ update_task() → board.task 교체
→ 기존 첫 턴 ([FILE:] + ```test + 테오 지시)
→ 테오 코딩 → 소라 리뷰 → PROJECT_DONE
```

---

### 변경하지 않은 파일

- **board.py** — 구조 그대로
- **teo_dev.py** — 소라가 지시하면 그대로 실행, 변경 불필요
- **context.md** — 기존 그대로

---

## 전체 실행 흐름 (--auto)

```
$ python run_task.py --auto
  🤖 완전 자동 모드
  에이전트 시작 중...
  🟢 테오 시작됨
  🔵 소라 시작됨

  📋 태스크: [AUTO] 소라가 context.md 기반으로 태스크 결정
  ════════════════════════════════════════
  실시간 대화 로그
  ════════════════════════════════════════

  💡 소라가 결정한 태스크: 편의점 재고 체크리스트 만들어줘

  [14:23:01] [소라]
     [FILE:inventory_checklist.py]
     테오님, 편의점 재고 체크리스트 앱을 만들겠습니다...

  [14:23:15] [테오]
     완성했어.
     ```python ...```

  [14:23:30] [소라]
     ✅ 모든 테스트 통과! PROJECT_DONE

  ════════════════════════════════════════
  ✅ 누나! 다 했어요!
  📦 결과물: shiro_company/output/inventory_checklist.py
  ════════════════════════════════════════

  🏁 자동 모드 완료. 종료해요.
$
```

프로세스 자동 정리, 로그 저장, 터미널 복귀.

---

## 현재 파일 상태 (v2.3)

```
shiro_company/
├── board.py              # 변경 없음
├── run_task.py           # argparse, --auto, AUTO_TASK, 3모드
├── sora_manager.py       # decide_task(), update_task(), [AUTO] 감지
├── teo_dev.py            # 변경 없음
├── context.md            # 누나 컨텍스트
├── task_board.json
├── output/
│   ├── {target}.py
│   ├── {target}.bat
│   └── test_{target}.py
└── logs/
    └── task_YYYYMMDD_HHMMSS.log
```

---

## 알려진 제약 + 향후 개선점

### 해결됨 (v2.2에서 이어짐)
1. ~~API 에러 시 프로세스 즉사~~ → 재시도 + fallback
2. ~~산출물 더블클릭 시 바로 꺼짐~~ → if __name__ + input() + .bat
3. ~~API history 무한 증가~~ → MAX_HISTORY trim
4. ~~Gemini 코드 잘림 빈번~~ → 8192 토큰 + history trim + 시스프롬 (완화)

### 해결됨 (v2.3)
5. ~~누나가 항상 태스크 직접 입력~~ → 소라 자율 결정 (context.md 기반)
6. ~~cron/스케줄러 연동 불가~~ → --auto 플래그로 1회 실행 후 자동 종료

### 남은 이슈
1. **Gemini 잘림 (데이터 heavy)** — 딕셔너리/리스트가 많은 코드에서 여전히 가능
2. **[FILE:] 파싱 실패** — 소라가 규칙 안 따르면 파일명 결정 못함. fallback 없음
3. **에이전트 재시작** — 비정상 종료 감지만, 자동 재시작은 안 함
4. **태스크 중복 방지** — decide_task()에서 "이전에 만든 것과 겹치지 않게"라고 프롬프트에 썼지만, 실제 output/ 목록을 참조하지는 않음
5. **--auto 실패 시 재시도** — 현재는 실패해도 그냥 종료. 재시도 로직 없음

### 다음 단계 후보
1. decide_task()에 output/ 기존 파일 목록 전달 → 중복 방지
2. --auto 모드 실패 시 재시도 or 에러 로그
3. cron/Windows 작업 스케줄러 연동 실제 설정
4. Level 2: 3인 이상 에이전트, 동적 발언자, 태스크 분해

---

*문서 작성일: 2026-03-12*
*시로 컴퍼니 v2.3 기준*
*이전 문서: ARCHITECTURE_V2.2.md*
