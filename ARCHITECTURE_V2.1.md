# 시로 컴퍼니 v2.1 — 범용 자율 협업 시스템

> v2(계산기 전용)에서 v2.1(범용 태스크)로의 업그레이드 문서.
> 이전 버전 문서: ARCHITECTURE.md

---

## v2 → v2.1 변경 요약

| 항목 | v2 (이전) | v2.1 (현재) |
|------|-----------|-------------|
| 태스크 | calculator.py 전용 | 아무 태스크나 가능 |
| 테스트 | 7개 하드코딩 | 소라가 태스크별 동적 생성 (pytest) |
| 파일명 | calculator.py 고정 | 소라가 첫 턴에 결정 |
| 실행 | 터미널 3개 수동 실행 | `python run_task.py` 하나로 전부 |
| 프로세스 수명 | 태스크 끝나면 종료 | 태스크 간 유지 (맥락 기억) |
| 태스크 연속 | 불가 | 완료 후 다음 태스크 입력 대기 |

---

## 현재 디렉토리 구조

```
duo-chat/
├── .env                          # ANTHROPIC_API_KEY, GEMINI_API_KEY
├── ARCHITECTURE.md               # v2 문서 (이전 버전)
├── ARCHITECTURE_V2.1.md          # 이 문서
│
└── shiro_company/
    ├── board.py                  # 메시지 보드 (턴 관리 + 파일 잠금 + 태스크 대기)
    ├── run_task.py               # 원커맨드 런처 + 모니터 + 태스크 루프
    ├── sora_manager.py           # 소라 PM — 동적 테스트 생성 + pytest 실행
    ├── teo_dev.py                # 테오 Dev — 동적 파일명 코드 작성
    ├── task_board.json           # 현재 태스크 상태 + 대화 기록
    ├── output/                   # 생성된 결과물 + 테스트 파일
    │   ├── {target}.py           # 테오가 만든 코드
    │   └── test_{target}.py      # 소라가 생성한 테스트
    └── logs/                     # 태스크별 로그 (task_YYYYMMDD_HHMMSS.log)
```

---

## 실행 방법

```bash
cd shiro_company
python run_task.py "TODO 앱 만들어줘"
```

터미널 하나만 열면 됨. run_task.py가 소라/테오 프로세스를 자동 실행.
태스크 완료 후 "다음 태스크 (q=종료)" 프롬프트가 뜸.

---

## 전체 흐름

```
[누나] "TODO 앱 만들어줘"
  │
  ▼
run_task.py
  ├── init_board(task)  →  task_board.json (status=active, turn=sora)
  ├── Popen(teo_dev.py)   ← 먼저 실행
  └── Popen(sora_manager.py)
  │
  ▼ (모니터링 루프: 1초 폴링)
  │
  ├── [소라 턴1] 태스크 분석
  │   ├── [FILE:todo_app.py] 출력
  │   ├── ```test 블록으로 pytest 코드 생성 → output/test_todo_app.py 저장
  │   ├── board에 target_file="todo_app.py", test_file="test_todo_app.py" 기록
  │   └── 테오에게 스펙 전달
  │
  ├── [테오 턴1] 코드 작성
  │   ├── board["target_file"] 읽어서 파일명 결정
  │   └── output/todo_app.py 저장
  │
  ├── [소라 턴2] 테스트 실행
  │   ├── 1단계: import 체크 (subprocess)
  │   ├── 2단계: pytest output/test_todo_app.py -v (subprocess)
  │   ├── 결과 파싱: PASSED/FAILED 카운트
  │   └── 피드백 or PROJECT_DONE
  │
  ├── (실패 시 테오 수정 → 소라 재검증 반복)
  │
  ├── [소라] PROJECT_DONE → set_done()
  │
  ▼
run_task.py: "누나! 다 했어요! 결과물: output/todo_app.py"
  │
  ▼
"다음 태스크 (q=종료): "  ← 프로세스 안 죽음, 맥락 유지
  │
  ▼
[누나] "이번엔 단위 변환기 만들어줘"
  │
  ▼
init_board(새 태스크) → 에이전트들 wait_new_task()에서 감지 → 반복
```

---

## 모듈별 상세

### board.py — 메시지 보드

```python
# 주요 함수
init_board(task)                    # 태스크 초기화 (target_file, test_file 빈값)
set_files(target_file, test_file)   # 소라 첫 턴에서 호출 → 파일명 기록
post(sender, content, code, filename)  # 메시지 게시 + 턴 교대 + 코드 저장
read_board()                        # 보드 읽기
wait_my_turn(me, timeout=180)       # 내 턴 대기. done이면 None 반환
wait_new_task(timeout=600)          # done 상태에서 새 active 대기 (태스크 간 연결)
set_done()                          # status를 done으로
get_conversation(data, last_n=4)    # 최근 4개 메시지 텍스트 변환 (토큰 절약)
```

**task_board.json 구조 (v2.1):**
```json
{
  "task": "TODO 앱 만들어줘",
  "status": "active",
  "turn": "sora",
  "target_file": "todo_app.py",
  "test_file": "test_todo_app.py",
  "messages": [
    {
      "id": 0,
      "from": "sora",
      "content": "메시지 내용",
      "time": "15:23:24",
      "file": "output/todo_app.py"
    }
  ]
}
```

v2 대비 추가된 필드: `target_file`, `test_file`
v2 대비 추가된 함수: `set_files()`, `wait_new_task()`
post()에 `filename` 파라미터 추가 (동적 파일명 저장)

---

### sora_manager.py — 소라 PM

**v2.1 핵심 변경: 동적 테스트 생성**

소라의 첫 턴 동작:
1. Claude에게 태스크 분석 요청
2. 응답에서 `[FILE:파일명.py]` 파싱 → target_file 결정
3. 응답에서 `` ```test `` 블록 파싱 → pytest 코드 추출
4. `output/test_{파일명}.py`로 저장
5. `set_files()` 호출 → board에 기록
6. 테오에게 스펙 전달

