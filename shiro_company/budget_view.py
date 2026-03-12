"""시로 컴퍼니 — 예산 뷰어 (더블클릭으로 실행)"""
from budget_tracker import load_budget

def main():
    data = load_budget()
    print("=" * 50)
    print(f"  💰 시로 컴퍼니 예산 현황 ({data['month']})")
    print("=" * 50)
    print(f"  월 예산:  ${data['budget_usd']:.2f}")
    print(f"  사용액:   ${data['spent_usd']:.4f}")
    print(f"  잔액:     ${data['remaining_usd']:.4f}")
    print(f"  API 호출: {len(data['calls'])}회")
    print()

    if data["calls"]:
        # 에이전트별 요약
        sora_calls = [c for c in data["calls"] if c["agent"] == "sora"]
        teo_calls = [c for c in data["calls"] if c["agent"] == "teo"]
        sora_cost = sum(c["cost_usd"] for c in sora_calls)
        print(f"  소라: {len(sora_calls)}회 (${sora_cost:.4f})")
        print(f"  테오: {len(teo_calls)}회 ($0.0000, 무료)")
        print()

        # 최근 5건
        print("  ── 최근 호출 ──")
        for c in data["calls"][-5:]:
            cost_str = f"${c['cost_usd']:.4f}" if c["cost_usd"] > 0 else "무료"
            print(f"  {c['time']} | {c['agent']} | {cost_str} | {c['task'][:40]}")

    print()
    input("종료하려면 Enter를 누르세요...")


if __name__ == "__main__":
    main()
