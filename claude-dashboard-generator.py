#!/usr/bin/env python3
"""
Claude Session Dashboard Generator
Run this script to regenerate the dashboard from live session files.
Usage: python3 claude-dashboard-generator.py
Output: claude-dashboard.html (open in browser)
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

# ── CONFIG ────────────────────────────────────────────────────────────────────
SESSION_DIR = Path(os.environ.get(
    "CLAUDE_SESSION_DIR",
    "/Users/jayden/Library/Application Support/Claude/local-agent-mode-sessions"
))

# Find the deepest session folder automatically
def find_session_dir(base: Path) -> Path:
    """Walk down to find the folder with local_*.json files"""
    if not base.exists():
        return base
    for root, dirs, files in os.walk(base):
        json_files = [f for f in files if f.startswith("local_") and f.endswith(".json")]
        if json_files:
            return Path(root)
    return base

WINDOW_BUDGET = 44_000   # estimated tokens per 5-hour Pro window
BYTES_PER_TOKEN = 3.5     # calibrated estimate from session analysis
OUTPUT_FILE = Path(__file__).parent / "claude-dashboard.html"

# ── DATA COLLECTION ──────────────────────────────────────────────────────────
def load_sessions(session_dir: Path) -> list:
    sessions = []
    if not session_dir.exists():
        print(f"⚠️  Session directory not found: {session_dir}", file=sys.stderr)
        return sessions

    for f in sorted(session_dir.glob("local_*.json")):
        size = f.stat().st_size
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            created = data.get("createdAt", "")
            last_activity = data.get("lastActivityAt", "")
            if isinstance(created, int):
                created = datetime.fromtimestamp(created / 1000).isoformat()
            if isinstance(last_activity, int):
                last_activity = datetime.fromtimestamp(last_activity / 1000).isoformat()
            created = str(created)
            last_activity = str(last_activity)
            sessions.append({
                "id": f.stem.replace("local_", ""),
                "title": str(data.get("title", "Untitled")),
                "createdAt": created,
                "lastActivityAt": last_activity,
                "model": str(data.get("model", "unknown")),
                "sizeBytes": size,
                "sizeKB": round(size / 1024, 1),
                "estimatedTokens": round(size / BYTES_PER_TOKEN),
                "hour": created[11:13] if len(created) >= 13 else "00"
            })
        except Exception as e:
            print(f"  Skip {f.name}: {e}", file=sys.stderr)

    sessions.sort(key=lambda x: x["createdAt"])
    return sessions


def parse_iso(s: str) -> datetime:
    """Parse ISO timestamp string to datetime, tolerating microseconds."""
    try:
        return datetime.strptime(s[:19], "%Y-%m-%dT%H:%M:%S")
    except Exception:
        return datetime.min


def build_chart_data(sessions: list, today: str) -> dict:
    by_date = defaultdict(list)
    for s in sessions:
        date = s["createdAt"][:10]
        by_date[date].append(s)

    # 14-day daily chart
    recent_dates = sorted(by_date.keys())[-14:]
    daily_labels, daily_sessions, daily_tokens_k = [], [], []
    for d in recent_dates:
        day_s = by_date[d]
        daily_labels.append(d[5:])
        daily_sessions.append(len(day_s))
        daily_tokens_k.append(round(sum(s["estimatedTokens"] for s in day_s) / 1000))

    # Hourly for today
    today_list = by_date.get(today, [])
    hourly = [0] * 24
    for s in today_list:
        h = int(s["hour"]) if s["hour"].isdigit() else 0
        hourly[h] += round(s["estimatedTokens"] / 1000)

    # ── FIXED: rolling 5-hour window anchored to most recent session ──
    # Counts all sessions within 5 hours BEFORE the most recent one
    window_start_iso = ""
    window_tokens = 0
    if sessions:
        most_recent = max(sessions, key=lambda s: s["createdAt"])
        most_recent_dt = parse_iso(most_recent["createdAt"])
        window_cutoff = most_recent_dt - timedelta(hours=5)
        window_start_iso = most_recent["createdAt"]
        window_tokens = sum(
            s["estimatedTokens"] for s in sessions
            if parse_iso(s["createdAt"]) >= window_cutoff
        )

    today_tokens = sum(s["estimatedTokens"] for s in today_list)
    total_tokens = sum(s["estimatedTokens"] for s in sessions)
    avg = round(total_tokens / len(sessions)) if sessions else 0

    # Model breakdown (last 30 sessions)
    model_counts = defaultdict(int)
    for s in sessions[-30:]:
        model_counts[s["model"]] += 1

    return {
        "generatedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "today": today,
        "todaySessionCount": len(today_list),
        "todayTokens": today_tokens,
        "totalSessions": len(sessions),
        "totalTokens": total_tokens,
        "avgTokensPerSession": avg,
        "windowTokens": window_tokens,
        "windowBudget": WINDOW_BUDGET,
        "windowPct": round(window_tokens / WINDOW_BUDGET * 100) if WINDOW_BUDGET else 0,
        "windowStartISO": window_start_iso,
        "dailyLabels": daily_labels,
        "dailySessions": daily_sessions,
        "dailyTokensK": daily_tokens_k,
        "hourlyTokensK": hourly,
        "recentSessions": sessions[-15:][::-1],
        "modelCounts": dict(model_counts),
    }


# ── HTML TEMPLATE ─────────────────────────────────────────────────────────────
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Claude Session Dashboard</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>
  :root {
    --bg: #0f1117; --card: #1a1d2e; --card2: #1e2235;
    --accent: #7c6ef5; --accent2: #5eead4;
    --warn: #f59e0b; --danger: #ef4444; --ok: #22c55e;
    --text: #e2e8f0; --muted: #64748b; --border: #2d3148;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: var(--bg); color: var(--text); font-family: 'Inter', system-ui, sans-serif; min-height: 100vh; }

  header { background: var(--card); border-bottom: 1px solid var(--border); padding: 16px 24px; display: flex; align-items: center; justify-content: space-between; }
  header h1 { font-size: 18px; font-weight: 600; letter-spacing: -0.3px; }
  header h1 span { color: var(--accent); }
  .gen-time { font-size: 12px; color: var(--muted); }
  .refresh-btn { background: var(--accent); color: white; border: none; border-radius: 8px; padding: 7px 16px; font-size: 13px; cursor: pointer; font-weight: 500; transition: opacity .2s; }
  .refresh-btn:hover { opacity: .85; }

  main { padding: 24px; max-width: 1400px; margin: 0 auto; }

  .kpi-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 24px; }
  .kpi { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 20px; }
  .kpi-label { font-size: 12px; color: var(--muted); text-transform: uppercase; letter-spacing: .5px; margin-bottom: 8px; }
  .kpi-value { font-size: 28px; font-weight: 700; line-height: 1; }
  .kpi-sub { font-size: 12px; color: var(--muted); margin-top: 6px; }
  .kpi.accent .kpi-value { color: var(--accent); }
  .kpi.teal .kpi-value { color: var(--accent2); }
  .kpi.warn .kpi-value { color: var(--warn); }
  .kpi.ok .kpi-value { color: var(--ok); }

  .window-card { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 20px; margin-bottom: 24px; }
  .window-card h2 { font-size: 14px; font-weight: 600; margin-bottom: 14px; color: var(--muted); text-transform: uppercase; letter-spacing: .5px; }
  .progress-bar-outer { background: var(--border); border-radius: 99px; height: 12px; overflow: hidden; margin-bottom: 8px; }
  .progress-bar-inner { height: 100%; border-radius: 99px; transition: width .5s ease; }
  .bar-ok { background: linear-gradient(90deg, var(--ok), var(--accent2)); }
  .bar-warn { background: linear-gradient(90deg, var(--warn), #f97316); }
  .bar-danger { background: linear-gradient(90deg, var(--danger), #dc2626); }
  .progress-labels { display: flex; justify-content: space-between; font-size: 12px; color: var(--muted); }
  .countdown { font-size: 32px; font-weight: 700; color: var(--accent); margin-top: 10px; }

  .charts-row { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 24px; }
  @media (max-width: 900px) { .charts-row { grid-template-columns: 1fr; } }
  .chart-card { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 20px; }
  .chart-card h2 { font-size: 14px; font-weight: 600; margin-bottom: 16px; color: var(--muted); text-transform: uppercase; letter-spacing: .5px; }
  .chart-wrap { position: relative; height: 220px; }

  .table-card { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 20px; }
  .table-card h2 { font-size: 14px; font-weight: 600; margin-bottom: 16px; color: var(--muted); text-transform: uppercase; letter-spacing: .5px; }
  table { width: 100%; border-collapse: collapse; font-size: 13px; }
  th { text-align: left; color: var(--muted); font-weight: 500; padding: 8px 12px; border-bottom: 1px solid var(--border); }
  td { padding: 10px 12px; border-bottom: 1px solid rgba(45,49,72,.5); vertical-align: middle; }
  tr:last-child td { border-bottom: none; } 
  tr:hover td { background: rgba(124,110,245,.05); }
  .model-badge { background: var(--border); border-radius: 6px; padding: 2px 8px; font-size: 11px; white-space: nowrap; }
  .model-badge.sonnet { background: rgba(124,110,245,.2); color: var(--accent); }
  .model-badge.haiku { background: rgba(94,234,212,.15); color: var(--accent2); }
  .model-badge.opus { background: rgba(251,191,36,.15); color: var(--warn); }
  .size-bar { display: inline-block; background: var(--accent); height: 6px; border-radius: 3px; vertical-align: middle; margin-left: 8px; opacity: .6; }
  .title-cell { max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .token-num { font-family: monospace; color: var(--accent2); }

  footer { text-align: center; padding: 24px; color: var(--muted); font-size: 12px; }
</style>
</head>
<body>

<header>
  <h1>⚡ Claude <span>Session Dashboard</span></h1>
  <div style="display:flex;align-items:center;gap:16px">
    <span class="gen-time" id="genTime">Generated: GENERATED_AT</span>
    <button class="refresh-btn" onclick="location.reload()">↻ Refresh</button>
  </div>
</header>

<main>

  <div class="kpi-row">
    <div class="kpi accent">
      <div class="kpi-label">Today's Sessions</div>
      <div class="kpi-value">TODAY_SESSION_COUNT</div>
      <div class="kpi-sub">TODAY</div>
    </div>
    <div class="kpi teal">
      <div class="kpi-label">Today's Est. Tokens</div>
      <div class="kpi-value">TODAY_TOKENS_K</div>
      <div class="kpi-sub">~3.5 bytes/token estimate</div>
    </div>
    <div class="kpi warn">
      <div class="kpi-label">5-Hr Window Used</div>
      <div class="kpi-value">WINDOW_PCT%</div>
      <div class="kpi-sub">WINDOW_TOKENS_K of WINDOW_BUDGET_K budget</div>
    </div>
    <div class="kpi ok">
      <div class="kpi-label">All-Time Sessions</div>
      <div class="kpi-value">TOTAL_SESSIONS</div>
      <div class="kpi-sub">AVG_TOKENS_K avg tokens/session</div>
    </div>
  </div>

  <div class="window-card">
    <h2>⏱ Active 5-Hour Window — Rolling Reset</h2>
    <div class="progress-bar-outer">
      <div class="progress-bar-inner WINDOW_BAR_CLASS" style="width: WINDOW_PCT_CSS%"></div>
    </div>
    <div class="progress-labels">
      <span>0</span>
      <span style="color:WINDOW_COLOR">WINDOW_TOKENS_K tokens used (WINDOW_PCT%)</span>
      <span>~WINDOW_BUDGET_K budget</span>
    </div>
    <div style="margin-top:14px; font-size:13px; color:var(--muted)">
      ℹ️ Claude Pro resets every 5 hours from first message in window. Budget is an estimate — actual limits vary.
      <div class="countdown" id="countdown"></div>
    </div>
  </div>

  <div class="charts-row">
    <div class="chart-card">
      <h2>📅 Sessions Per Day (14 days)</h2>
      <div class="chart-wrap"><canvas id="dailyChart"></canvas></div>
    </div>
    <div class="chart-card">
      <h2>🕐 Today's Token Usage by Hour</h2>
      <div class="chart-wrap"><canvas id="hourlyChart"></canvas></div>
    </div>
  </div>

  <div class="table-card">
    <h2>🗂 Recent Sessions</h2>
    <table>
      <thead>
        <tr>
          <th>Time</th>
          <th>Title</th>
          <th>Model</th>
          <th>Size</th>
          <th>Est. Tokens</th>
        </tr>
      </thead>
      <tbody>SESSIONS_HTML</tbody>
    </table>
  </div>

</main>

<footer>
  Claude Session Dashboard — auto-generated from local session files · Run <code>python3 claude-dashboard-generator.py</code> to refresh
</footer>

<script>
const DATA = DATA_JSON_PLACEHOLDER;

function updateCountdown() {
  // windowStartISO = most recent session timestamp; window expires 5h after that
  const anchor = DATA.windowStartISO ? new Date(DATA.windowStartISO).getTime() : null;
  const el = document.getElementById('countdown');
  if (!anchor) { el.textContent = 'No session data'; return; }
  const windowEnd = anchor + (5 * 60 * 60 * 1000);
  const now = Date.now();
  const diff = windowEnd - now;
  if (diff <= 0) {
    el.textContent = '✅ Window reset — new 5-hour window available';
    el.style.color = 'var(--ok)';
    return;
  }
  const h = Math.floor(diff / 3600000);
  const m = Math.floor((diff % 3600000) / 60000);
  const s = Math.floor((diff % 60000) / 1000);
  const resetTime = new Date(windowEnd).toLocaleTimeString('en-US', {hour:'2-digit', minute:'2-digit', hour12:true});
  el.textContent = `Next reset in: ${h}h ${m}m ${s}s  (at ${resetTime})`;
}
updateCountdown();
setInterval(updateCountdown, 1000);

new Chart(document.getElementById('dailyChart'), {
  type: 'bar',
  data: {
    labels: DATA.dailyLabels,
    datasets: [{
      label: 'Sessions',
      data: DATA.dailySessions,
      backgroundColor: 'rgba(124,110,245,0.7)',
      borderRadius: 6,
    }, {
      label: 'Tokens (K)',
      data: DATA.dailyTokensK,
      backgroundColor: 'rgba(94,234,212,0.4)',
      borderRadius: 6,
      yAxisID: 'y2'
    }]
  },
  options: {
    responsive: true, maintainAspectRatio: false,
    plugins: { legend: { labels: { color: '#94a3b8', font: { size: 11 } } } },
    scales: {
      x: { ticks: { color: '#64748b', font: { size: 10 } }, grid: { color: '#2d3148' } },
      y: { ticks: { color: '#64748b', font: { size: 10 } }, grid: { color: '#2d3148' }, title: { display: true, text: 'Sessions', color: '#64748b', font: { size: 10 } } },
      y2: { position: 'right', ticks: { color: '#5eead4', font: { size: 10 } }, grid: { display: false }, title: { display: true, text: 'Tokens K', color: '#5eead4', font: { size: 10 } } }
    }
  }
});

const hourLabels = Array.from({length:24}, (_,i) => i === 0 ? '12a' : i < 12 ? `${i}a` : i === 12 ? '12p' : `${i-12}p`);
new Chart(document.getElementById('hourlyChart'), {
  type: 'bar',
  data: {
    labels: hourLabels,
    datasets: [{
      label: 'Tokens (K)',
      data: DATA.hourlyTokensK,
      backgroundColor: DATA.hourlyTokensK.map((v, i) => {
        const now = new Date().getHours();
        return i === now ? 'rgba(245,158,11,0.8)' : 'rgba(124,110,245,0.5)';
      }),
      borderRadius: 4,
    }]
  },
  options: {
    responsive: true, maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: {
      x: { ticks: { color: '#64748b', font: { size: 9 }, maxRotation: 0 }, grid: { color: '#2d3148' } },
      y: { ticks: { color: '#64748b', font: { size: 10 } }, grid: { color: '#2d3148' } }
    }
  }
});
</script>
</body>
</html>
"""


