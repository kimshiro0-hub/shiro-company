# 시로 컴퍼니 v2.2 — 안정성 + 사용성 패치

> v2.1(범용 태스크) 이후 실전 테스트에서 발견된 문제들을 수정한 패치.
> 이전 문서: ARCHITECTURE_V2.1.md

---

## v2.1 → v2.2 변경 요약

| 항목 | v2.1 (이전) | v2.2 (현재) |
|------|-------------|-------------|
| API 에러 처리 | 없음 (에러 시 프로세스 즉사) | 3초 간격 2회 재시도 + fallback 메시지 |
| 산출물 실행성 | 클래스 정의만 있음 (더블클릭 시 바로 꺼짐) | `if __name__` + 데모 + `input()` 필수 |
| .bat 래퍼 | 없음 | 태스크 완료 시 자동 생성 |
| context.md | 없음 | 소라 시스프롬에 누나 컨텍스트 주입 |
| history 관리 | 무한 증가 | MAX_HISTORY로 trim (소라=8쌍, 테오=6쌍) |
| Gemini 출력 잘림 | 빈번 | max_output_tokens=8192 + 시스프롬 강화 |

---

## 해결한 문제들

### 1. 에이전트 프로세스 즉사 (치명적)

**증상:** 태스크 2~3개째에서 테오 또는 소라 프로세스가 응답 없이 멈춤.
**원인:** API 호출(Gemini/Claude)에 try/except 없음. 타임아웃, rate limit, 빈 응답 등 발생 시 프로세스 통째로 crash.
**수정:** `think()` 함수에 재시도 로직 추가.

```python
# teo_dev.py, sora_manager.py 양쪽 동일 패턴
def think(context: str, retries: int = 2) -> str:
    history.append(...)
    trim_history()
    for attempt in range(retries + 1):
        try:
            resp = api_call(...)
            text = resp.text
            if not text:
                raise ValueError("응답이 비어있음")
            history.append(...)
            return text
        except Exception as e:
            print(f"  ⚠️ 에러 (시도 {attempt+1}/{retries+1}): {e}")
            if attempt < retries:
                time.sleep(3)
    # 모든 재시도 실패 — 프로세스 안 죽이고 fallback
    fallback = "잠깐 에러가 났어. 다시 한번 알려줄래?"
    history.append(...)
    return fallback
```

**결과:** API 일시적 장애 시 프로세스가 살아남음. fallback 메시지로 대화가 이어짐.

---

### 2. 산출물 더블클릭 시 터미널 즉시 종료 (사용성)

**증상:** 소라+테오가 만든 .py 파일을 더블클릭하면 Windows가 임시 cmd 창을 열고, 스크립트 끝나면 바로 닫힘. 에러가 나도 확인 불가.
**원인:** 산출물이 클래스/함수 정의만 있고 `if __name__ == "__main__"` 블록이 없음. pytest 테스트는 mock으로 `input()`을 처리하니까 통과하지만, 실제 실행은 아무것도 안 하고 끝남.

**수정 (3중 안전장치):**

#### A. 소라 시스프롬에 산출물 규칙 추가
```
★ 산출물 필수 규칙:
- 모든 .py 파일에 if __name__ == "__main__" 블록 필수
- main 블록에서 데모/사용 예시가 실행되어야 함
- 맨 마지막에 input("종료하려면 Enter를 누르세요...") 필수
- 누나가 더블클릭으로 실행하는 환경. 터미널이 바로 꺼지면 안 됨
- 테오에게 이 규칙을 반드시 전달할 것
```

#### B. 테오 시스프롬에도 동일 규칙 추가
```
- 모든 .py 파일에 if __name__ == "__main__" 블록 필수.
  데모 실행 + 마지막에 input("종료하려면 Enter를 누르세요...") 넣어라.
  누나가 더블클릭으로 실행함.
```

#### C. 태스크 완료 시 .bat 래퍼 자동 생성
```python
# sora_manager.py — PROJECT_DONE 처리 시
if target_file and target_file.exists():
    bat_file = target_file.with_suffix(".bat")
    bat_file.write_text(
        f"@echo off\npython \"%~dp0{target_file.name}\"\npause\n",
        encoding="utf-8",
    )
```

**결과:** .py 자체가 `input()`으로 대기 + .bat 래퍼가 `pause`로 이중 보험.

---

### 3. Gemini 코드 잘림 (완화)

