"""
Illumio Rule Scheduler — Flask Web GUI (Dark Theme)
Optional dependency: pip install flask
"""
import json
import re
import threading
import webbrowser
from datetime import datetime
from src.core import truncate, extract_id

# ==========================================
# Flask App Factory
# ==========================================
def create_app(core_system):
    from flask import Flask, request, jsonify, Response

    app = Flask(__name__)
    cfg = core_system['cfg']
    db = core_system['db']
    pce = core_system['pce']
    engine = core_system['engine']

    # ── Serve SPA ──
    @app.route('/')
    def index():
        return Response(_HTML_PAGE, content_type='text/html; charset=utf-8')

    # ── RuleSets ──
    @app.route('/api/rulesets')
    def api_rulesets():
        kw = request.args.get('q', '')
        if kw:
            rs_list = pce.search_rulesets(kw)
        else:
            rs_list = pce.get_all_rulesets(force_refresh=True)
        result = []
        for rs in rs_list:
            href = rs['href']
            st = db.get_schedule_type(rs)
            result.append({
                'href': href,
                'id': extract_id(href),
                'name': rs.get('name',''),
                'enabled': rs.get('enabled', False),
                'sch': '★' if st == 1 else ('●' if st == 2 else ''),
            })
        return jsonify(result)

    @app.route('/api/rulesets/<rs_id>')
    def api_ruleset_detail(rs_id):
        pce.update_label_cache(silent=True)
        rs = pce.get_ruleset_by_id(rs_id)
        if not rs:
            return jsonify({'error': 'Not found'}), 404
        rules = []
        # RuleSet self row
        rs_href = rs['href']
        rules.append({
            'href': rs_href,
            'id': extract_id(rs_href),
            'desc': '▶ [ENTIRE RULESET]',
            'enabled': rs.get('enabled', False),
            'src': 'ALL', 'dst': 'ALL', 'svc': 'ALL',
            'sch': '★' if rs_href in db.get_all() else '',
            'is_ruleset': True,
        })
        for r in rs.get('rules', []):
            href = r['href']
            dest = r.get('destinations', r.get('consumers', []))
            rules.append({
                'href': href,
                'id': extract_id(href),
                'desc': truncate(r.get('description'), 50),
                'enabled': r.get('enabled', False),
                'src': truncate(pce.resolve_actor_str(dest), 30),
                'dst': truncate(pce.resolve_actor_str(r.get('providers', [])), 30),
                'svc': truncate(pce.resolve_service_str(r.get('ingress_services', [])), 25),
                'sch': '★' if href in db.get_all() else '',
                'is_ruleset': False,
            })
        return jsonify({'name': rs['name'], 'href': rs_href, 'rules': rules})

    # ── Schedules ──
    @app.route('/api/schedules')
    def api_schedules():
        data = db.get_all()
        result = []
        for href, c in data.items():
            entry = {
                'href': href,
                'id': extract_id(href),
                'type': 'RS' if c.get('is_ruleset') else 'Rule',
                'rs_name': c.get('detail_rs', 'Unknown'),
                'name': c.get('detail_name', c.get('name', '')),
            }
            if c.get('type') == 'recurring':
                entry['action'] = 'ALLOW' if c.get('action') == 'allow' else 'BLOCK'
                days = c.get('days', [])
                d_str = 'Everyday' if len(days) == 7 else ','.join([d[:3] for d in days])
                entry['timing'] = f"{d_str} {c.get('start','')}-{c.get('end','')}"
            else:
                entry['action'] = 'EXPIRE'
                entry['timing'] = c.get('expire_at', '').replace('T', ' ')
            result.append(entry)
        return jsonify(result)

    @app.route('/api/schedules', methods=['POST'])
    def api_schedule_create():
        d = request.get_json()
        href = d.get('href')
        if not href:
            return jsonify({'error': 'href is required'}), 400

        db_entry = {
            'name': d.get('name', ''),
            'is_ruleset': d.get('is_ruleset', False),
            'detail_rs': d.get('detail_rs', ''),
            'detail_src': d.get('detail_src', 'All'),
            'detail_dst': d.get('detail_dst', 'All'),
            'detail_svc': d.get('detail_svc', 'All'),
            'detail_name': d.get('name', ''),
        }

        try:
            if d.get('schedule_type') == 'recurring':
                days = [x.strip() for x in d.get('days', '').split(',')]
                datetime.strptime(d.get('start', ''), '%H:%M')
                datetime.strptime(d.get('end', ''), '%H:%M')
                db_entry.update({
                    'type': 'recurring',
                    'action': d.get('action', 'allow'),
                    'days': days,
                    'start': d.get('start'),
                    'end': d.get('end'),
                })
                note_msg = f"[📅 排程: {d.get('action','allow')} {d.get('start')}-{d.get('end')}]"
            else:
                ex = d.get('expire_at', '').replace(' ', 'T')
                datetime.fromisoformat(ex)
                db_entry.update({'type': 'one_time', 'action': 'allow', 'expire_at': ex})
                note_msg = f"[⏳ 有效期限至 {ex} 止]"
        except ValueError as e:
            return jsonify({'error': f'Invalid format: {e}'}), 400

        db.put(href, db_entry)
        pce.update_rule_note(href, note_msg)
        return jsonify({'ok': True, 'message': 'Schedule saved and provisioned.'})

    @app.route('/api/schedules/<path:href>', methods=['DELETE'])
    def api_schedule_delete(href):
        try:
            pce.update_rule_note(href, '', remove=True)
        except Exception:
            pass
        db.delete(href)
        return jsonify({'ok': True})

    # ── Check ──
    @app.route('/api/check', methods=['POST'])
    def api_check():
        logs = engine.check(silent=True)
        ansi_re = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        clean_logs = [ansi_re.sub('', l) for l in logs]
        return jsonify({'logs': clean_logs})

    # ── Config ──
    @app.route('/api/config', methods=['GET'])
    def api_config_get():
        return jsonify({
            'pce_url': cfg.config.get('pce_url', ''),
            'org_id': cfg.config.get('org_id', ''),
            'api_key': cfg.config.get('api_key', ''),
            'api_secret': '••••••••' if cfg.config.get('api_secret') else '',
        })

    @app.route('/api/config', methods=['POST'])
    def api_config_save():
        d = request.get_json()
        if not all([d.get('pce_url'), d.get('org_id'), d.get('api_key'), d.get('api_secret')]):
            return jsonify({'error': 'All fields required'}), 400
        cfg.save(d['pce_url'], d['org_id'], d['api_key'], d['api_secret'])
        pce.update_label_cache(silent=True)
        return jsonify({'ok': True, 'message': 'Configuration saved!'})

    # ── Stop ──
    @app.route('/api/stop', methods=['POST'])
    def api_stop():
        func = request.environ.get('werkzeug.server.shutdown')
        if func:
            func()
        else:
            import os, signal
            os.kill(os.getpid(), signal.SIGINT)
        return jsonify({'ok': True, 'message': 'Server shutting down...'})

    return app


