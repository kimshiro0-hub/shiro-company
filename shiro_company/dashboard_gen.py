"""시로 컴퍼니 — 대시보드 HTML 생성기"""
import sys
import json
import os
import re
from pathlib import Path
from datetime import datetime
from collections import defaultdict

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

HERE = Path(__file__).parent
BUDGET_FILE = HERE / "budget.json"
OUTPUT_DIR = HERE / "output"
LOG_DIR = HERE / "logs"
DASHBOARD_DIR = HERE / "dashboard"


def load_budget() -> dict:
    if not BUDGET_FILE.exists():
        return {"month": "", "budget_usd": 5.0, "spent_usd": 0.0, "remaining_usd": 5.0, "calls": []}
    return json.loads(BUDGET_FILE.read_text(encoding="utf-8"))


def get_outputs() -> list:
    """output/ 안의 .py 파일 목록 (테스트 제외)"""
    if not OUTPUT_DIR.exists():
        return []
    items = []
    for f in sorted(OUTPUT_DIR.glob("*.py")):
        if f.name.startswith("test_") or f.name == "__init__.py":
            continue
        stat = f.stat()
        items.append({
            "name": f.name,
            "date": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
            "size": stat.st_size,
        })
    return items


def get_last_sora_message() -> str:
    """logs/에서 가장 최근 로그의 소라 마지막 메시지 추출"""
    if not LOG_DIR.exists():
        return "아직 로그가 없어요."
    logs = sorted(LOG_DIR.glob("task_*.log"), reverse=True)
    if not logs:
        return "아직 로그가 없어요."
    try:
        text = logs[0].read_text(encoding="utf-8")
        # [소라] 블록 찾기 — 마지막 것
        blocks = re.findall(r"\[소라\]\n((?:     .+\n?)+)", text)
        if blocks:
            msg = blocks[-1].replace("     ", "").strip()
            # PROJECT_DONE 등 제거
            msg = msg.replace("PROJECT_DONE", "").strip()
            if len(msg) > 200:
                msg = msg[:200] + "..."
            return msg
        return "소라의 메시지를 찾지 못했어요."
    except Exception:
        return "로그 읽기 실패."


def calc_daily_costs(calls: list) -> dict:
    """일별 비용 집계"""
    daily = defaultdict(float)
    for c in calls:
        day = c["time"][:10]  # "2026-03-12"
        daily[day] += c["cost_usd"]
    return dict(sorted(daily.items()))


def calc_agent_stats(calls: list) -> dict:
    """에이전트별 호출 수"""
    stats = defaultdict(int)
    for c in calls:
        stats[c["agent"]] += 1
    return dict(stats)


def calc_task_costs(calls: list) -> dict:
    """태스크별 비용"""
    costs = defaultdict(float)
    for c in calls:
        if not c["task"].startswith("[AUTO]"):
            costs[c["task"]] += c["cost_usd"]
    return dict(costs)


