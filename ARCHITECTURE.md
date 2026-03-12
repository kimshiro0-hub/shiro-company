# 시로 컴퍼니 멀티 에이전트 시스템 — 아키텍처 문서

## 프로젝트 개요

누나(보스)를 보좌하는 AI 멀티 에이전트 시스템.
소라(Claude, PM)와 테오(Gemini, 개발자)가 자율적으로 대화하며 태스크를 수행한다.

---

## 디렉토리 구조

```
duo-chat/
├── .env                          # API 키 (ANTHROPIC_API_KEY, GEMINI_API_KEY)
│
├── [v1] 단순 채팅 모드 (독립 인스턴스)
│   ├── chat.py                   # 유저 I/O 담당 (터미널 1)
│   ├── sora.py                   # 소라 인스턴스 - Claude API (터미널 2)
│   ├── teo.py                    # 테오 인스턴스 - Gemini API (터미널 3)
│   ├── shared.py                 # 파일 기반 메시지 버스 (messages.json)
│   └── messages.json             # 공유 메시지 저장소
│
├── [v2] 시로 컴퍼니 (자율 협업 모드)
│   └── shiro_company/
│       ├── board.py              # 메시지 보드 (턴 관리 + 파일 잠금)
│       ├── run_task.py           # 태스크 런처 + 실시간 모니터 + 로그 저장
│       ├── sora_manager.py       # 소라 PM (Claude) - 코드 실행 능력 보유
│       ├── teo_dev.py            # 테오 개발자 (Gemini) - 코드 작성
│       ├── task_board.json       # 현재 태스크 상태 + 대화 기록
│       ├── output/               # 생성된 결과물 (calculator.py 등)
│       └── logs/                 # 실행 로그 (task_YYYYMMDD_HHMMSS.log)
```

---

## 아키텍처 진화 과정

### v1: 단순 채팅 (3개 독립 프로세스)

```
[유저] ─input─→ chat.py ─write─→ messages.json
                                      │
                              ┌───read─┘───read──┐
                              ▼                   ▼
                          sora.py             teo.py
                        (Claude API)        (Gemini API)
                              │                   │
                              └───write──┬──write──┘
                                         ▼
                                   messages.json
                                         │
                              chat.py ←read─┘
                              (화면 출력)
```

- 통신: `messages.json` 파일 폴링 (0.3초 간격)
- 동기화: `filelock` 라이브러리
- 순서: 유저 → 소라 응답 → 테오 응답 (고정)

### v2: 자율 협업 (턴 기반 대화)

```
[누나/보스] ──태스크──→ run_task.py ──init──→ task_board.json
                           │                    (turn: "sora")
                           │ (모니터링)              │
                           │                ┌──read──┤──read──┐
                           │                ▼        │        ▼
                       실시간 출력      sora_manager  │    teo_dev
                       + 로그 저장      (Claude PM)   │   (Gemini Dev)
                                            │        │        │
                                            │   ┌────┘        │
                                            ▼   ▼             ▼
                                       코드 실행(subprocess)  코드 작성
                                       테스트 검증            파일 저장
                                            │                 │
                                            └──write──┬──write┘
                                                      ▼
                                              task_board.json
                                              (turn 교대)
```

---

## 핵심 모듈 상세

### board.py — 메시지 보드

```python
# 주요 함수
init_board(task)              # 태스크 초기화, turn="sora"로 시작
post(sender, content, code)   # 메시지 게시 + 턴 자동 교대
wait_my_turn(me, timeout)     # 자기 턴이 올 때까지 대기 (폴링)
get_conversation(data, last_n=4)  # 최근 N개 메시지를 텍스트로 변환

# 턴 교대 로직
post("sora", ...) → turn = "teo"
post("teo", ...)  → turn = "sora"
```

**task_board.json 구조:**
```json
{
  "task": "태스크 설명",
  "status": "active" | "done",
  "turn": "sora" | "teo",
  "messages": [
    {
      "id": 0,
      "from": "sora",
      "content": "메시지 내용",
      "time": "15:23:24",
      "file": "output/calculator.py"  // 코드 제출 시
    }
  ]
}
```

### sora_manager.py — 소라 PM

**역할:** 기획, 지시, 코드 리뷰, 실행 검증

**능력:**
- Claude API (claude-sonnet-4-20250514) 호출
- `subprocess.run()`으로 테오가 만든 코드를 실제 실행
- 자동화된 테스트 스위트 실행 (7개 테스트)
- 테스트 결과를 컨텍스트에 포함시켜 리뷰