# ==========================================
# Entry Point
# ==========================================
def launch_gui(core_system, port=5000):
    host = '127.0.0.1'
    app = create_app(core_system)
    url = f'http://{host}:{port}'
    print(f"[WebGUI] Starting at {url}")
    print(f"[WebGUI] Press Ctrl+C to stop")
    threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    app.run(host=host, port=port, debug=False, use_reloader=False)


# ==========================================
# Embedded SPA (Single-Page Application)
# ==========================================
_HTML_PAGE = r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Illumio Rule Scheduler</title>
<style>
:root {
  --bg-dark: #0f1117;
  --bg-panel: #161b22;
  --bg-card: #1c2333;
  --bg-input: #21262d;
  --fg: #e6edf3;
  --fg-dim: #7d8590;
  --accent: #58a6ff;
  --accent2: #00d2ff;
  --green: #3fb950;
  --red: #f85149;
  --gold: #d29922;
  --border: #30363d;
  --radius: 8px;
}
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
  background: var(--bg-dark);
  color: var(--fg);
  line-height: 1.5;
  min-height: 100vh;
}

/* ── Header ── */
.header {
  background: var(--bg-panel);
  border-bottom: 1px solid var(--border);
  padding: 12px 24px;
  display: flex;
  align-items: center;
  gap: 16px;
}
.header h1 { font-size: 18px; color: var(--accent2); font-weight: 700; }
.header .version { font-size: 12px; color: var(--fg-dim); }
.header .stop-btn {
  margin-left: auto;
  background: var(--red);
  color: #fff;
  border: none;
  padding: 6px 14px;
  border-radius: var(--radius);
  cursor: pointer;
  font-size: 12px;
  font-weight: 600;
}
.header .stop-btn:hover { opacity: 0.85; }

