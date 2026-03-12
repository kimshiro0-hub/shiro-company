"""소라 — 시로 컴퍼니 PM (동적 테스트 생성 + 코드 실행)"""
import sys
import re
import subprocess
from pathlib import Path
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv(Path(__file__).parent.parent / ".env", override=True)
from board import wait_my_turn, wait_new_task, post, set_done, set_files, get_conversation, read_board, OUTPUT_DIR, BOARD_FILE, _lock
from budget_tracker import record_call
import json

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

# context.md 로드
CONTEXT_FILE = Path(__file__).parent / "context.md"
BOSS_CONTEXT = ""
if CONTEXT_FILE.exists():
    BOSS_CONTEXT = CONTEXT_FILE.read_text(encoding="utf-8")

SYSTEM = f"""너는 소라(空). 시로 컴퍼니의 PM. 34세.
- 테오(개발자 후배)와 대화하면서 프로젝트를 진행한다.
- 존댓말 사용. 테오한테는 "테오" 또는 "테오님"이라고 부름.
- 누나(보스)가 만족할 결과물을 만드는 게 목표.
- 기획, 설계, 리뷰를 담당. 직접 코드를 쓰지는 않음.

★ 누나 컨텍스트 (항상 참고):
{BOSS_CONTEXT}

★ 첫 번째 턴 필수 규칙:
1. 태스크를 분석해서 파일명을 결정 (예: todo_app.py, unit_converter.py)
2. 테스트 코드를 ```test 블록에 작성 (pytest 스타일, 5-10개)
3. 반드시 [FILE:파일명.py]를 응답 첫 줄에 써라
4. 테오에게: 파일명, 클래스/함수 스펙, 통과해야 할 테스트를 전달

테스트 코드 규칙:
- ```test 블록으로 감싸라 (```python 아님!)
- pytest 스타일 (def test_xxx 형식)
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
- 아직 FAIL이 있으면 절대 PROJECT_DONE을 붙이지 마라."""

client = Anthropic()
history = []
MAX_TURNS = 12
MAX_HISTORY = 8  # Claude에 보내는 최대 history 쌍 수


def trim_history():
    """history가 너무 길면 최근 MAX_HISTORY*2개만 유지"""
    if len(history) > MAX_HISTORY * 2:
        history[:] = history[-(MAX_HISTORY * 2):]


def extract_test_code(text: str) -> str | None:
    """소라 응답에서 ```test 블록 추출"""
    pattern = r"```test\s*\n(.*?)(?:```|$)"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return None


def extract_filename(text: str) -> str | None:
    """[FILE:xxx.py] 패턴에서 파일명 추출"""
    match = re.search(r"\[FILE:\s*(\S+\.py)\s*\]", text)
    if match:
        return match.group(1)
    return None


def run_tests(target_file: Path, test_file: Path) -> dict:
    """pytest로 테스트 실행"""
    if not target_file.exists():
        return {"success": False, "stage": "missing", "output": f"{target_file.name} 파일이 없어요."}
    if not test_file.exists():
        return {"success": False, "stage": "missing", "output": f"{test_file.name} 테스트 파일이 없어요."}

    # 1단계: import 체크
    module_name = target_file.stem
    result = subprocess.run(
        [sys.executable, "-c",
         f"import sys; sys.path.insert(0, r'{target_file.parent}'); import {module_name}; print('IMPORT_OK')"],
        capture_output=True, text=True, timeout=10, encoding="cp949", errors="replace"
    )
    if result.returncode != 0:
        return {"success": False, "stage": "import", "output": result.stderr}

    # 2단계: pytest 실행
    result = subprocess.run(
        [sys.executable, "-m", "pytest", str(test_file), "-v", "--tb=short", "--no-header"],
        capture_output=True, text=True, timeout=30,
        encoding="cp949", errors="replace",
        env={**__import__("os").environ, "PYTHONPATH": str(target_file.parent)}
    )
    output = result.stdout + result.stderr

    # 결과 파싱
    passed = len(re.findall(r"PASSED", output))
    failed = len(re.findall(r"FAILED", output))
    errors = len(re.findall(r"ERROR", output))

    return {
        "success": failed == 0 and errors == 0 and passed > 0,
        "stage": "test",
        "output": output,
        "passed": passed,
        "failed": failed + errors,
    }


def _current_task() -> str:
    """현재 board의 task 필드 읽기 (예산 기록용)"""
    try:
        data = read_board()
        return data.get("task", "unknown")
    except Exception:
        return "unknown"


def think(context: str, retries: int = 2) -> str:
    history.append({"role": "user", "content": context})
    trim_history()
    model = "claude-sonnet-4-20250514"
    for attempt in range(retries + 1):
        try:
            resp = client.messages.create(
                model=model,
                max_tokens=2048,
                system=SYSTEM,
                messages=history,
            )
            text = resp.content[0].text
            if not text:
                raise ValueError("Claude 응답이 비어있음")
            history.append({"role": "assistant", "content": text})
            # 예산 기록
            try:
                record_call(
                    agent="sora", model=model,
                    input_tokens=resp.usage.input_tokens,
                    output_tokens=resp.usage.output_tokens,
                    task=_current_task(),
                )
            except Exception:
                pass  # 예산 기록 실패해도 대화는 계속
            return text
        except Exception as e:
            print(f"  ⚠️ Claude 에러 (시도 {attempt+1}/{retries+1}): {e}")
            if attempt < retries:
                import time
                time.sleep(3)
    fallback = "테오님, 잠깐 시스템 에러가 있었어요. 다시 한번 보내주시겠어요?"
    history.append({"role": "assistant", "content": fallback})
    return fallback