def generate_html(budget: dict, outputs: list, sora_msg: str) -> str:
    calls = budget.get("calls", [])
    daily = calc_daily_costs(calls)
    agent_stats = calc_agent_stats(calls)
    task_costs = calc_task_costs(calls)

    total_calls = len(calls)
    sora_calls = agent_stats.get("sora", 0)
    teo_calls = agent_stats.get("teo", 0)

    # 게이지바 퍼센트
    budget_total = budget.get("budget_usd", 5.0)
    remaining = budget.get("remaining_usd", budget_total)
    gauge_pct = max(0, min(100, (remaining / budget_total * 100))) if budget_total > 0 else 0

    # 차트 데이터
    daily_labels = json.dumps(list(daily.keys()))
    daily_values = json.dumps([round(v, 4) for v in daily.values()])

    # 산출물 갤러리 HTML
    gallery_rows = ""
    for o in outputs:
        cost = task_costs.get(o["name"].replace(".py", ""), 0)
        # 태스크 이름으로도 찾기
        for tk, tv in task_costs.items():
            if o["name"].replace(".py", "") in tk.lower().replace(" ", "_"):
                cost = tv
                break
        gallery_rows += f"""
        <tr>
          <td><code>{o['name']}</code></td>
          <td>{o['date']}</td>
          <td>{o['size']:,} B</td>
          <td>${cost:.4f}</td>
        </tr>"""
    if not gallery_rows:
        gallery_rows = '<tr><td colspan="4" style="text-align:center;opacity:0.5">아직 산출물이 없어요</td></tr>'

    # 소라 메시지 escape
    sora_escaped = sora_msg.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>시로 컴퍼니 대시보드</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js"></script>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: 'Segoe UI', -apple-system, sans-serif;
    background: #0f0f17;
    color: #e0e0e0;
    padding: 20px;
    max-width: 1200px;
    margin: 0 auto;
  }}
  h1 {{
    text-align: center;
    font-size: 1.6rem;
    margin-bottom: 8px;
    color: #fff;
  }}
  .subtitle {{
    text-align: center;
    font-size: 0.85rem;
    color: #888;
    margin-bottom: 24px;
  }}

  /* 요약 카드 */
  .cards {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 12px;
    margin-bottom: 24px;
  }}
  .card {{
    background: #1a1a2e;
    border-radius: 12px;
    padding: 16px;
    text-align: center;
  }}
  .card .value {{
    font-size: 1.8rem;
    font-weight: 700;
    color: #60a5fa;
  }}
  .card .label {{
    font-size: 0.8rem;
    color: #888;
    margin-top: 4px;
  }}
  .card.warn .value {{ color: #f59e0b; }}
  .card.good .value {{ color: #34d399; }}

  /* 섹션 */
  .section {{
    background: #1a1a2e;
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 16px;
  }}
  .section h2 {{
    font-size: 1.1rem;
    margin-bottom: 12px;
    color: #a78bfa;
  }}

  /* 차트 그리드 */
  .chart-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
    margin-bottom: 16px;
  }}
  @media (max-width: 700px) {{
    .chart-grid {{ grid-template-columns: 1fr; }}
  }}
  .chart-box {{
    background: #1a1a2e;
    border-radius: 12px;
    padding: 16px;
  }}
  .chart-box h3 {{
    font-size: 0.9rem;
    color: #888;
    margin-bottom: 8px;
  }}
  canvas {{ max-height: 220px; }}

  /* 게이지바 */
  .gauge {{
    background: #2a2a3e;
    border-radius: 8px;
    height: 28px;
    overflow: hidden;
    margin-top: 8px;
  }}
  .gauge-fill {{
    height: 100%;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.75rem;
    font-weight: 600;
    color: #fff;
    transition: width 0.5s;
  }}

  /* 테이블 */
  table {{
    width: 100%;
    border-collapse: collapse;
  }}
  th, td {{
    padding: 8px 12px;
    text-align: left;
    border-bottom: 1px solid #2a2a3e;
    font-size: 0.85rem;
  }}
  th {{ color: #888; font-weight: 500; }}
  code {{
    background: #2a2a3e;
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 0.8rem;
  }}

  /* CEO 한줄평 */
  .ceo-quote {{
    background: #1e1b4b;
    border-left: 3px solid #a78bfa;
    padding: 16px;
    border-radius: 0 12px 12px 0;
    font-style: italic;
    line-height: 1.6;
  }}
  .ceo-quote .author {{
    margin-top: 8px;
    font-style: normal;
    font-size: 0.8rem;
    color: #888;
  }}

  /* placeholder */
  .placeholder {{
    text-align: center;
    padding: 32px;
    color: #555;
    font-size: 0.9rem;
  }}

  .noscript-fallback {{ display: none; }}
</style>
</head>
<body>

<h1>시로 컴퍼니 대시보드</h1>
<p class="subtitle">{budget.get('month', 'N/A')} | 생성: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>

<!-- 요약 카드 -->
<div class="cards">
  <div class="card">
    <div class="value">${budget_total:.2f}</div>
    <div class="label">월 예산</div>
  </div>
  <div class="card warn">
    <div class="value">${budget.get('spent_usd', 0):.4f}</div>
    <div class="label">사용액</div>
  </div>
  <div class="card good">
    <div class="value">${remaining:.4f}</div>
    <div class="label">잔액</div>
  </div>
  <div class="card">
    <div class="value">{total_calls}</div>
    <div class="label">총 API 호출</div>
  </div>
</div>

<!-- 투자 트랙 -->
<div class="section">
  <h2>📈 투자 트랙</h2>
  <div class="placeholder">투자 모듈 준비 중</div>
</div>

<!-- 운영 트랙: 차트 -->
<div class="chart-grid">
  <div class="chart-box">
    <h3>에이전트별 호출 비율</h3>
    <canvas id="agentChart"></canvas>
    <noscript><div class="noscript-fallback">소라: {sora_calls}회 | 테오: {teo_calls}회</div></noscript>
  </div>
  <div class="chart-box">
    <h3>일별 비용 추이</h3>
    <canvas id="dailyChart"></canvas>
    <noscript><div class="noscript-fallback">Chart.js 필요</div></noscript>
  </div>
</div>

<!-- 예산 잔액 게이지 -->
<div class="section">
  <h2>💰 예산 잔액</h2>
  <div class="gauge">
    <div class="gauge-fill" style="width:{gauge_pct:.1f}%;background:{'#34d399' if gauge_pct > 50 else '#f59e0b' if gauge_pct > 10 else '#ef4444'}">
      {gauge_pct:.1f}%
    </div>
  </div>
  <p style="text-align:right;font-size:0.75rem;color:#888;margin-top:4px">${remaining:.4f} / ${budget_total:.2f}</p>
</div>

<!-- 산출물 갤러리 -->
<div class="section">
  <h2>📦 산출물 갤러리</h2>
  <table>
    <thead>
      <tr><th>파일</th><th>생성일</th><th>크기</th><th>비용</th></tr>
    </thead>
    <tbody>
      {gallery_rows}
    </tbody>
  </table>
</div>

<!-- CEO 한줄평 -->
<div class="section">
  <h2>🔵 소라의 마지막 코멘트</h2>
  <div class="ceo-quote">
    {sora_escaped}
    <div class="author">— 소라 (PM)</div>
  </div>
</div>

<script>
// 오프라인 체크 — Chart.js 없으면 텍스트 폴백
if (typeof Chart === 'undefined') {{
  document.querySelectorAll('canvas').forEach(c => {{
    const p = document.createElement('p');
    p.style.cssText = 'text-align:center;color:#555;padding:20px';
    p.textContent = '오프라인 — Chart.js를 로드할 수 없어요';
    c.parentNode.replaceChild(p, c);
  }});
}} else {{
  // 도넛 차트: 에이전트별 호출
  new Chart(document.getElementById('agentChart'), {{
    type: 'doughnut',
    data: {{
      labels: ['소라 (Claude)', '테오 (Gemini)'],
      datasets: [{{
        data: [{sora_calls}, {teo_calls}],
        backgroundColor: ['#60a5fa', '#34d399'],
        borderWidth: 0,
      }}]
    }},
    options: {{
      responsive: true,
      plugins: {{
        legend: {{ position: 'bottom', labels: {{ color: '#ccc', font: {{ size: 11 }} }} }}
      }}
    }}
  }});

  // 라인 차트: 일별 비용
  new Chart(document.getElementById('dailyChart'), {{
    type: 'line',
    data: {{
      labels: {daily_labels},
      datasets: [{{
        label: '비용 ($)',
        data: {daily_values},
        borderColor: '#a78bfa',
        backgroundColor: 'rgba(167,139,250,0.1)',
        fill: true,
        tension: 0.3,
        pointRadius: 4,
        pointBackgroundColor: '#a78bfa',
      }}]
    }},
    options: {{
      responsive: true,
      scales: {{
        x: {{ ticks: {{ color: '#888' }}, grid: {{ color: '#2a2a3e' }} }},
        y: {{ ticks: {{ color: '#888', callback: v => '$'+v.toFixed(3) }}, grid: {{ color: '#2a2a3e' }} }}
      }},
      plugins: {{
        legend: {{ display: false }}
      }}
    }}
  }});
}}
</script>

</body>
</html>"""


def main():
    DASHBOARD_DIR.mkdir(exist_ok=True)
    budget = load_budget()
    outputs = get_outputs()
    sora_msg = get_last_sora_message()

    html = generate_html(budget, outputs, sora_msg)
    out_path = DASHBOARD_DIR / "index.html"
    out_path.write_text(html, encoding="utf-8")
    print(f"  📊 대시보드 생성: {out_path}")
    return out_path


if __name__ == "__main__":
    path = main()
    # 브라우저에서 열기
    import webbrowser
    webbrowser.open(str(path))