def model_badge(model: str) -> str:
    if "sonnet" in model.lower():
        return '<span class="model-badge sonnet">Sonnet</span>'
    elif "haiku" in model.lower():
        return '<span class="model-badge haiku">Haiku</span>'
    elif "opus" in model.lower():
        return '<span class="model-badge opus">Opus</span>'
    return f'<span class="model-badge">{model[:12]}</span>'


def fmt_tokens(n: int) -> str:
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.0f}K"
    return str(n)


def build_html(data: dict) -> str:
    rows = []
    max_size = max((s["sizeKB"] for s in data["recentSessions"]), default=1)
    for s in data["recentSessions"]:
        time_str = s["createdAt"][5:16].replace("T", " ")
        bar_w = round(s["sizeKB"] / max_size * 60)
        rows.append(
            f"<tr>"
            f"<td style='color:var(--muted);font-size:12px;white-space:nowrap'>{time_str}</td>"
            f"<td class='title-cell'>{s['title']}</td>"
            f"<td>{model_badge(s['model'])}</td>"
            f"<td style='white-space:nowrap'>{s['sizeKB']}KB<span class='size-bar' style='width:{bar_w}px'></span></td>"
            f"<td class='token-num'>{fmt_tokens(s['estimatedTokens'])}</td>"
            f"</tr>"
        )

    sessions_html = "\n".join(rows)
    window_pct = data["windowPct"]
    window_pct_css = min(window_pct, 100)
    if window_pct < 60:
        bar_class, color = "bar-ok", "#22c55e"
    elif window_pct < 85:
        bar_class, color = "bar-warn", "#f59e0b"
    else:
        bar_class, color = "bar-danger", "#ef4444"

    html = HTML_TEMPLATE
    html = html.replace("GENERATED_AT", data["generatedAt"])
    html = html.replace("TODAY", data["today"])
    html = html.replace("TODAY_SESSION_COUNT", str(data["todaySessionCount"]))
    html = html.replace("TODAY_TOKENS_K", fmt_tokens(data["todayTokens"]))
    html = html.replace("WINDOW_PCT%", f"{window_pct}%")
    html = html.replace("WINDOW_PCT_CSS", str(window_pct_css))
    html = html.replace("WINDOW_TOKENS_K", fmt_tokens(data["windowTokens"]))
    html = html.replace("WINDOW_BUDGET_K", fmt_tokens(data["windowBudget"]))
    html = html.replace("TOTAL_SESSIONS", str(data["totalSessions"]))
    html = html.replace("AVG_TOKENS_K", fmt_tokens(data["avgTokensPerSession"]))
    html = html.replace("WINDOW_BAR_CLASS", bar_class)
    html = html.replace("WINDOW_COLOR", color)
    html = html.replace("SESSIONS_HTML", sessions_html)
    html = html.replace("DATA_JSON_PLACEHOLDER", json.dumps(data))
    return html


# ── MAIN ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("🔍 Scanning session files...")
    real_dir = find_session_dir(SESSION_DIR)
    print(f"   Directory: {real_dir}")
    sessions = load_sessions(real_dir)
    print(f"   Found {len(sessions)} sessions")

    if not sessions:
        print("❌ No sessions found. Check SESSION_DIR path.")
        sys.exit(1)

    today = datetime.now().strftime("%Y-%m-%d")
    data = build_chart_data(sessions, today)

    html = build_html(data)
    OUTPUT_FILE.write_text(html, encoding="utf-8")
    print(f"✅ Dashboard written → {OUTPUT_FILE}")
    print(f"   Today: {data['todaySessionCount']} sessions, {fmt_tokens(data['todayTokens'])} tokens")
    print(f"   5-hr window: {data['windowPct']}% used ({fmt_tokens(data['windowTokens'])} of {fmt_tokens(data['windowBudget'])})")
    print(f"   Window anchor: {data['windowStartISO']}")