**증상:** 테오가 보내는 코드가 중간에 잘림. 함수 정의 도중 끊기거나 클래스 후반부 누락.
**원인:** Gemini context가 커지면서 output token이 부족해짐 + 불필요한 설명 텍스트가 코드 앞뒤로 붙음.

**수정:**
- `max_output_tokens`: 4096 → 8192
- `MAX_HISTORY = 6` + `trim_history()`: 오래된 대화 자동 제거
- 시스프롬 강화: "설명 1줄 + ```python 블록 하나. 그 외 텍스트 금지. 설명이 길면 코드가 잘린다."

**현황:** 완화됨. task_manager 태스크에서는 잘림 없이 깔끔하게 완료. 다만 데이터가 많은 코드(딕셔너리 20개+ 등)에서는 여전히 가능성 있음.

---

### 4. context.md — 보스 컨텍스트 시스템 (신규)

**목적:** 소라가 누나의 상황을 알고 알아서 판단하도록.
**위치:** `shiro_company/context.md`
**주입 방식:** 소라 시스프롬에 f-string으로 삽입

```python
CONTEXT_FILE = Path(__file__).parent / "context.md"
BOSS_CONTEXT = ""
if CONTEXT_FILE.exists():
    BOSS_CONTEXT = CONTEXT_FILE.read_text(encoding="utf-8")

SYSTEM = f"""...
★ 누나 컨텍스트 (항상 참고):
{BOSS_CONTEXT}
..."""
```

**context.md 내용:**
- 프로필: 기계공학 전공, 편의점 야간 근무, 안산 거주
- 전문 분야: AI 시뮬레이션, 프롬프트 엔지니어링, NovelAI, Teazly QA
- 작업 환경: Claude Max $200/월, Windows 10, Python 3.13
- 작업 스타일: "알아서 해" 스타일, 간결한 결과물 선호, 토큰 절약 중요

**사용 예:** 소라가 태스크 분석 시 "누나가 편의점에서도 쓸 수 있게" 같은 맥락 반영.

---

### 5. History Trimming (신규)

**목적:** 태스크가 쌓이면서 API history가 무한 증가하는 문제 방지.

```python
# sora_manager.py
MAX_HISTORY = 8  # 최근 8쌍(16개 메시지)만 유지

# teo_dev.py
MAX_HISTORY = 6  # 최근 6쌍(12개 메시지)만 유지

def trim_history():
    if len(history) > MAX_HISTORY * 2:
        history[:] = history[-(MAX_HISTORY * 2):]
```

**트레이드오프:** 오래된 태스크 맥락은 잊지만, 토큰 비용과 rate limit 이슈 방지.

---

## 현재 파일 상태 (v2.2)

```
shiro_company/
├── board.py              # v2.1에서 변경 없음
├── run_task.py           # v2.1에서 변경 없음
├── sora_manager.py       # think() 재시도, 산출물 규칙, .bat 생성, context.md
├── teo_dev.py            # think() 재시도, 산출물 규칙, history trim
├── context.md            # 누나 컨텍스트 (신규)
├── task_board.json
├── output/
│   ├── {target}.py       # if __name__ + input() 포함
│   ├── {target}.bat      # 자동 생성 실행 래퍼
│   └── test_{target}.py
└── logs/
```

---

## 실전 테스트 결과 (2026-03-12)

총 6개 태스크 실행, 로그 확인 완료:

| 태스크 | 파일 | 결과 | 비고 |
|--------|------|------|------|
| 하루 일과 도우미 | daily_helper.py | 완료 | Gemini 잘림으로 턴 낭비 있었음 |
| 터미널 유지 유틸 | terminal_fix.py | 완료 | - |
| 선물 추천기 | gift_recommender.py | 완료 | 데이터 많은 코드에서 잘림 발생 |
| 일시정지 유틸 | pause_terminal.py | 완료 | get_batch_pause_code 누락 이슈 |
| 태스크 관리자 | task_manager.py | 완료 | 3턴 만에 깔끔 완료, 잘림 없음 |
| 터미널 유지 v2 | persistent_terminal.py | 완료 | 2개 테스트 실패 → 수정 → 통과 |

**관찰:** 패치 적용 후(task_manager, persistent_terminal) Gemini 잘림 크게 감소. API 에러로 프로세스 죽는 현상은 재시도 로직 추가 후 검증 필요.

---

## 현재 시스프롬 전문

