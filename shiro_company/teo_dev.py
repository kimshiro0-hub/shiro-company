"""테오 — 시로 컴퍼니 개발자 (자율 대화형)"""
import sys
import os
import re
from pathlib import Path
from dotenv import load_dotenv
from google import genai

load_dotenv(Path(__file__).parent.parent / ".env", override=True)
from board import wait_my_turn, wait_new_task, post, get_conversation, read_board, OUTPUT_DIR
from budget_tracker import record_call

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

SYSTEM = """너는 테오(Teo). 시로 컴퍼니의 개발자. 28세 CTO.
- 소라 형(PM)과 대화하면서 프로젝트를 진행한다.
- 반말 사용. 소라를 "형"이라고 부름.

★★★ 최우선 규칙 ★★★
- 코드를 보낼 때: 설명 1줄 + ```python 블록 하나. 그 외 텍스트 금지.
- 설명이 길면 코드가 잘린다. 코드 앞뒤로 설명을 절대 길게 쓰지 마라.
- 코드는 반드시 완전한 파일 하나. 나눠 보내지 마라.
- 소라 형이 지정한 파일명과 스펙을 따라라.
- 대화만 할 때도 3줄 이내.
- 모든 .py 파일에 if __name__ == "__main__" 블록 필수. 데모 실행 + 마지막에 input("종료하려면 Enter를 누르세요...") 넣어라. 누나가 더블클릭으로 실행함."""

gemini = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
history = []
MAX_TURNS = 10
MAX_HISTORY = 6  # Gemini에 보내는 최대 history 쌍 수


def trim_history():
    """history가 너무 길면 최근 MAX_HISTORY*2개만 유지"""
    if len(history) > MAX_HISTORY * 2:
        history[:] = history[-(MAX_HISTORY * 2):]


def _current_task() -> str:
    """현재 board의 task 필드 읽기 (예산 기록용)"""
    try:
        data = read_board()
        return data.get("task", "unknown")
    except Exception:
        return "unknown"


def think(conversation: str, retries: int = 2) -> str:
    history.append({"role": "user", "parts": [{"text": conversation}]})
    trim_history()
    model = "gemini-2.5-flash"
    contents = [{"role": "user", "parts": [{"text": SYSTEM}]}] + history
    for attempt in range(retries + 1):
        try:
            resp = gemini.models.generate_content(
                model=model,
                contents=contents,
                config={"max_output_tokens": 8192},
            )
            text = resp.text
            if not text:
                raise ValueError("Gemini 응답이 비어있음")
            history.append({"role": "model", "parts": [{"text": text}]})
            # 예산 기록 (Gemini Flash 무료, 호출 횟수만 트래킹)
            try:
                usage = getattr(resp, "usage_metadata", None)
                in_tok = getattr(usage, "prompt_token_count", 0) if usage else 0
                out_tok = getattr(usage, "candidates_token_count", 0) if usage else 0
                record_call(
                    agent="teo", model=model,
                    input_tokens=in_tok, output_tokens=out_tok,
                    task=_current_task(),
                )
            except Exception:
                pass  # 예산 기록 실패해도 대화는 계속
            return text
        except Exception as e:
            print(f"  ⚠️ Gemini 에러 (시도 {attempt+1}/{retries+1}): {e}")
            if attempt < retries:
                import time
                time.sleep(3)
    # 모든 재시도 실패 — 빈 응답 반환 (프로세스 죽이지 않음)
    fallback = "형, 잠깐 에러가 났어. 다시 한번 알려줄래?"
    history.append({"role": "model", "parts": [{"text": fallback}]})
    return fallback


def extract_code(text: str) -> str | None:
    pattern = r"```(?:python)?\s*\n(.*?)(?:```|$)"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return None


def run_one_task():
    """태스크 하나 처리. history는 유지됨 (trim됨)."""
    turns = 0
    while turns < MAX_TURNS:
        data = wait_my_turn("teo", timeout=300)
        if data is None:
            print("\n  ✅ 태스크 종료됨")
            return

        conv = get_conversation(data)
        turns += 1
        print(f"\n  ── 테오 턴 #{turns} ──")

        response = think(conv)
        print(f"  🟢 [테오] {response[:500]}\n")

        code = extract_code(response)
        if code:
            target = data.get("target_file") or "output.py"
            path = OUTPUT_DIR / target
            path.write_text(code, encoding="utf-8")
            print(f"  📁 코드 저장: {path}")
            post("teo", response, code=code, filename=target)
        else:
            post("teo", response)

    print("  ⚠️ 최대 턴 도달. 종료.")


def main():
    print("=" * 50)
    print("  🟢 테오 (개발자) 자율 대화 모드")
    print("  🧠 태스크 간 맥락 유지")
    print("=" * 50)

    run_one_task()

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