def update_task(new_task: str):
    """board의 task 필드를 업데이트"""
    with _lock():
        data = json.loads(BOARD_FILE.read_text(encoding="utf-8"))
        data["task"] = new_task
        BOARD_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def decide_task() -> str:
    """context.md 기반으로 오늘 만들 산출물을 Claude에게 결정하게 함"""
    prompt = f"""오늘 누나에게 만들어줄 산출물을 하나 정해.
context.md를 참고해서, 누나한테 실제로 쓸모 있는 걸로.

조건:
- Python 단일 파일로 완성 가능한 것
- 더블클릭으로 바로 실행 가능한 것
- 15분 안에 완성 가능한 규모
- 이전에 만든 것과 겹치지 않게

태스크를 한 줄로 출력해. 예: "편의점 교대 시간 알림 타이머 만들어줘"
태스크 한 줄만. 다른 설명 금지."""

    history.append({"role": "user", "content": prompt})
    trim_history()
    model = "claude-sonnet-4-20250514"
    resp = client.messages.create(
        model=model,
        max_tokens=256,
        system=SYSTEM,
        messages=history,
    )
    task = resp.content[0].text.strip().strip('"').strip("'")
    history.append({"role": "assistant", "content": task})
    # 예산 기록
    try:
        record_call(
            agent="sora", model=model,
            input_tokens=resp.usage.input_tokens,
            output_tokens=resp.usage.output_tokens,
            task="[AUTO] 태스크 결정",
        )
    except Exception:
        pass
    return task


def run_one_task():
    """태스크 하나 처리. history는 유지됨."""
    target_file = None
    test_file = None
    turns = 0

    # [AUTO] 모드: 소라가 태스크 결정
    data = read_board()
    if data["task"].startswith("[AUTO]"):
        print("\n  🤖 자동 모드 — 태스크 결정 중...")
        decided = decide_task()
        update_task(decided)
        print(f"  💡 결정된 태스크: {decided}")

    while turns < MAX_TURNS:
        data = wait_my_turn("sora", timeout=300)
        if data is None:
            print("\n  ✅ 태스크 종료됨")
            return

        conv = get_conversation(data)
        turns += 1
        print(f"\n  ── 소라 턴 #{turns} ──")

        # 테오가 코드 제출했으면 테스트 실행
        exec_result = None
        if target_file and test_file:
            last_msg = data["messages"][-1] if data["messages"] else None
            if last_msg and last_msg["from"] == "teo" and last_msg.get("file"):
                print("  ⚡ 테스트 실행 중...")
                try:
                    exec_result = run_tests(target_file, test_file)
                    if exec_result["success"]:
                        print(f"  ✅ 모든 테스트 통과! ({exec_result.get('passed', '?')}개)")
                        print(exec_result.get("output", "")[:500])
                    else:
                        print(f"  ❌ 실패! (passed={exec_result.get('passed', 0)}, failed={exec_result.get('failed', 0)})")
                        print(exec_result.get("output", "")[:500])
                except Exception as e:
                    exec_result = {"success": False, "stage": "crash", "output": str(e)}
                    print(f"  💥 크래시: {e}")

        if exec_result:
            if exec_result["success"]:
                conv += f"\n\n[시스템] 테스트 결과: 모든 테스트 통과! ({exec_result.get('passed', '?')} passed, 0 failed)\n{exec_result.get('output', '')[:1000]}"
            else:
                conv += f"\n\n[시스템] 테스트 결과: 실패 (단계: {exec_result['stage']})\n{exec_result.get('output', '')[:1000]}"

        response = think(conv)
        print(f"  🔵 [소라] {response[:500]}\n")

        # 첫 턴: 테스트 코드 + 파일명 추출
        if turns == 1:
            fname = extract_filename(response)
            test_code = extract_test_code(response)

            if fname:
                target_file = OUTPUT_DIR / fname
                test_fname = f"test_{fname}"
                test_file = OUTPUT_DIR / test_fname
                set_files(fname, test_fname)
                print(f"  📋 타겟 파일: {fname}")

            if test_code and test_file:
                test_file.write_text(test_code, encoding="utf-8")
                print(f"  📋 테스트 저장: {test_file}")

        if "PROJECT_DONE" in response:
            clean = response.replace("PROJECT_DONE", "").strip()
            post("sora", clean)
            set_done()
            # 실행용 .bat 래퍼 자동 생성 (더블클릭 시 터미널 안 꺼지게)
            if target_file and target_file.exists():
                bat_file = target_file.with_suffix(".bat")
                bat_file.write_text(
                    f"@echo off\npython \"%~dp0{target_file.name}\"\npause\n",
                    encoding="utf-8",
                )
                print(f"  📦 실행파일: {bat_file}")
            print("=" * 50)
            print("  ✅ 프로젝트 완료!")
            print("=" * 50)
            return

        post("sora", response)

    print("  ⚠️ 최대 턴 도달. 종료.")
    set_done()


def main():
    print("=" * 50)
    print("  🔵 소라 (PM) 자율 대화 모드")
    print("  ⚡ 동적 테스트 생성 + 코드 실행")
    print("  🧠 태스크 간 맥락 유지")
    print("=" * 50)

    # 첫 태스크 처리
    run_one_task()

    # 다음 태스크 대기 루프
    while True:
        print("\n  ⏳ 다음 태스크 대기 중...")
        data = wait_new_task(timeout=600)
        if data is None:
            print("  ⏰ 대기 시간 초과. 종료.")
            return
        print(f"\n  📋 새 태스크: {data['task']}")
        run_one_task()


if __name__ == "__main__":
    main()
