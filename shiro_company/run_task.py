"""시로 컴퍼니 — 자율 협업 런처 + 모니터 + 태스크 루프"""
import sys
import time
import argparse
import subprocess
from pathlib import Path
from datetime import datetime
from board import init_board, read_board
from budget_tracker import get_remaining, get_task_cost, load_budget

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

HERE = Path(__file__).parent
LOG_DIR = HERE / "logs"
LOG_DIR.mkdir(exist_ok=True)

AUTO_TASK = "[AUTO] 소라가 context.md 기반으로 태스크 결정"


def monitor_task(log_file):
    """태스크 하나의 대화를 모니터링. 완료되면 리턴."""
    f = open(log_file, "w", encoding="utf-8")

    def log(text):
        print(text)
        f.write(text + "\n")
        f.flush()

    log("")
    log("=" * 60)
    log("  실시간 대화 로그")
    log("=" * 60)

    last_count = 0
    auto_resolved = False
    while True:
        data = read_board()
        msgs = data["messages"]

        # [AUTO] 모드에서 소라가 태스크를 결정하면 표시
        if not auto_resolved and not data["task"].startswith("[AUTO]") and data["task"]:
            log(f"\n  💡 소라가 결정한 태스크: {data['task']}")
            auto_resolved = True

        for msg in msgs[last_count:]:
            name = "[소라]" if msg["from"] == "sora" else "[테오]"
            log(f"\n  [{msg['time']}] {name}")
            for line in msg["content"].split("\n"):
                log(f"     {line}")
            if msg.get("file"):
                log(f"     📁 파일: {msg['file']}")

        last_count = len(msgs)

        if data["status"] == "done":
            target = data.get("target_file", "")
            log("")
            log("=" * 60)
            log("  ✅ 누나! 다 했어요!")
            if target:
                log(f"  📦 결과물: shiro_company/output/{target}")
            log(f"  📋 로그: {log_file}")
            log("=" * 60)
            break

        time.sleep(1)

    f.close()


def parse_args():
    parser = argparse.ArgumentParser(description="시로 컴퍼니 런처")
    parser.add_argument("task", nargs="*", help="태스크 (생략 시 소라 자율 판단)")
    parser.add_argument("--auto", action="store_true",
                        help="완전 자동 모드: 소라가 태스크 결정 → 완료 → 자동 종료")
    return parser.parse_args()


def main():
    args = parse_args()

    # 태스크 결정
    if args.task:
        task = " ".join(args.task)
    elif args.auto:
        # 예산 5% 이하면 실행 안 함
        try:
            budget = load_budget()
            remaining = budget["remaining_usd"]
            threshold = budget["budget_usd"] * 0.05
            if remaining <= threshold:
                print(f"\n  💸 예산 부족 (잔액: ${remaining:.4f}). 이번 달 운영 종료.")
                return
        except Exception:
            pass
        task = AUTO_TASK
        print("\n  🤖 완전 자동 모드 — 소라가 알아서 결정하고 완료 후 종료해요.")
    else:
        print("\n  시로 컴퍼니에 오신 걸 환영해요, 누나!")
        print("  태스크를 입력하면 소라와 테오가 알아서 해드릴게요.")
        print("  빈칸 Enter → 소라가 알아서 골라요.\n")
        task = input("  📝 태스크 (Enter=자동): ").strip()
        if not task:
            task = AUTO_TASK
            print(f"  🤖 자동 모드: {task}")

    # 에이전트 프로세스 실행 (한번만, 안 죽임)
    print("  에이전트 시작 중...")
    teo_proc = subprocess.Popen(
        [sys.executable, str(HERE / "teo_dev.py")],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        encoding="utf-8", errors="replace",
    )
    time.sleep(1)
    sora_proc = subprocess.Popen(
        [sys.executable, str(HERE / "sora_manager.py")],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        encoding="utf-8", errors="replace",
    )
    print("  🟢 테오 시작됨")
    print("  🔵 소라 시작됨")
    if not args.auto:
        print("  🧠 에이전트는 태스크 간 맥락을 기억해요")

    try:
        # 태스크 루프
        while True:
            print(f"\n  📋 태스크: {task}")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = LOG_DIR / f"task_{timestamp}.log"

            # 보드 초기화 → 에이전트들이 자동으로 감지
            init_board(task)

            # 모니터링 (완료될 때까지 대기)
            monitor_task(log_file)

            # 태스크 비용 출력
            try:
                done_data = read_board()
                actual_task = done_data.get("task", task)
                task_cost = get_task_cost(actual_task)
                remaining = get_remaining()
                print(f"  💰 이번 태스크 비용: ${task_cost:.4f} | 월 잔액: ${remaining:.4f}")
            except Exception:
                pass

            # 대시보드 자동 갱신
            try:
                subprocess.run(
                    [sys.executable, str(HERE / "dashboard_gen.py")],
                    capture_output=True, timeout=10,
                )
                print("  📊 대시보드 갱신 완료")
            except Exception:
                pass

            # --auto 모드: 1회 완료 후 즉시 종료
            if args.auto:
                print("\n  🏁 자동 모드 완료. 종료해요.")
                break

            # 에이전트 생존 확인
            if sora_proc.poll() is not None or teo_proc.poll() is not None:
                print("\n  ⚠️ 에이전트가 비정상 종료됐어요. 재시작이 필요해요.")
                break

            # 다음 태스크 입력
            print("")
            task = input("  📝 다음 태스크 (Enter=자동, q=종료): ").strip()
            if task.lower() == "q":
                print("\n  시로 컴퍼니를 이용해주셔서 감사해요, 누나! 👋")
                break
            if not task:
                task = AUTO_TASK
                print(f"  🤖 자동 모드: {task}")

    finally:
        # 종료 시 프로세스 정리
        for proc in [sora_proc, teo_proc]:
            if proc.poll() is None:
                proc.terminate()
                proc.wait(timeout=5)


if __name__ == "__main__":
    main()
