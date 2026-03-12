"""시로 컴퍼니 — API 예산 트래커"""
import json
import time
from pathlib import Path
from filelock import FileLock

BUDGET_FILE = Path(__file__).parent / "budget.json"
BUDGET_LOCK = Path(__file__).parent / "budget.lock"

DEFAULT_BUDGET = {
    "month": time.strftime("%Y-%m"),
    "budget_usd": 5.00,
    "spent_usd": 0.00,
    "remaining_usd": 5.00,
    "calls": [],
}

# Claude Sonnet 4 가격 (2026-03 기준)
CLAUDE_INPUT_PER_1M = 3.00
CLAUDE_OUTPUT_PER_1M = 15.00


def _lock():
    return FileLock(str(BUDGET_LOCK), timeout=5)


def load_budget() -> dict:
    """budget.json 로드. 없거나 월이 바뀌었으면 초기화."""
    with _lock():
        if not BUDGET_FILE.exists():
            save_budget_unlocked(DEFAULT_BUDGET.copy())
            return DEFAULT_BUDGET.copy()

        data = json.loads(BUDGET_FILE.read_text(encoding="utf-8"))

        # 월이 바뀌었으면 리셋
        current_month = time.strftime("%Y-%m")
        if data.get("month") != current_month:
            fresh = DEFAULT_BUDGET.copy()
            fresh["month"] = current_month
            fresh["calls"] = []
            save_budget_unlocked(fresh)
            return fresh

        return data


def save_budget_unlocked(data: dict):
    """lock 없이 저장 (이미 lock 안에서 호출될 때 사용)"""
    BUDGET_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def save_budget(data: dict):
    """lock 잡고 저장"""
    with _lock():
        save_budget_unlocked(data)


def record_call(agent: str, model: str, input_tokens: int, output_tokens: int, task: str) -> dict:
    """API 호출 기록 + 비용 차감. 기록된 call dict 반환."""
    # 비용 계산
    if "claude" in model.lower() or "sonnet" in model.lower():
        cost = (input_tokens * CLAUDE_INPUT_PER_1M / 1_000_000) + \
               (output_tokens * CLAUDE_OUTPUT_PER_1M / 1_000_000)
    else:
        # Gemini Flash 등 무료 모델
        cost = 0.0

    cost = round(cost, 6)

    call = {
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "agent": agent,
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": cost,
        "task": task[:80],  # 너무 길면 자르기
    }

    with _lock():
        if not BUDGET_FILE.exists():
            data = DEFAULT_BUDGET.copy()
            data["month"] = time.strftime("%Y-%m")
            data["calls"] = []
        else:
            data = json.loads(BUDGET_FILE.read_text(encoding="utf-8"))

        # 월 체크
        current_month = time.strftime("%Y-%m")
        if data.get("month") != current_month:
            data = DEFAULT_BUDGET.copy()
            data["month"] = current_month
            data["calls"] = []

        data["calls"].append(call)
        data["spent_usd"] = round(data["spent_usd"] + cost, 6)
        data["remaining_usd"] = round(data["budget_usd"] - data["spent_usd"], 6)
        save_budget_unlocked(data)

    # 예산 경고 (10% 이하)
    if data["remaining_usd"] <= data["budget_usd"] * 0.10:
        print(f"  ⚠️ 예산 경고: 잔액 ${data['remaining_usd']:.4f}")

    return call


def get_remaining() -> float:
    """잔액 반환"""
    data = load_budget()
    return data["remaining_usd"]


def get_task_cost(task: str) -> float:
    """특정 태스크의 총 비용 계산"""
    data = load_budget()
    total = sum(c["cost_usd"] for c in data["calls"] if c["task"] == task[:80])
    return round(total, 6)
