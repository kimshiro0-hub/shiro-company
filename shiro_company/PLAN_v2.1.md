# 시로 컴퍼니 v2.1 — 범용 태스크 처리 업그레이드

## Context
v2에서 소라(PM)+테오(Dev)가 자율 협업으로 계산기를 만드는 것까지 검증 완료.
하지만 현재 코드는 **calculator.py 전용**으로 하드코딩되어 있어서 다른 태스크를 줄 수 없음.

**목표:** 누나가 아무 태스크나 던지면, 소라가 알아서 분석→테스트 설계→테오에게 지시→검증→완료하는 범용 시스템.

---

## 변경 대상 파일 (4개)

### 1. `board.py` — 파일명 동적화
**현재:** `post()`에서 코드 저장 시 `calculator.py` 하드코딩
**변경:**
- `post(sender, content, code, filename)` — filename 파라미터 추가
- filename이 주어지면 `OUTPUT_DIR / filename`에 저장
- task_board.json에 `target_file` 필드 추가 (소라가 첫 턴에 설정)

### 2. `sora_manager.py` — 핵심 변경 (동적 테스트 생성)
**현재:** `run_code()`가 calculator.py 전용 테스트 7개 하드코딩
**변경:**
- 소라 첫 턴: 태스크 분석 → **테스트 코드 + 파일명 + 요구사항**을 생성
  - Claude에게 "이 태스크에 맞는 pytest 코드를 만들어줘" 요청
  - 생성된 테스트를 `output/test_{filename}`으로 저장
  - board에 target_file 설정
- `run_code()` → `run_tests()` 리팩토링:
  - 하드코딩 테스트 삭제
  - 소라가 생성한 테스트 파일을 `pytest`로 실행
  - 결과 파싱: passed/failed 카운트
- 시스템 프롬프트 업데이트:
  - "첫 턴에는 반드시 테스트 코드를 먼저 작성하라"
  - "```test``` 블록으로 테스트 코드를 제출하라"
  - "테오에게 파일명과 클래스/함수 스펙을 명확히 전달하라"
  - "모든 테스트 통과 시 PROJECT_DONE"

### 3. `teo_dev.py` — 동적 파일명 지원
**현재:** 코드 추출 후 `calculator.py`에 저장
**변경:**
- board에서 `target_file` 읽어서 해당 파일명으로 저장
- 시스템 프롬프트에 "소라가 지정한 파일명으로 코드를 작성하라" 추가

### 4. `run_task.py` — 태스크 루프 + 다음 지시 대기
**현재:** 태스크 하나 완료 후 종료
**변경:**
- 태스크 완료 후 "다음 태스크를 입력하세요" 프롬프트
- 새 태스크 입력 시 board 초기화 → 에이전트들에게 새 태스크 전달
- `/quit` 입력 시 진짜 종료
- output/ 디렉토리 태스크별 관리 (기존 파일 유지)

---

## 새로운 흐름

```
[누나] "TODO 앱 만들어줘"
  ↓
run_task.py → board 초기화 (task="TODO 앱 만들어줘")
  ↓
[소라 턴1] 태스크 분석
  - "파일명: todo_app.py"
  - "테스트 코드 생성 → output/test_todo_app.py 저장"
  - "테오에게: todo_app.py를 만들어. 스펙은 이거야..."
  - board에 target_file="todo_app.py" 기록
  ↓
[테오 턴1] 코드 작성 → output/todo_app.py 저장
  ↓
[소라 턴2] pytest output/test_todo_app.py 실행
  - 3/5 passed → "테오, 이거 고쳐"
  ↓
[테오 턴2] 수정 → output/todo_app.py 덮어쓰기
  ↓
[소라 턴3] 5/5 passed → PROJECT_DONE
  ↓
run_task.py: "완료! 다음 태스크?"
  ↓
[누나] "이번엔 웹 스크래퍼 만들어줘"
  ↓
(반복)
```

---

## 소라의 테스트 생성 전략

소라 시스템 프롬프트에 다음 규칙 추가:

```
첫 번째 턴에서 반드시:
1. 태스크를 분석하고 파일명을 결정 (예: todo_app.py)
2. 테스트 코드를 ```test 블록으로 작성
3. 테오에게 파일명, 클래스/함수 스펙, 통과해야 할 테스트를 전달

테스트 코드 규칙:
- pytest 스타일
- 최소 5개, 최대 10개 테스트
- import는 target 파일에서 가져오기
- 기본 기능 + 에지 케이스 + 에러 처리 포함
```

소라가 Claude API로 생성하는 테스트 예시 (TODO 앱이라면):
```python
from todo_app import TodoApp

def test_add_task():
    app = TodoApp()
    app.add("밥 먹기")
    assert len(app.tasks) == 1

def test_complete_task():
    app = TodoApp()
    app.add("밥 먹기")
    app.complete(0)
    assert app.tasks[0]["done"] == True

# ... 등등
```

---

## task_board.json 구조 변경

```json
{
  "task": "TODO 앱 만들어줘",
  "status": "active",
  "turn": "sora",
  "target_file": "todo_app.py",
  "test_file": "test_todo_app.py",
  "messages": [...]
}
```

---

## 검증 방법

1. 터미널 3개로 실행 (기존과 동일)
2. "간단한 단위 변환기를 만들어줘" 같은 계산기 아닌 태스크 입력
3. 소라가 테스트 코드를 먼저 생성하는지 확인
4. 테오가 지정된 파일명으로 코드를 작성하는지 확인
5. 소라가 pytest로 검증하고 피드백 루프가 도는지 확인
6. 완료 후 "다음 태스크?" 프롬프트가 뜨는지 확인
7. 두 번째 태스크도 정상 작동하는지 확인

---

*작성일: 2026-03-12*
*작성자: 소라 (Claude Code 인스턴스)*