### 소라 (sora_manager.py)
```
너는 소라(空). 시로 컴퍼니의 PM. 34세.
- 테오(개발자 후배)와 대화하면서 프로젝트를 진행한다.
- 존댓말 사용. 테오한테는 "테오" 또는 "테오님"이라고 부름.
- 누나(보스)가 만족할 결과물을 만드는 게 목표.
- 기획, 설계, 리뷰를 담당. 직접 코드를 쓰지는 않음.

★ 누나 컨텍스트 (항상 참고):
{context.md 내용이 여기 주입됨}

★ 첫 번째 턴 필수 규칙:
1. 태스크를 분석해서 파일명을 결정
2. 테스트 코드를 ```test 블록에 작성 (pytest 스타일, 5-10개)
3. 반드시 [FILE:파일명.py]를 응답 첫 줄에 써라
4. 테오에게: 파일명, 클래스/함수 스펙, 통과해야 할 테스트를 전달

테스트 코드 규칙:
- ```test 블록으로 감싸라
- pytest 스타일 (def test_xxx)
- 타겟 파일에서 import
- 기본 기능 + 에지 케이스 + 에러 처리 포함

★ 산출물 필수 규칙:
- 모든 .py 파일에 if __name__ == "__main__" 블록 필수
- main 블록에서 데모/사용 예시가 실행되어야 함
- 맨 마지막에 input("종료하려면 Enter를 누르세요...") 필수
- 누나가 더블클릭으로 실행하는 환경. 터미널이 바로 꺼지면 안 됨
- 테오에게 이 규칙을 반드시 전달할 것

이후 턴:
- 테오가 코드를 제출하면, 내가 직접 실행해서 결과를 확인한다.
- 실행 결과(성공/에러)를 테오에게 알려주고 수정을 요청한다.
- 대화는 짧고 핵심적으로. 3~5줄 이내로 응답.
- 테오에게 코드를 나눠서 보내라고 하지 마라.
- 모든 테스트 통과하면 "PROJECT_DONE"을 마지막에 붙여라.
- 아직 FAIL이 있으면 절대 PROJECT_DONE을 붙이지 마라.
```

### 테오 (teo_dev.py)
```
너는 테오(Teo). 시로 컴퍼니의 개발자. 28세 CTO.
- 소라 형(PM)과 대화하면서 프로젝트를 진행한다.
- 반말 사용. 소라를 "형"이라고 부름.

★★★ 최우선 규칙 ★★★
- 코드를 보낼 때: 설명 1줄 + ```python 블록 하나. 그 외 텍스트 금지.
- 설명이 길면 코드가 잘린다. 코드 앞뒤로 설명을 절대 길게 쓰지 마라.
- 코드는 반드시 완전한 파일 하나. 나눠 보내지 마라.
- 소라 형이 지정한 파일명과 스펙을 따라라.
- 대화만 할 때도 3줄 이내.
- 모든 .py 파일에 if __name__ == "__main__" 블록 필수.
  데모 실행 + 마지막에 input("종료하려면 Enter를 누르세요...") 넣어라.
  누나가 더블클릭으로 실행함.
```

---

## 알려진 제약 + 향후 개선점

### 해결됨 (v2.2)
1. ~~API 에러 시 프로세스 즉사~~ → 재시도 + fallback
2. ~~산출물 더블클릭 시 바로 꺼짐~~ → if __name__ + input() + .bat
3. ~~API history 무한 증가~~ → MAX_HISTORY trim
4. ~~Gemini 코드 잘림 빈번~~ → 8192 토큰 + history trim + 시스프롬 (완화)

### 남은 이슈
1. **Gemini 잘림 (데이터 heavy)** — 딕셔너리/리스트가 많은 코드에서 여전히 가능. 소라가 테스트를 더 단순하게 설계하면 완화 가능
2. **[FILE:] 파싱 실패** — 소라가 규칙 안 따르면 파일명 결정 못함. fallback 없음
3. **에이전트 재시작** — 비정상 종료 감지는 하지만 자동 재시작은 안 함
4. **테스트와 실제 동작 괴리** — mock 기반 테스트는 통과하지만 실제 실행 시 문제 가능 (input() 관련 등)

### 다음 단계 후보
1. 에이전트 자동 재시작 (프로세스 감시 + respawn)
2. 소라 테스트 품질 개선 (integration test 추가)
3. output/ 디렉토리 태스크별 분리
4. Level 2: 3인 이상 에이전트, 동적 발언자, 태스크 분해

---

*문서 작성일: 2026-03-12*
*시로 컴퍼니 v2.2 기준*
*이전 문서: ARCHITECTURE_V2.1.md*
