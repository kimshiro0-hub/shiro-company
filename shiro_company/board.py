"""시로 컴퍼니 메시지 보드 — 자율 대화형"""
import json
import time
from pathlib import Path
from filelock import FileLock

BOARD_FILE = Path(__file__).parent / "task_board.json"
LOCK_FILE = Path(__file__).parent / "task_board.lock"
OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


def _lock():
    return FileLock(str(LOCK_FILE), timeout=5)


def init_board(task: str):
    with _lock():
        data = {
            "task": task,
            "status": "active",
            "turn": "sora",
            "target_file": "",
            "test_file": "",
            "messages": [],
        }
        BOARD_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def set_files(target_file: str, test_file: str):
    """소라가 첫 턴에 파일명 결정 후 호출"""
    with _lock():
        data = json.loads(BOARD_FILE.read_text(encoding="utf-8"))
        data["target_file"] = target_file
        data["test_file"] = test_file
        BOARD_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def read_board() -> dict:
    with _lock():
        if not BOARD_FILE.exists():
            return {"task": "", "status": "idle", "turn": "", "messages": []}
        return json.loads(BOARD_FILE.read_text(encoding="utf-8"))


def post(sender: str, content: str, code: str = None, filename: str = None):
    """메시지 게시 + 턴 넘기기"""
    with _lock():
        data = json.loads(BOARD_FILE.read_text(encoding="utf-8"))
        msg = {
            "id": len(data["messages"]),
            "from": sender,
            "content": content,
            "time": time.strftime("%H:%M:%S"),
        }
        if code:
            fname = filename or data.get("target_file") or "output.py"
            path = OUTPUT_DIR / fname
            path.write_text(code, encoding="utf-8")
            msg["file"] = str(path)

        data["messages"].append(msg)
        data["turn"] = "teo" if sender == "sora" else "sora"
        BOARD_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return msg["id"]


def set_done():
    with _lock():
        data = json.loads(BOARD_FILE.read_text(encoding="utf-8"))
        data["status"] = "done"
        BOARD_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def wait_my_turn(me: str, timeout=180) -> dict | None:
    """내 턴이 올 때까지 대기, 보드 전체 반환. done이면 None."""
    start = time.time()
    while time.time() - start < timeout:
        data = read_board()
        if data["status"] == "done":
            return None
        if data["turn"] == me:
            return data
        time.sleep(0.5)
    return None


def wait_new_task(timeout=600) -> dict | None:
    """현재 태스크가 done 상태일 때, 새 태스크(active)가 올 때까지 대기"""
    start = time.time()
    while time.time() - start < timeout:
        data = read_board()
        if data["status"] == "active":
            return data
        time.sleep(1)
    return None


def get_conversation(data: dict, last_n: int = 4) -> str:
    """최근 대화를 텍스트로 변환 (토큰 절약)"""
    lines = [f"[태스크] {data['task']}"]
    recent = data["messages"][-last_n:] if len(data["messages"]) > last_n else data["messages"]
    for msg in recent:
        name = "소라" if msg["from"] == "sora" else "테오"
        # 코드가 너무 길면 앞부분만
        content = msg["content"]
        if len(content) > 1500:
            content = content[:1500] + "\n... (이하 생략)"
        lines.append(f"[{name}] {content}")
    return "\n\n".join(lines)