**테스트 항목:**
1. import 성공 여부 (문법 에러 체크)
2. 사칙연산 5개 (2+3, 10-3, 4*5, 10/2, 10/3)
3. 0 나누기 에러 처리
4. 히스토리 저장 확인

**완료 조건:** 7/7 테스트 통과 시 "PROJECT_DONE" 선언

**토큰 절약:**
- 최근 4개 메시지만 컨텍스트에 포함
- 코드가 1500자 초과 시 앞부분만 전달

### teo_dev.py — 테오 개발자

**역할:** 코드 작성, 기술 제안, 수정

**능력:**
- Gemini API (gemini-2.5-flash) 호출
- 응답에서 코드블록 자동 추출 (정규식)
- 추출된 코드를 `output/` 디렉토리에 파일로 저장

**코드 추출:**
```python
# ```python ... ``` 패턴 매칭 (닫는 ``` 없어도 처리)
pattern = r"```(?:python)?\s*\n(.*?)(?:```|$)"
```

### run_task.py — 태스크 모니터

**역할:** 태스크 시작, 실시간 모니터링, 로그 저장

**기능:**
- `task_board.json` 변경 감지 (1초 폴링)
- 새 메시지를 터미널에 실시간 출력
- `logs/task_YYYYMMDD_HHMMSS.log`에 자동 저장
- `status: "done"` 감지 시 종료

---

## 실행 방법

```bash
cd shiro_company

# 터미널 1: 모니터 + 태스크 시작
python run_task.py "태스크 설명"

# 터미널 2: 테오 (먼저 실행 권장)
python teo_dev.py

# 터미널 3: 소라
python sora_manager.py
```

**실행 순서 중요:** 테오 → 소라 순서로 시작해야 턴 교대가 안정적

---

## 대화 흐름 예시

```
[보스] "Python CLI 계산기 만들어줘"
  ↓
[소라 턴1] 요구사항 분석 → 테오에게 지시
  ↓
[테오 턴1] 코드 v1 작성 → calculator.py 저장
  ↓
[소라 턴2] 코드 실행 → SyntaxError 발견 → 수정 요청
  ↓
[테오 턴2] 코드 v2 수정 → calculator.py 덮어쓰기
  ↓
[소라 턴3] 코드 실행 → 7/7 통과 → "PROJECT_DONE"
  ↓
[시스템] status="done" → 모든 프로세스 종료
```

---

## 알려진 제약 사항

1. **Gemini 출력 잘림:** 코드가 길면 중간에 끊김. 시스템 프롬프트로 "짧게 보내라" 강제
2. **Windows 인코딩:** subprocess에서 cp949 사용 필요 (encoding="cp949", errors="replace")
3. **API Rate Limit:** 대화가 길어지면 Claude 30k 토큰/분 제한 도달. 최근 4개 메시지만 전달로 완화
4. **턴 교대 타이밍:** 프로세스 시작 순서가 중요. 테오를 먼저 띄워야 안정적
5. **파일 기반 통신:** 폴링 방식이라 지연 있음 (0.5초). 에이전트 수 증가 시 병목 가능
6. **코드 테스트 하드코딩:** calculator.py 전용 테스트. 다른 태스크에는 테스트 로직 수정 필요

---

## 다음 단계를 위한 개선 포인트

1. **에이전트 추가:** 리서처, QA, 디자이너 등 역할 확장
2. **통신 구조:** 파일 폴링 → Redis pub/sub 또는 WebSocket
3. **동적 테스트:** 태스크에 따라 테스트 코드를 소라가 자동 생성
4. **태스크 큐:** 완료 후 대기 모드 → 다음 태스크 자동 수신
5. **오케스트레이터:** 중앙 컨트롤러가 에이전트 배정/모니터링
6. **도구 접근권:** 에이전트별 권한 체계 (파일 접근, 네트워크 등)
7. **메모리:** 이전 태스크 결과를 다음 태스크에서 참조

---

## API 사용 현황

| 에이전트 | API | 모델 | 비용 |
|---------|-----|------|------|
| 소라 (PM) | Anthropic Claude | claude-sonnet-4-20250514 | 유료 (토큰당) |
| 테오 (Dev) | Google Gemini | gemini-2.5-flash | 무료 티어 |

---

*문서 작성일: 2026-03-12*
*시로 컴퍼니 v2 기준*