/* ── Tabs ── */
.tab-bar {
  display: flex;
  background: var(--bg-panel);
  border-bottom: 1px solid var(--border);
  padding: 0 24px;
  gap: 0;
}
.tab-btn {
  background: none;
  border: none;
  color: var(--fg-dim);
  padding: 10px 20px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  border-bottom: 2px solid transparent;
  transition: all 0.2s;
}
.tab-btn:hover { color: var(--fg); }
.tab-btn.active { color: var(--accent); border-bottom-color: var(--accent); }

/* ── Content ── */
.content { padding: 20px 24px; max-width: 1400px; margin: 0 auto; }
.tab-panel { display: none; }
.tab-panel.active { display: block; }

/* ── Toolbar ── */
.toolbar { display: flex; gap: 8px; margin-bottom: 16px; align-items: center; flex-wrap: wrap; }
.toolbar input[type="text"] {
  background: var(--bg-input);
  border: 1px solid var(--border);
  color: var(--fg);
  padding: 7px 12px;
  border-radius: var(--radius);
  font-size: 13px;
  width: 280px;
}
.toolbar input:focus { outline: none; border-color: var(--accent); }

/* ── Buttons ── */
.btn {
  background: var(--bg-card);
  border: 1px solid var(--border);
  color: var(--fg);
  padding: 7px 14px;
  border-radius: var(--radius);
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  transition: all 0.15s;
}
.btn:hover { background: var(--bg-input); border-color: var(--fg-dim); }
.btn-accent {
  background: #1f6feb;
  border-color: #1f6feb;
  color: #fff;
}
.btn-accent:hover { background: #388bfd; border-color: #388bfd; }
.btn-danger { background: var(--red); border-color: var(--red); color: #fff; }
.btn-danger:hover { opacity: 0.85; }

/* ── Tables ── */
table {
  width: 100%;
  border-collapse: collapse;
  background: var(--bg-panel);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  overflow: hidden;
  font-size: 13px;
}
th {
  background: var(--bg-card);
  color: var(--accent);
  padding: 8px 12px;
  text-align: left;
  font-weight: 600;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  white-space: nowrap;
}
td {
  padding: 7px 12px;
  border-top: 1px solid var(--border);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 260px;
}
tr { cursor: pointer; transition: background 0.1s; }
tr:hover { background: var(--bg-card); }
tr.selected { background: #1c3a5e !important; }
.badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 600;
}
.badge-on { background: rgba(63,185,80,0.15); color: var(--green); }
.badge-off { background: rgba(248,81,73,0.15); color: var(--red); }
.badge-sch { color: var(--gold); font-size: 14px; }

/* ── Split Pane ── */
.split-pane { display: grid; grid-template-columns: 340px 1fr; gap: 16px; }
.pane-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.pane-header h3 { font-size: 13px; color: var(--fg-dim); font-weight: 500; }
.table-wrap { overflow-y: auto; max-height: 520px; border-radius: var(--radius); }

/* ── Log Panel ── */
.log-panel {
  background: #0d1117;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 16px;
  font-family: 'Cascadia Code', 'Consolas', monospace;
  font-size: 13px;
  color: #c9d1d9;
  min-height: 400px;
  max-height: 520px;
  overflow-y: auto;
  white-space: pre-wrap;
  line-height: 1.7;
}

/* ── Form (Settings) ── */
.form-card {
  background: var(--bg-panel);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 24px;
  max-width: 560px;
}
.form-card h3 { color: var(--accent); margin-bottom: 20px; font-size: 16px; }
.form-row {
  display: grid;
  grid-template-columns: 120px 1fr;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}
.form-row label { font-size: 13px; color: var(--fg-dim); }
.form-row input {
  background: var(--bg-input);
  border: 1px solid var(--border);
  color: var(--fg);
  padding: 8px 12px;
  border-radius: var(--radius);
  font-size: 13px;
}
.form-row input:focus { outline: none; border-color: var(--accent); }

/* ── Modal ── */
.modal-overlay {
  position: fixed; top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex; justify-content: center; align-items: center;
  z-index: 1000;
}
.modal {
  background: var(--bg-panel);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 24px;
  width: 480px;
  max-width: 90vw;
}
.modal h3 { color: var(--accent); margin-bottom: 16px; }
.modal .form-row { grid-template-columns: 140px 1fr; }
.modal-actions { display: flex; gap: 8px; margin-top: 20px; justify-content: flex-end; }

/* ── Toast ── */
.toast-container { position: fixed; top: 16px; right: 16px; z-index: 2000; }
.toast {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 12px 20px;
  margin-bottom: 8px;
  font-size: 13px;
  animation: slideIn 0.3s ease;
  display: flex;
  align-items: center;
  gap: 8px;
}
.toast.success { border-left: 3px solid var(--green); }
.toast.error { border-left: 3px solid var(--red); }
@keyframes slideIn { from { opacity: 0; transform: translateX(40px); } to { opacity: 1; transform: translateX(0); } }

/* ── Responsive ── */
@media (max-width: 800px) {
  .split-pane { grid-template-columns: 1fr; }
  .toolbar input[type="text"] { width: 100%; }
}

/* ── Radio Group ── */
.radio-group { display: flex; gap: 16px; margin-bottom: 14px; }
.radio-group label {
  display: flex; align-items: center; gap: 6px;
  cursor: pointer; font-size: 13px; color: var(--fg);
}
.radio-group input[type="radio"] { accent-color: var(--accent); }
</style>
</head>
<body>

<!-- Header -->
<div class="header">
  <h1>🕒 Illumio Rule Scheduler</h1>
  <span class="version">v4.2 · Web GUI</span>
  <button class="stop-btn" onclick="stopServer()">⏹ Stop Server</button>
</div>

<!-- Tabs -->
<div class="tab-bar">
  <button class="tab-btn active" onclick="showTab('browse')">📋 Browse & Add</button>
  <button class="tab-btn" onclick="showTab('schedules')">⏱ Schedules</button>
  <button class="tab-btn" onclick="showTab('logs')">📜 Logs & Check</button>
  <button class="tab-btn" onclick="showTab('settings')">⚙ Settings</button>
</div>

<div style="padding:6px 20px;font-size:12px;color:var(--fg-dim);background:var(--bg-panel);border-bottom:1px solid var(--border)">
  Hint: <span style="color:#f0a500">★</span> = RuleSet scheduled &nbsp;&nbsp; <span style="color:#58a6ff">●</span> = Child rule only
</div>

<div class="content">

<!-- ━━━ Browse Tab ━━━ -->
<div id="tab-browse" class="tab-panel active">
  <div class="toolbar">
    <input type="text" id="search-input" placeholder="Search RuleSets..." onkeydown="if(event.key==='Enter')searchRS()">
    <button class="btn" onclick="searchRS()">🔍 Search</button>
    <button class="btn" onclick="loadAllRS()">↻ Refresh All</button>
  </div>
  <div class="split-pane">
    <!-- Left: RuleSets -->
    <div>
      <div class="pane-header"><h3>RuleSets</h3><span id="rs-count" style="color:var(--fg-dim);font-size:12px"></span></div>
      <div class="table-wrap">
        <table><thead><tr><th style="width:50px">⚡</th><th>Name</th><th style="width:60px">ID</th><th style="width:30px">📅</th></tr></thead>
        <tbody id="rs-table"></tbody></table>
      </div>
    </div>
    <!-- Right: Rules -->
    <div>
      <div class="pane-header">
        <h3 id="rules-title">← Select a RuleSet</h3>
        <button class="btn btn-accent" onclick="openScheduleModal()">＋ Schedule Selected</button>
      </div>
      <div class="table-wrap">
        <table><thead><tr><th style="width:50px">⚡</th><th style="width:60px">ID</th><th>Description</th><th>Source</th><th>Dest</th><th>Service</th><th style="width:30px">📅</th></tr></thead>
        <tbody id="rules-table"></tbody></table>
      </div>
    </div>
  </div>
</div>

<!-- ━━━ Schedules Tab ━━━ -->
<div id="tab-schedules" class="tab-panel">
  <div class="toolbar">
    <button class="btn" onclick="loadSchedules()">↻ Refresh</button>
    <button class="btn btn-danger" onclick="deleteSelectedSchedule()">🗑 Delete Selected</button>
  </div>
  <div class="table-wrap">
    <table><thead><tr><th style="width:50px">Type</th><th>RuleSet</th><th>Description</th><th style="width:70px">Action</th><th>Timing / Expires</th><th style="width:60px">ID</th></tr></thead>
    <tbody id="sch-table"></tbody></table>
  </div>
</div>

<!-- ━━━ Logs Tab ━━━ -->
<div id="tab-logs" class="tab-panel">
  <div class="toolbar">
    <button class="btn btn-accent" onclick="runCheck()">▶ Run Manual Check</button>
    <button class="btn" onclick="document.getElementById('log-panel').textContent=''">Clear</button>
  </div>
  <div class="log-panel" id="log-panel">Ready. Click "Run Manual Check" to start.\n</div>
</div>

<!-- ━━━ Settings Tab ━━━ -->
<div id="tab-settings" class="tab-panel">
  <div class="form-card">
    <h3>⚙ PCE API Configuration</h3>
    <div class="form-row"><label>PCE URL</label><input id="cfg-url" type="text" placeholder="https://pce.example.com:8443"></div>
    <div class="form-row"><label>Org ID</label><input id="cfg-org" type="text" placeholder="1"></div>
    <div class="form-row"><label>API Key</label><input id="cfg-key" type="text" placeholder="api_..."></div>
    <div class="form-row"><label>API Secret</label><input id="cfg-sec" type="password" placeholder="••••••••"></div>
    <div style="margin-top:16px"><button class="btn btn-accent" onclick="saveConfig()">💾 Save Configuration</button></div>
  </div>
</div>

</div><!-- /content -->

<!-- Toast Container -->
<div class="toast-container" id="toast-container"></div>

<!-- Schedule Modal (hidden) -->
<div class="modal-overlay" id="schedule-modal" style="display:none">
<div class="modal">
  <h3 id="modal-title">📅 Schedule</h3>
  <div id="modal-target-info"></div>
  <div class="radio-group">
    <label><input type="radio" name="sch-type" value="recurring" checked onchange="toggleSchType()"> Recurring (Weekly)</label>
    <label><input type="radio" name="sch-type" value="one_time" onchange="toggleSchType()"> One-Time Expiration</label>
  </div>
  <div id="recurring-fields">
    <div class="form-row"><label>Action</label><select id="sch-action" style="background:var(--bg-input);border:1px solid var(--border);color:var(--fg);padding:8px;border-radius:var(--radius)"><option value="allow">Allow (enable in window)</option><option value="block">Block (disable in window)</option></select></div>
    <div class="form-row"><label>Days</label><input id="sch-days" type="text" value="Monday,Tuesday,Wednesday,Thursday,Friday"></div>
    <div class="form-row"><label>Start (HH:MM)</label><input id="sch-start" type="text" value="08:00"></div>
    <div class="form-row"><label>End (HH:MM)</label><input id="sch-end" type="text" value="18:00"></div>
  </div>
  <div id="onetime-fields" style="display:none">
    <div class="form-row"><label>Expire At</label><input id="sch-expire" type="text" value=""></div>
    <div style="font-size:11px;color:var(--fg-dim);margin-top:4px">Format: YYYY-MM-DD HH:MM  (auto-disable & remove)</div>
  </div>
  <div class="modal-actions">
    <button class="btn" onclick="closeModal()">Cancel</button>
    <button class="btn btn-accent" onclick="saveSchedule()">💾 Save Schedule</button>
  </div>
</div>
</div>

<script>
// ━━━ State ━━━
let selectedRS = null;     // {href, name}
let selectedRule = null;   // {href, name, is_ruleset, detail_rs, src, dst, svc}
let selectedSchHref = null;

// ━━━ Toast ━━━
function toast(msg, type='success') {
  const c = document.getElementById('toast-container');
  const t = document.createElement('div');
  t.className = 'toast ' + type;
  t.textContent = (type==='success' ? '✓ ' : '✗ ') + msg;
  c.appendChild(t);
  setTimeout(() => t.remove(), 3500);
}

// ━━━ Tabs ━━━
function showTab(name) {
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('tab-' + name).classList.add('active');
  const btns = document.querySelectorAll('.tab-btn');
  const idx = {browse:0, schedules:1, logs:2, settings:3}[name];
  btns[idx].classList.add('active');
  if (name === 'schedules') loadSchedules();
  if (name === 'settings') loadConfig();
}

// ━━━ RuleSets ━━━
async function loadAllRS() {
  try {
    const res = await fetch('/api/rulesets');
    const data = await res.json();
    renderRS(data);
  } catch(e) { toast('Failed to load RuleSets: ' + e.message, 'error'); }
}
async function searchRS() {
  const q = document.getElementById('search-input').value;
  try {
    const res = await fetch('/api/rulesets?q=' + encodeURIComponent(q));
    const data = await res.json();
    renderRS(data);
  } catch(e) { toast('Search failed: ' + e.message, 'error'); }
}
function renderRS(list) {
  const tb = document.getElementById('rs-table');
  tb.innerHTML = '';
  document.getElementById('rs-count').textContent = list.length + ' items';
  list.forEach(rs => {
    const tr = document.createElement('tr');
    tr.innerHTML = `<td><span class="badge ${rs.enabled?'badge-on':'badge-off'}">${rs.enabled?'ON':'OFF'}</span></td>
      <td title="${rs.name}">${rs.name}</td>
      <td>${rs.id}</td>
      <td class="badge-sch">${rs.sch}</td>`;
    tr.onclick = () => selectRS(rs, tr);
    tb.appendChild(tr);
  });
}
async function selectRS(rs, tr) {
  selectedRS = rs;
  selectedRule = null;  // Reset rule selection when switching RS
  document.querySelectorAll('#rs-table tr').forEach(r => r.classList.remove('selected'));
  tr.classList.add('selected');
  try {
    const res = await fetch('/api/rulesets/' + rs.id);
    const data = await res.json();
    document.getElementById('rules-title').textContent = `${data.name} (${data.rules.length} items)`;
    renderRules(data.rules, rs.name);
  } catch(e) { toast('Failed to load rules: ' + e.message, 'error'); }
}
function renderRules(rules, rsName) {
  const tb = document.getElementById('rules-table');
  tb.innerHTML = '';
  rules.forEach((r, idx) => {
    const tr = document.createElement('tr');
    tr.innerHTML = `<td><span class="badge ${r.enabled?'badge-on':'badge-off'}">${r.enabled?'ON':'OFF'}</span></td>
      <td>${r.id}</td>
      <td title="${r.desc}">${r.desc}</td>
      <td title="${r.src}">${r.src}</td>
      <td title="${r.dst}">${r.dst}</td>
      <td title="${r.svc}">${r.svc}</td>
      <td class="badge-sch">${r.sch}</td>`;
    tr.onclick = () => {
      document.querySelectorAll('#rules-table tr').forEach(x => x.classList.remove('selected'));
      tr.classList.add('selected');
      selectedRule = { href: r.href, name: r.desc, is_ruleset: r.is_ruleset, detail_rs: rsName, src: r.src, dst: r.dst, svc: r.svc };
    };
    tb.appendChild(tr);
    // Auto-select first row (ENTIRE RULESET)
    if (idx === 0) {
      tr.classList.add('selected');
      selectedRule = { href: r.href, name: r.desc, is_ruleset: r.is_ruleset, detail_rs: rsName, src: r.src, dst: r.dst, svc: r.svc };
    }
  });
}

// ━━━ Schedule Modal ━━━
function openScheduleModal() {
  if (!selectedRS || !selectedRule) { toast('Please select a RuleSet on the left and a rule on the right first.', 'error'); return; }
  const r = selectedRule;
  const typeLabel = r.is_ruleset ? '📦 RuleSet' : '📄 Rule';
  document.getElementById('modal-title').textContent = '📅 New Schedule';
  document.getElementById('modal-target-info').innerHTML = `
    <div style="background:var(--bg-card);border:1px solid var(--border);border-radius:var(--radius);padding:12px;margin-bottom:14px;font-size:13px">
      <div style="margin-bottom:6px"><span style="color:var(--fg-dim)">Type:</span> <strong style="color:var(--accent)">${typeLabel}</strong></div>
      <div style="margin-bottom:4px"><span style="color:var(--fg-dim)">RuleSet:</span> ${r.detail_rs}</div>
      <div style="margin-bottom:4px"><span style="color:var(--fg-dim)">Target:</span> <strong>${r.name || 'ID ' + r.href.split('/').pop()}</strong></div>
      <div style="display:flex;gap:16px;margin-top:4px;color:var(--fg-dim);font-size:12px">
        <span>Src: ${r.src}</span><span>Dst: ${r.dst}</span><span>Svc: ${r.svc}</span>
      </div>
    </div>`;
  const now = new Date();
  const pad = n => String(n).padStart(2, '0');
  document.getElementById('sch-expire').value = `${now.getFullYear()}-${pad(now.getMonth()+1)}-${pad(now.getDate())} 23:59`;
  document.getElementById('schedule-modal').style.display = 'flex';
}
function closeModal() { document.getElementById('schedule-modal').style.display = 'none'; }
function toggleSchType() {
  const v = document.querySelector('input[name="sch-type"]:checked').value;
  document.getElementById('recurring-fields').style.display = v === 'recurring' ? 'block' : 'none';
  document.getElementById('onetime-fields').style.display = v === 'one_time' ? 'block' : 'none';
}
async function saveSchedule() {
  const schType = document.querySelector('input[name="sch-type"]:checked').value;
  const payload = {
    href: selectedRule.href,
    name: selectedRule.name,
    is_ruleset: selectedRule.is_ruleset,
    detail_rs: selectedRule.detail_rs,
    detail_src: selectedRule.src,
    detail_dst: selectedRule.dst,
    detail_svc: selectedRule.svc,
    schedule_type: schType,
  };
  if (schType === 'recurring') {
    payload.action = document.getElementById('sch-action').value;
    payload.days = document.getElementById('sch-days').value;
    payload.start = document.getElementById('sch-start').value;
    payload.end = document.getElementById('sch-end').value;
  } else {
    payload.expire_at = document.getElementById('sch-expire').value;
  }
  try {
    const res = await fetch('/api/schedules', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(payload) });
    const data = await res.json();
    if (data.ok) { toast(data.message); closeModal(); if (selectedRS) selectRS(selectedRS, document.querySelector('#rs-table tr.selected')); }
    else toast(data.error || 'Failed', 'error');
  } catch(e) { toast('Error: ' + e.message, 'error'); }
}

// ━━━ Schedules List ━━━
async function loadSchedules() {
  try {
    const res = await fetch('/api/schedules');
    const data = await res.json();
    const tb = document.getElementById('sch-table');
    tb.innerHTML = '';
    data.forEach(s => {
      const tr = document.createElement('tr');
      tr.innerHTML = `<td>${s.type}</td><td title="${s.rs_name}">${s.rs_name}</td><td title="${s.name}">${s.name}</td>
        <td><span class="badge ${s.action==='ALLOW'?'badge-on':(s.action==='BLOCK'?'badge-off':'')}">${s.action}</span></td>
        <td>${s.timing}</td><td>${s.id}</td>`;
      tr.onclick = () => {
        document.querySelectorAll('#sch-table tr').forEach(x => x.classList.remove('selected'));
        tr.classList.add('selected');
        selectedSchHref = s.href;
      };
      tb.appendChild(tr);
    });
  } catch(e) { toast('Failed: ' + e.message, 'error'); }
}
async function deleteSelectedSchedule() {
  if (!selectedSchHref) { toast('Select a schedule first.', 'error'); return; }
  if (!confirm('Delete this schedule?')) return;
  try {
    await fetch('/api/schedules/' + encodeURIComponent(selectedSchHref), {method:'DELETE'});
    toast('Schedule deleted.');
    selectedSchHref = null;
    loadSchedules();
  } catch(e) { toast('Error: ' + e.message, 'error'); }
}

// ━━━ Logs & Check ━━━
async function runCheck() {
  const panel = document.getElementById('log-panel');
  const now = new Date().toLocaleTimeString();
  panel.textContent += `[${now}] Starting policy check...\n`;
  try {
    const res = await fetch('/api/check', {method:'POST'});
    const data = await res.json();
    data.logs.forEach(l => panel.textContent += l + '\n');
    panel.textContent += '✔ Check complete.\n\n';
    panel.scrollTop = panel.scrollHeight;
  } catch(e) { panel.textContent += 'Error: ' + e.message + '\n'; }
}

// ━━━ Settings ━━━
async function loadConfig() {
  try {
    const res = await fetch('/api/config');
    const data = await res.json();
    document.getElementById('cfg-url').value = data.pce_url || '';
    document.getElementById('cfg-org').value = data.org_id || '';
    document.getElementById('cfg-key').value = data.api_key || '';
    document.getElementById('cfg-sec').value = '';
    document.getElementById('cfg-sec').placeholder = data.api_secret || '••••••••';
  } catch(e) { toast('Failed to load config', 'error'); }
}
async function saveConfig() {
  const payload = {
    pce_url: document.getElementById('cfg-url').value,
    org_id: document.getElementById('cfg-org').value,
    api_key: document.getElementById('cfg-key').value,
    api_secret: document.getElementById('cfg-sec').value,
  };
  if (!payload.pce_url || !payload.org_id || !payload.api_key || !payload.api_secret) {
    toast('All fields are required.', 'error'); return;
  }
  try {
    const res = await fetch('/api/config', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload) });
    const data = await res.json();
    if (data.ok) toast(data.message);
    else toast(data.error, 'error');
  } catch(e) { toast('Error: ' + e.message, 'error'); }
}

// ━━━ Stop Server ━━━
async function stopServer() {
  if (!confirm('Stop the Web GUI server?')) return;
  try { await fetch('/api/stop', {method:'POST'}); } catch(e) {}
  document.body.innerHTML = '<div style="display:flex;justify-content:center;align-items:center;height:100vh;flex-direction:column;gap:12px"><h2 style="color:var(--accent)">Server Stopped</h2><p style="color:var(--fg-dim)">You can close this tab.</p></div>';
}

// ━━━ Init ━━━
document.addEventListener('DOMContentLoaded', () => { loadAllRS(); });
</script>
</body>
</html>
'''
