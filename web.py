import json
import logging
from datetime import datetime, timezone

from flask import Flask, jsonify, render_template_string

from storage.database import get_stats, get_unnotified_qualified

logger = logging.getLogger(__name__)

app = Flask(__name__)

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Web3 Builder Scanner</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#0a0a0f;color:#e0e0e0;min-height:100vh}
.header{background:linear-gradient(135deg,#1a1a2e 0%,#16213e 50%,#0f3460 100%);padding:24px 32px;border-bottom:1px solid #1e3a5f}
.header h1{font-size:24px;color:#fff;display:flex;align-items:center;gap:10px}
.header h1 span{color:#00d4aa}
.header p{color:#8892a4;font-size:14px;margin-top:4px}
.container{max-width:1200px;margin:0 auto;padding:24px}
.stats-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:16px;margin-bottom:24px}
.stat-card{background:#12121a;border:1px solid #1e2a3a;border-radius:12px;padding:20px;position:relative;overflow:hidden}
.stat-card::before{content:'';position:absolute;top:0;left:0;right:0;height:3px}
.stat-card.blue::before{background:linear-gradient(90deg,#3b82f6,#60a5fa)}
.stat-card.green::before{background:linear-gradient(90deg,#10b981,#34d399)}
.stat-card.purple::before{background:linear-gradient(90deg,#8b5cf6,#a78bfa)}
.stat-card.orange::before{background:linear-gradient(90deg,#f59e0b,#fbbf24)}
.stat-card.red::before{background:linear-gradient(90deg,#ef4444,#f87171)}
.stat-label{font-size:12px;color:#6b7280;text-transform:uppercase;letter-spacing:1px;margin-bottom:8px}
.stat-value{font-size:32px;font-weight:700;color:#fff}
.stat-sub{font-size:12px;color:#6b7280;margin-top:4px}
.section{background:#12121a;border:1px solid #1e2a3a;border-radius:12px;margin-bottom:24px;overflow:hidden}
.section-header{padding:16px 20px;border-bottom:1px solid #1e2a3a;display:flex;justify-content:space-between;align-items:center}
.section-header h2{font-size:16px;color:#fff}
.badge{background:#1e3a5f;color:#60a5fa;padding:4px 10px;border-radius:20px;font-size:12px;font-weight:600}
.badge.live{background:#064e3b;color:#34d399;animation:pulse 2s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.6}}
table{width:100%;border-collapse:collapse}
th{text-align:left;padding:12px 20px;font-size:12px;color:#6b7280;text-transform:uppercase;letter-spacing:1px;border-bottom:1px solid #1e2a3a;background:#0d0d14}
td{padding:12px 20px;border-bottom:1px solid #1a1a28;font-size:14px}
tr:hover td{background:#16162a}
.username{color:#3b82f6;text-decoration:none;font-weight:600}
.username:hover{text-decoration:underline}
.score-bar{height:6px;background:#1e2a3a;border-radius:3px;overflow:hidden;width:100px;display:inline-block;vertical-align:middle;margin-left:8px}
.score-fill{height:100%;border-radius:3px;transition:width .3s}
.score-high{background:linear-gradient(90deg,#10b981,#34d399)}
.score-mid{background:linear-gradient(90deg,#f59e0b,#fbbf24)}
.score-low{background:linear-gradient(90deg,#ef4444,#f87171)}
.signal-tag{display:inline-block;background:#1e2a3a;color:#94a3b8;padding:2px 8px;border-radius:6px;font-size:11px;margin:2px}
.status-dot{width:8px;height:8px;border-radius:50%;display:inline-block;margin-right:6px}
.status-dot.active{background:#34d399;box-shadow:0 0 6px #34d399}
.status-dot.idle{background:#6b7280}
.runs-list{padding:0}
.run-item{display:flex;justify-content:space-between;align-items:center;padding:12px 20px;border-bottom:1px solid #1a1a28}
.run-item:last-child{border-bottom:none}
.run-time{color:#6b7280;font-size:13px}
.run-stats{display:flex;gap:16px}
.run-stat{font-size:13px;color:#94a3b8}
.run-stat b{color:#fff}
.empty{text-align:center;padding:40px;color:#6b7280}
.footer{text-align:center;padding:24px;color:#4b5563;font-size:12px}
.btn{background:linear-gradient(135deg,#3b82f6,#2563eb);color:#fff;border:none;padding:8px 16px;border-radius:8px;cursor:pointer;font-size:13px;font-weight:600;transition:all .2s}
.btn:hover{transform:translateY(-1px);box-shadow:0 4px 12px rgba(59,130,246,.4)}
.btn:disabled{opacity:.5;cursor:not-allowed;transform:none;box-shadow:none}
.refresh-spin{animation:spin 1s linear infinite}
@keyframes spin{from{transform:rotate(0deg)}to{transform:rotate(360deg)}}
@media(max-width:768px){.stats-grid{grid-template-columns:repeat(2,1fr)}.container{padding:12px}th,td{padding:8px 12px}}
</style>
</head>
<body>
<div class="header">
<h1>&#9889; Web3 Builder <span>Scanner</span></h1>
<p>Automated discovery of genuine Web3 builders under 1k followers</p>
</div>
<div class="container">
<div class="stats-grid">
<div class="stat-card blue">
<div class="stat-label">Total Discovered</div>
<div class="stat-value" id="total">-</div>
<div class="stat-sub">accounts scanned</div>
</div>
<div class="stat-card green">
<div class="stat-label">Qualified</div>
<div class="stat-value" id="qualified">-</div>
<div class="stat-sub">score >= 60</div>
</div>
<div class="stat-card purple">
<div class="stat-label">Notified</div>
<div class="stat-value" id="notified">-</div>
<div class="stat-sub">sent to Telegram</div>
</div>
<div class="stat-card orange">
<div class="stat-label">Last Run</div>
<div class="stat-value" id="last-run" style="font-size:18px">-</div>
<div class="stat-sub" id="run-ago">-</div>
</div>
<div class="stat-card red">
<div class="stat-label">Status</div>
<div class="stat-value"><span class="status-dot active"></span>Active</div>
<div class="stat-sub">runs every hour</div>
</div>
</div>
<div class="section">
<div class="section-header">
<h2>Top Builders</h2>
<span class="badge" id="count-badge">0 found</span>
</div>
<div id="builders-list">
<div class="empty">Loading...</div>
</div>
</div>
<div class="section">
<div class="section-header">
<h2>Recent Runs</h2>
<button class="btn" onclick="loadData()" id="refresh-btn">Refresh</button>
</div>
<div id="runs-list" class="runs-list">
<div class="empty">Loading...</div>
</div>
</div>
</div>
<div class="footer">Web3 Builder Scanner &mdash; Discovers genuine builders, scores with AI, pushes to Telegram</div>
<script>
function timeAgo(iso){if(!iso)return'-';const s=Math.floor((Date.now()-new Date(iso))/1000);if(s<60)return s+'s ago';if(s<3600)return Math.floor(s/60)+'m ago';if(s<86400)return Math.floor(s/3600)+'h ago';return Math.floor(s/86400)+'d ago'}
function scoreClass(s){return s>=60?'score-high':s>=30?'score-mid':'score-low'}
function loadData(){
document.getElementById('refresh-btn').textContent='Loading...';
document.getElementById('refresh-btn').disabled=true;
fetch('/api/stats').then(r=>r.json()).then(d=>{
document.getElementById('total').textContent=d.total_accounts;
document.getElementById('qualified').textContent=d.qualified;
document.getElementById('notified').textContent=d.notified;
document.getElementById('last-run').textContent=d.last_run_short||d.last_run;
document.getElementById('run-ago').textContent=d.last_run_ago||'';
}).catch(e=>console.error(e));
fetch('/api/accounts').then(r=>r.json()).then(d=>{
const el=document.getElementById('builders-list');
document.getElementById('count-badge').textContent=d.length+' found';
if(!d.length){el.innerHTML='<div class="empty">No builders discovered yet. First run in progress...</div>';return}
el.innerHTML='<table><tr><th>Builder</th><th>Score</th><th>Followers</th><th>Signals</th><th>AI Verdict</th></tr>'+
d.map(a=>'<tr><td><a class="username" href="'+a.profile_url+'" target="_blank">@'+a.username+'</a><br><span style="color:#6b7280;font-size:12px">'+(a.name||'')+'</span></td><td><b>'+a.final_score+'</b>/100<span class="score-bar"><span class="score-fill '+scoreClass(a.final_score)+'" style="width:'+a.final_score+'%"></span></span></td><td>'+a.followers+'</td><td>'+((a.signals_list||[]).slice(0,3).map(s=>'<span class="signal-tag">'+s+'</span>').join(''))+'</td><td>'+(a.llm_verdict||'-')+'</td></tr>'
).join('')+'</table>';
}).catch(e=>console.error(e));
fetch('/api/runs').then(r=>r.json()).then(d=>{
const el=document.getElementById('runs-list');
if(!d.length){el.innerHTML='<div class="empty">No runs yet</div>';return}
el.innerHTML=d.map(r=>'<div class="run-item"><div><div class="run-time">'+r.timestamp+'</div></div><div class="run-stats"><span class="run-stat">Found <b>'+r.accounts_found+'</b></span><span class="run-stat">Qualified <b>'+r.accounts_qualified+'</b></span><span class="run-stat">Notified <b>'+r.accounts_notified+'</b></span><span class="run-stat">Errors <b>'+r.errors+'</b></span><span class="run-stat">'+r.duration_seconds+'s</span></div></div>').join('');
}).catch(e=>console.error(e));
document.getElementById('refresh-btn').textContent='Refresh';
document.getElementById('refresh-btn').disabled=false;
}
loadData();setInterval(loadData,30000);
</script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(DASHBOARD_HTML)


@app.route("/api/stats")
def api_stats():
    import sqlite3
    from config import settings

    db = sqlite3.connect(settings.db_path)
    cur = db.cursor()

    cur.execute("SELECT COUNT(*) FROM accounts")
    total = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM accounts WHERE qualifies = 1")
    qualified = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM accounts WHERE notified = 1")
    notified = cur.fetchone()[0]

    cur.execute("SELECT timestamp FROM runs ORDER BY id DESC LIMIT 1")
    row = cur.fetchone()
    last_run = row[0] if row else "never"

    last_run_short = last_run
    last_run_ago = ""
    if last_run and last_run != "never":
        try:
            dt = datetime.fromisoformat(last_run)
            diff = datetime.now(timezone.utc) - dt
            secs = int(diff.total_seconds())
            if secs < 60:
                last_run_ago = f"{secs}s ago"
            elif secs < 3600:
                last_run_ago = f"{secs // 60}m ago"
            elif secs < 86400:
                last_run_ago = f"{secs // 3600}h ago"
            else:
                last_run_ago = f"{secs // 86400}d ago"
            last_run_short = dt.strftime("%b %d, %H:%M UTC")
        except Exception:
            pass

    db.close()
    return jsonify({
        "total_accounts": total,
        "qualified": qualified,
        "notified": notified,
        "last_run": last_run,
        "last_run_short": last_run_short,
        "last_run_ago": last_run_ago,
    })


@app.route("/api/accounts")
def api_accounts():
    import sqlite3
    from config import settings

    db = sqlite3.connect(settings.db_path)
    db.row_factory = sqlite3.Row
    cur = db.cursor()
    cur.execute(
        "SELECT * FROM accounts ORDER BY final_score DESC LIMIT 100"
    )
    rows = cur.fetchall()
    db.close()

    result = []
    for row in rows:
        d = dict(row)
        try:
            d["signals_list"] = json.loads(d.get("signals") or "[]")
        except (json.JSONDecodeError, TypeError):
            d["signals_list"] = []
        d["profile_url"] = f"https://x.com/{d['username']}"
        result.append(d)

    return jsonify(result)


@app.route("/api/runs")
def api_runs():
    import sqlite3
    from config import settings

    db = sqlite3.connect(settings.db_path)
    db.row_factory = sqlite3.Row
    cur = db.cursor()
    cur.execute("SELECT * FROM runs ORDER BY id DESC LIMIT 20")
    rows = cur.fetchall()
    db.close()
    return jsonify([dict(row) for row in rows])