소라의 이후 턴 동작:
1. 테오가 코드 제출했는지 확인 (last_msg.file 존재 여부)
2. `run_tests(target, test)` 실행:
   - 1단계: import 체크 (subprocess, cp949)
   - 2단계: `pytest test_file -v --tb=short` (subprocess)
   - PASSED/FAILED/ERROR 카운트 파싱
3. 결과를 컨텍스트에 추가 → Claude에게 판단 요청
4. 모든 테스트 통과 → "PROJECT_DONE" → set_done()

**시스템 프롬프트 핵심 규칙:**
- 첫 턴: `[FILE:xxx.py]` + `` ```test `` 블록 필수
- pytest 스타일, 5-10개 테스트
- 3-5줄 이내 응답
- 코드 나눠 보내라고 하지 마라
- FAIL 남아있으면 절대 PROJECT_DONE 붙이지 마라

**맥락 유지:**
- `history = []`는 모듈 레벨 변수
- `run_one_task()`가 끝나도 history 안 지움
- `main()` → `run_one_task()` → `wait_new_task()` → `run_one_task()` 루프
- 프로세스가 살아있는 한 이전 태스크 대화 기억

```python
# 추출 함수
extract_filename(text)   # [FILE:xxx.py] → "xxx.py"
extract_test_code(text)  # ```test ... ``` → 테스트 코드 문자열
```

---

### teo_dev.py — 테오 개발자

**v2.1 변경:**
- `OUTPUT_DIR / "calculator.py"` → `OUTPUT_DIR / data["target_file"]`
- 시스템 프롬프트에 "소라 형이 지정한 파일명/스펙을 따라라" 추가
- `run_one_task()` + `wait_new_task()` 루프로 맥락 유지

**코드 추출:** 기존과 동일
```python
pattern = r"```(?:python)?\s*\n(.*?)(?:```|$)"
```

---

### run_task.py — 런처/모니터

**v2.1 변경:**
- 터미널 1개로 전부 실행 (subprocess.Popen으로 소라/테오 자동 실행)
- 프로세스를 태스크 간에 안 죽임 (맥락 유지)
- 태스크 완료 후 "다음 태스크 (q=종료)" 입력 대기
- 에이전트 비정상 종료 감지
- try/finally로 종료 시 프로세스 정리 보장

```
실행 순서:
1. Popen(teo_dev.py)     ← 1초 먼저
2. Popen(sora_manager.py)
3. init_board(task)
4. monitor_task() — 1초 폴링으로 대화 실시간 출력 + 로그 저장
5. 완료 감지 → "다음 태스크?" → init_board(새 태스크) → 4번 반복
```

---

## 프로세스 수명 모델

```
run_task.py (메인 프로세스)
  │
  ├── teo_dev.py (서브 프로세스, 전체 세션 동안 유지)
  │   └── main() → run_one_task() → wait_new_task() → run_one_task() → ...
  │                  [history 누적]                      [history 유지]
  │
  └── sora_manager.py (서브 프로세스, 전체 세션 동안 유지)
      └── main() → run_one_task() → wait_new_task() → run_one_task() → ...
                     [history 누적]                      [history 유지]
```

- 에이전트 프로세스는 **세션 전체** 수명
- API history는 프로세스 메모리에 누적 → 이전 태스크 맥락 참조 가능
- board 대화는 태스크마다 리셋 (init_board) → 토큰 절약
- API history가 너무 길어지면 rate limit 이슈 가능 (현재 미대응, 향후 개선점)

---

## 의존성

```
pip install anthropic google-genai python-dotenv filelock pytest
```

---

## 알려진 제약 + 향후 개선점

### 유지되는 제약 (v2에서 그대로)
1. Gemini 출력 잘림 — 시스템 프롬프트로 완화
2. Windows cp949 인코딩 — subprocess에서 처리
3. Claude 30k 토큰/분 rate limit — get_conversation(last_n=4)로 완화
4. 파일 기반 통신 0.5초 지연

### v2.1에서 해결된 것
1. ~~코드 테스트 하드코딩~~ → 동적 테스트 생성
2. ~~파일명 고정~~ → 소라가 동적 결정
3. ~~터미널 3개 실행~~ → 원커맨드 실행
4. ~~태스크 간 기억 없음~~ → 프로세스 유지로 맥락 기억

### 새로운 제약/개선점
1. **API history 무한 증가** — 태스크 많아지면 토큰 비용 증가. 요약/압축 메커니즘 필요
2. **소라 테스트 품질** — Claude가 생성하는 테스트의 품질이 태스크 성공률을 좌우
3. **[FILE:] 파싱 실패** — 소라가 규칙 안 따르면 파일명 결정 못함. fallback 필요
4. **에이전트 비정상 종료** — 현재는 감지만 하고 재시작 안 함

---

## 다음 단계 (Level 2 후보)

1. **에이전트 3명 이상** — 리서처, QA 등 역할 추가
2. **오케스트레이터** — 턴 교대를 "소라↔테오 핑퐁"에서 → 동적 발언자 지정
3. **태스크 분해** — 큰 태스크를 서브태스크로 쪼개서 병렬 처리
4. **도구 접근권** — 에이전트별 파일/네트워크 권한
5. **통신 업그레이드** — 파일 폴링 → Redis/WebSocket

---

*문서 작성일: 2026-03-12*
*시로 컴퍼니 v2.1 기준*
*이전 문서: ARCHITECTURE.md (v2)*
