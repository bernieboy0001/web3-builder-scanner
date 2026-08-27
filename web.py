import json
import logging
from datetime import datetime, timezone

from flask import Flask, jsonify, render_template_string

logger = logging.getLogger(__name__)

app = Flask(__name__)


@app.errorhandler(Exception)
def handle_error(e):
    import traceback
    tb = traceback.format_exc()
    logger.error(f"API error: {e}\n{tb}")
    return jsonify({"error": str(e), "traceback": tb.splitlines()[-5:]}), 500

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
.stats-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:16px;margin-bottom:24px}
.stat-card{background:#12121a;border:1px solid #1e2a3a;border-radius:12px;padding:20px;position:relative;overflow:hidden}
.stat-card::before{content:'';position:absolute;top:0;left:0;right:0;height:3px}
.stat-card.blue::before{background:linear-gradient(90deg,#3b82f6,#60a5fa)}
.stat-card.green::before{background:linear-gradient(90deg,#10b981,#34d399)}
.stat-card.purple::before{background:linear-gradient(90deg,#8b5cf6,#a78bfa)}
.stat-card.orange::before{background:linear-gradient(90deg,#f59e0b,#fbbf24)}
.stat-card.red::before{background:linear-gradient(90deg,#ef4444,#f87171)}
.stat-card.cyan::before{background:linear-gradient(90deg,#06b6d4,#22d3ee)}
.stat-label{font-size:11px;color:#6b7280;text-transform:uppercase;letter-spacing:1px;margin-bottom:8px}
.stat-value{font-size:28px;font-weight:700;color:#fff}
.stat-sub{font-size:11px;color:#6b7280;margin-top:4px}
.section{background:#12121a;border:1px solid #1e2a3a;border-radius:12px;margin-bottom:24px;overflow:hidden}
.section-header{padding:16px 20px;border-bottom:1px solid #1e2a3a;display:flex;justify-content:space-between;align-items:center}
.section-header h2{font-size:16px;color:#fff;display:flex;align-items:center;gap:8px}
.badge{background:#1e3a5f;color:#60a5fa;padding:4px 10px;border-radius:20px;font-size:12px;font-weight:600}
.badge.green{background:#064e3b;color:#34d399}
.badge.orange{background:#78350f;color:#fbbf24}
.badge.purple{background:#3b0764;color:#c084fc}
.tabs{display:flex;gap:4px;padding:12px 20px;background:#0d0d14;border-bottom:1px solid #1e2a3a}
.tab{padding:8px 16px;border-radius:8px;cursor:pointer;font-size:13px;color:#6b7280;transition:all .2s;border:none;background:transparent}
.tab:hover{color:#e0e0e0;background:#1e2a3a}
.tab.active{color:#fff;background:#1e3a5f}
table{width:100%;border-collapse:collapse}
th{text-align:left;padding:12px 20px;font-size:11px;color:#6b7280;text-transform:uppercase;letter-spacing:1px;border-bottom:1px solid #1e2a3a;background:#0d0d14}
td{padding:12px 20px;border-bottom:1px solid #1a1a28;font-size:14px}
tr:hover td{background:#16162a}
.username{color:#3b82f6;text-decoration:none;font-weight:600}
.username:hover{text-decoration:underline}
.project-name{color:#a78bfa;font-weight:600}
.score-bar{height:6px;background:#1e2a3a;border-radius:3px;overflow:hidden;width:80px;display:inline-block;vertical-align:middle;margin-left:8px}
.score-fill{height:100%;border-radius:3px;transition:width .3s}
.score-high{background:linear-gradient(90deg,#10b981,#34d399)}
.score-mid{background:linear-gradient(90deg,#f59e0b,#fbbf24)}
.score-low{background:linear-gradient(90deg,#ef4444,#f87171)}
.signal-tag{display:inline-block;background:#1e2a3a;color:#94a3b8;padding:2px 8px;border-radius:6px;font-size:11px;margin:2px}
.chain-tag{display:inline-block;padding:2px 8px;border-radius:6px;font-size:11px;font-weight:600;margin:2px}
.chain-eth{background:#627eea22;color:#627eea}
.chain-base{background:#0052ff22;color:#5a9dff}
.chain-arb{background:#28a0f022;color:#28a0f0}
.chain-poly{background:#8247e522;color:#a06aef}
.chain-sol{background:#9945ff22;color:#9945ff}
.chain-default{background:#6b728022;color:#94a3b8}
.type-tag{display:inline-block;padding:2px 8px;border-radius:6px;font-size:11px;font-weight:500}
.type-defi{background:#10b98115;color:#34d399}
.type-nft{background:#8b5cf615;color:#a78bfa}
.type-token{background:#f59e0b15;color:#fbbf24}
.type-infra{background:#3b82f615;color:#60a5fa}
.type-tooling{background:#06b6d415;color:#22d3ee}
.type-other{background:#6b728015;color:#94a3b8}
.status-dot{width:8px;height:8px;border-radius:50%;display:inline-block;margin-right:6px}
.status-dot.active{background:#34d399;box-shadow:0 0 6px #34d399}
.runs-list{padding:0}
.run-item{display:flex;justify-content:space-between;align-items:center;padding:12px 20px;border-bottom:1px solid #1a1a28}
.run-item:last-child{border-bottom:none}
.run-time{color:#6b7280;font-size:13px}
.run-stats{display:flex;gap:16px;flex-wrap:wrap}
.run-stat{font-size:13px;color:#94a3b8}
.run-stat b{color:#fff}
.empty{text-align:center;padding:40px;color:#6b7280}
.footer{text-align:center;padding:24px;color:#4b5563;font-size:12px}
.btn{background:linear-gradient(135deg,#3b82f6,#2563eb);color:#fff;border:none;padding:8px 16px;border-radius:8px;cursor:pointer;font-size:13px;font-weight:600;transition:all .2s}
.btn:hover{transform:translateY(-1px);box-shadow:0 4px 12px rgba(59,130,246,.4)}
.btn:disabled{opacity:.5;cursor:not-allowed}
@media(max-width:768px){.stats-grid{grid-template-columns:repeat(2,1fr)}.container{padding:12px}th,td{padding:8px 12px}.run-stats{gap:8px}}
</style>
</head>
<body>
<div class="header">
<h1>&#9889; Web3 Builder <span>Scanner</span></h1>
<p>Discovering genuine Web3 builders & newly launched projects under 1k followers</p>
</div>
<div class="container">
<div class="stats-grid">
<div class="stat-card blue">
<div class="stat-label">Builders Found</div>
<div class="stat-value" id="total">-</div>
<div class="stat-sub">accounts scanned</div>
</div>
<div class="stat-card cyan">
<div class="stat-label">Projects</div>
<div class="stat-value" id="projects-count">-</div>
<div class="stat-sub">newly launched</div>
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
<div class="stat-label">No Website</div>
<div class="stat-value" id="no-website-count">-</div>
<div class="stat-sub">builders needing sites</div>
</div>
<div class="stat-card red">
<div class="stat-label">Status</div>
<div class="stat-value"><span class="status-dot active"></span>Live</div>
<div class="stat-sub" id="last-run">-</div>
</div>
</div>

<div class="tabs">
<button class="tab active" onclick="switchTab('projects')">New Projects</button>
<button class="tab" onclick="switchTab('builders')">Top Builders</button>
<button class="tab" onclick="switchTab('nowebsite')">No Website Yet</button>
<button class="tab" onclick="switchTab('runs')">Run History</button>
</div>

<div id="tab-projects" class="section" style="border-radius:0 0 12px 12px;margin-top:-1px">
<div class="section-header">
<h2> Newly Launched Projects <span class="badge green" id="proj-badge">0</span></h2>
</div>
<div id="projects-list"><div class="empty">Loading...</div></div>
</div>

<div id="tab-builders" class="section" style="display:none;border-radius:0 0 12px 12px;margin-top:-1px">
<div class="section-header">
<h2>Top Builders</h2>
<span class="badge" id="count-badge">0</span>
</div>
<div id="builders-list"><div class="empty">Loading...</div></div>
</div>

<div id="tab-nowebsite" class="section" style="display:none;border-radius:0 0 12px 12px;margin-top:-1px">
<div class="section-header">
<h2>Builders Without Websites <span class="badge orange" id="nw-badge">0</span></h2>
</div>
<div id="nowebsite-list"><div class="empty">Loading...</div></div>
</div>

<div id="tab-runs" class="section" style="display:none;border-radius:0 0 12px 12px;margin-top:-1px">
<div class="section-header">
<h2>Run History</h2>
<button class="btn" onclick="loadData()" id="refresh-btn">Refresh</button>
</div>
<div id="runs-list" class="runs-list"><div class="empty">Loading...</div></div>
</div>
</div>
<div class="footer">Web3 Builder Scanner &mdash; Discovers genuine builders & projects, scores with AI, pushes to Telegram</div>
<script>
function scoreClass(s){return s>=60?'score-high':s>=30?'score-mid':'score-low'}
function chainClass(c){if(!c)return'chain-default';c=c.toLowerCase();if(c.includes('eth'))return'chain-eth';if(c.includes('base'))return'chain-base';if(c.includes('arb'))return'chain-arb';if(c.includes('poly'))return'chain-poly';if(c.includes('sol'))return'chain-sol';return'chain-default'}
function typeClass(t){if(!t)return'type-other';t=t.toLowerCase();if(t.includes('defi'))return'type-defi';if(t.includes('nft'))return'type-nft';if(t.includes('token'))return'type-token';if(t.includes('infra'))return'type-infra';if(t.includes('tool'))return'type-tooling';return'type-other'}
let activeTab='projects';
function switchTab(t){document.querySelectorAll('.tab').forEach(e=>e.classList.remove('active'));document.querySelectorAll('[id^=tab-]').forEach(e=>e.style.display='none');event.target.classList.add('active');document.getElementById('tab-'+t).style.display='';activeTab=t}
function loadData(){
fetch('/api/stats').then(r=>r.json()).then(d=>{
document.getElementById('total').textContent=d.total_accounts;
document.getElementById('projects-count').textContent=d.projects_count;
document.getElementById('qualified').textContent=d.qualified;
document.getElementById('notified').textContent=d.notified;
document.getElementById('no-website-count').textContent=d.no_website;
document.getElementById('last-run').textContent=d.last_run_short||d.last_run;
}).catch(e=>console.error(e));
fetch('/api/projects').then(r=>r.json()).then(d=>{
document.getElementById('proj-badge').textContent=d.length;
const el=document.getElementById('projects-list');
if(!d.length){el.innerHTML='<div class="empty">No projects discovered yet. Scanning...</div>';return}
el.innerHTML='<table><tr><th>Project</th><th>Chain</th><th>Type</th><th>Builder</th><th>Score</th><th>Links</th></tr>'+
d.map(p=>'<tr><td><span class="project-name">'+p.name+'</span><br><span style="color:#6b7280;font-size:12px;max-width:300px;display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">'+(p.description||'').substring(0,80)+'</span></td><td><span class="chain-tag '+chainClass(p.chain)+'">'+p.chain+'</span></td><td><span class="type-tag '+typeClass(p.project_type)+'">'+p.project_type+'</span></td><td><a class="username" href="https://x.com/'+p.username+'" target="_blank">@'+p.username+'</a></td><td><b>'+p.score+'</b>/100<span class="score-bar"><span class="score-fill '+scoreClass(p.score)+'" style="width:'+p.score+'%"></span></span></td><td>'+(p.url?'<a href="'+p.url+'" target="_blank" style="color:#3b82f6;text-decoration:none;font-size:12px">Link</a>':'')+(p.github_url?' <a href="'+p.github_url+'" target="_blank" style="color:#94a3b8;text-decoration:none;font-size:12px">GitHub</a>':'')+'</td></tr>'
).join('')+'</table>';
}).catch(e=>console.error(e));
fetch('/api/accounts').then(r=>r.json()).then(d=>{
document.getElementById('count-badge').textContent=d.length;
const el=document.getElementById('builders-list');
if(!d.length){el.innerHTML='<div class="empty">No builders discovered yet.</div>';return}
el.innerHTML='<table><tr><th>Builder</th><th>Score</th><th>Followers</th><th>Project</th><th>Signals</th><th>AI</th></tr>'+
d.map(a=>'<tr><td><a class="username" href="'+a.profile_url+'" target="_blank">@'+a.username+'</a><br><span style="color:#6b7280;font-size:12px">'+(a.name||'')+'</span></td><td><b>'+a.final_score+'</b>/100<span class="score-bar"><span class="score-fill '+scoreClass(a.final_score)+'" style="width:'+a.final_score+'%"></span></span></td><td>'+a.followers+'</td><td>'+(a.project_name?'<span style="color:#a78bfa;font-size:13px">'+a.project_name+'</span><br><span class="chain-tag '+chainClass(a.project_chain)+'" style="font-size:10px">'+a.project_chain+'</span>':'<span style="color:#6b7280;font-size:12px">-</span>')+'</td><td>'+((a.signals_list||[]).slice(0,3).map(s=>'<span class="signal-tag">'+s+'</span>').join(''))+'</td><td><span style="font-size:12px">'+(a.llm_verdict||'-')+'</span></td></tr>'
).join('')+'</table>';
}).catch(e=>console.error(e));
fetch('/api/no-website').then(r=>r.json()).then(d=>{
document.getElementById('nw-badge').textContent=d.length;
const el=document.getElementById('nowebsite-list');
if(!d.length){el.innerHTML='<div class="empty">No no-website builders found yet.</div>';return}
el.innerHTML='<table><tr><th>Builder</th><th>Score</th><th>Followers</th><th>Bio</th><th>Signals</th><th>Action</th></tr>'+
d.map(a=>'<tr><td><a class="username" href="'+a.profile_url+'" target="_blank">@'+a.username+'</a><br><span style="color:#6b7280;font-size:12px">'+(a.name||'')+'</span></td><td><b>'+a.final_score+'</b>/100<span class="score-bar"><span class="score-fill '+scoreClass(a.final_score)+'" style="width:'+a.final_score+'%"></span></span></td><td>'+a.followers+'</td><td><span style="color:#6b7280;font-size:12px;max-width:250px;display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">'+(a.description||'').substring(0,100)+'</span></td><td>'+((a.signals_list||[]).slice(0,3).map(s=>'<span class="signal-tag">'+s+'</span>').join(''))+'</td><td><a href="https://x.com/'+a.username+'" target="_blank" style="color:#3b82f6;text-decoration:none;font-size:12px">View Profile</a></td></tr>'
).join('')+'</table>';
}).catch(e=>console.error(e));
fetch('/api/runs').then(r=>r.json()).then(d=>{
const el=document.getElementById('runs-list');
if(!d.length){el.innerHTML='<div class="empty">No runs yet</div>';return}
el.innerHTML=d.map(r=>'<div class="run-item"><div><div class="run-time">'+r.timestamp+'</div></div><div class="run-stats"><span class="run-stat">Found <b>'+r.accounts_found+'</b></span><span class="run-stat">Projects <b>'+(r.projects_found||0)+'</b></span><span class="run-stat">Qualified <b>'+r.accounts_qualified+'</b></span><span class="run-stat">Notified <b>'+r.accounts_notified+'</b></span><span class="run-stat">Errors <b>'+r.errors+'</b></span><span class="run-stat">'+r.duration_seconds+'s</span></div></div>').join('');
}).catch(e=>console.error(e));
}
loadData();setInterval(loadData,30000);
</script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(DASHBOARD_HTML)


def _db():
    import sqlite3
    from config import settings
    return sqlite3.connect(settings.db_path)


@app.route("/api/stats")
def api_stats():
    db = _db()
    cur = db.cursor()

    cur.execute("SELECT COUNT(*) FROM accounts")
    total = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM accounts WHERE qualifies = 1")
    qualified = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM accounts WHERE notified = 1")
    notified = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM projects")
    projects_count = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM accounts WHERE has_website = 0 AND final_score > 0")
    no_website = cur.fetchone()[0]

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
        "projects_count": projects_count,
        "no_website": no_website,
        "last_run": last_run,
        "last_run_short": last_run_short,
        "last_run_ago": last_run_ago,
    })


@app.route("/api/accounts")
def api_accounts():
    db = _db()
    db.row_factory = sqlite3.Row
    cur = db.cursor()
    cur.execute("SELECT * FROM accounts ORDER BY final_score DESC LIMIT 100")
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


@app.route("/api/projects")
def api_projects():
    db = _db()
    db.row_factory = sqlite3.Row
    cur = db.cursor()
    cur.execute("SELECT * FROM projects ORDER BY score DESC, discovered_at DESC LIMIT 100")
    rows = cur.fetchall()
    db.close()

    result = []
    for row in rows:
        d = dict(row)
        try:
            d["signals_list"] = json.loads(d.get("signals") or "[]")
        except (json.JSONDecodeError, TypeError):
            d["signals_list"] = []
        result.append(d)
    return jsonify(result)


@app.route("/api/no-website")
def api_no_website():
    db = _db()
    db.row_factory = sqlite3.Row
    cur = db.cursor()
    cur.execute(
        """SELECT * FROM accounts
        WHERE has_website = 0 AND final_score > 0
        ORDER BY final_score DESC LIMIT 100"""
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
    db = _db()
    db.row_factory = sqlite3.Row
    cur = db.cursor()
    cur.execute("SELECT id, timestamp, accounts_found, accounts_qualified, accounts_notified, projects_found, errors, duration_seconds FROM runs ORDER BY id DESC LIMIT 20")
    rows = cur.fetchall()
    db.close()
    result = [dict(row) for row in rows]
    return jsonify(result)
