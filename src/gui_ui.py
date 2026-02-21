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
import src.i18n as i18n

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

    # ── RuleSets (with pagination) ──
    @app.route('/api/rulesets')
    def api_rulesets():
        kw = request.args.get('q', '')
        page = int(request.args.get('page', 1))
        size = int(request.args.get('size', 50))
        if kw:
            rs_list = pce.search_rulesets(kw)
        else:
            rs_list = pce.get_all_rulesets(force_refresh=True)
        total = len(rs_list)
        start = (page - 1) * size
        end = start + size
        paginated = rs_list[start:end]
        result = []
        for rs in paginated:
            href = rs['href']
            st = db.get_schedule_type(rs)
            # update_type: null=provisioned, "create"=new draft, "update"=modified draft
            ut = rs.get('update_type')
            prov = 'draft' if ut else 'active'
            result.append({
                'href': href,
                'id': extract_id(href),
                'name': rs.get('name',''),
                'enabled': rs.get('enabled', False),
                'sch': 'star' if st == 1 else ('dot' if st == 2 else ''),
                'prov': prov,
            })
        return jsonify({'items': result, 'total': total, 'page': page, 'size': size, 'pages': (total + size - 1) // size})

    @app.route('/api/rulesets/<rs_id>')
    def api_ruleset_detail(rs_id):
        pce.update_label_cache(silent=True)
        rs = pce.get_ruleset_by_id(rs_id)
        if not rs:
            return jsonify({'error': 'Not found'}), 404
        rules = []
        rs_href = rs['href']
        rs_ut = rs.get('update_type')
        rs_prov = 'draft' if rs_ut else 'active'
        # RuleSet self row
        rules.append({
            'href': rs_href,
            'id': extract_id(rs_href),
            'desc': '▶ [ENTIRE RULESET]',
            'enabled': rs.get('enabled', False),
            'src': 'ALL', 'dst': 'ALL', 'svc': 'ALL',
            'sch': 'star' if rs_href in db.get_all() else '',
            'is_ruleset': True,
            'prov': rs_prov,
        })
        for r in rs.get('rules', []):
            href = r['href']
            dest = r.get('destinations', r.get('consumers', []))
            r_ut = r.get('update_type', rs_ut)  # rules inherit RS provision if no own field
            r_prov = 'draft' if r_ut else 'active'
            rules.append({
                'href': href,
                'id': extract_id(href),
                'desc': truncate(r.get('description'), 50),
                'enabled': r.get('enabled', False),
                'src': truncate(pce.resolve_actor_str(dest), 30),
                'dst': truncate(pce.resolve_actor_str(r.get('providers', [])), 30),
                'svc': truncate(pce.resolve_service_str(r.get('ingress_services', [])), 25),
                'sch': 'star' if href in db.get_all() else '',
                'is_ruleset': False,
                'prov': r_prov,
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
                from datetime import datetime
                t1 = datetime.strptime(d.get('start', ''), '%H:%M')
                t2 = datetime.strptime(d.get('end', ''), '%H:%M')
                if t1 >= t2:
                    raise ValueError(i18n.t('sch_time_invalid'))
                
                db_entry.update({
                    'type': 'recurring',
                    'action': d.get('action', 'allow'),
                    'days': days,
                    'start': d.get('start'),
                    'end': d.get('end'),
                })
                act_str = i18n.t('action_enable_in_window') if d.get('action') == 'allow' else i18n.t('action_disable_in_window')
                days_str = i18n.t('action_everyday') if len(days) == 7 else ','.join([dx[:3] for dx in days])
                note_msg = f"[📅 {i18n.t('sch_tag_recurring')}: {days_str} {db_entry['start']}-{db_entry['end']} {act_str}]"
            else:
                from datetime import datetime
                ex = d.get('expire_at', '').replace(' ', 'T')
                if len(ex) == 16: ex += ":00Z"
                datetime.fromisoformat(ex.replace("Z", "+00:00"))
                db_entry.update({'type': 'one_time', 'action': 'allow', 'expire_at': ex})
                note_msg = f"[⏳ {i18n.t('sch_tag_expire')}: {d.get('expire_at')}]"
        except ValueError as e:
            return jsonify({'error': str(e)}), 400

        db.put(href, db_entry)
        pce.update_rule_note(href, note_msg)
        return jsonify({'ok': True, 'message': i18n.t('sch_updated')})

    @app.route('/api/schedules/<path:href>', methods=['GET'])
    def api_schedule_get(href):
        href = f"/{href}"
        data = db.get(href)
        if not data:
            return jsonify({'error': 'Not found'}), 404
        return jsonify(data)

    @app.route('/api/schedules/delete', methods=['POST'])
    def api_schedule_delete():
        d = request.get_json()
        hrefs = d.get('hrefs', [])
        if not hrefs:
            return jsonify({'error': 'No hrefs provided'}), 400
        count = 0
        for href in hrefs:
            try:
                pce.update_rule_note(href, '', remove=True)
            except Exception:
                pass
            db.delete(href)
            count += 1
        return jsonify({'ok': True, 'count': count})

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
            'lang': i18n.get_lang(),
        })

    @app.route('/api/config', methods=['POST'])
    def api_config_save():
        d = request.get_json()
        if not all([d.get('pce_url'), d.get('org_id'), d.get('api_key')]):
            return jsonify({'error': 'URL, Org ID and API Key are required'}), 400
        
        api_sec = d.get('api_secret')
        if not api_sec:
            api_sec = cfg.config.get('api_secret')
            if not api_sec:
                return jsonify({'error': 'API Secret is required for first-time setup'}), 400
                
        cfg.save(d['pce_url'], d['org_id'], d['api_key'], api_sec)
        if 'lang' in d:
            i18n.set_lang(d['lang'])
            cfg.save_lang(d['lang'])
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
    host = '0.0.0.0'
    app = create_app(core_system)
    url = f'http://{host}:{port}'
    browser_url = f'http://localhost:{port}'
    print(f"[WebGUI] Starting at {url}")
    print(f"[WebGUI] Press Ctrl+C to stop")
    threading.Timer(1.0, lambda: webbrowser.open(browser_url)).start()
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
.split-pane { display: flex; flex-direction: row; height: calc(100vh - 120px); }
.left-pane { width: 340px; min-width: 200px; max-width: 600px; display: flex; flex-direction: column; }
.resizer { width: 8px; cursor: col-resize; background: transparent; transition: background 0.2s; margin-right: 8px; }
.resizer:hover, .resizer.resizing { background: var(--accent); opacity: 0.5; }
.right-pane { flex: 1; min-width: 300px; display: flex; flex-direction: column; overflow: hidden; }
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

/* ── Schedule & Provision badges ── */
.sch-star { color: #f0a500; font-size: 14px; }
.sch-dot { color: #58a6ff; font-size: 14px; }
.badge-prov { font-size: 10px; padding: 2px 6px; border-radius: 4px; font-weight: 600; }
.prov-active { background: #16a34a22; color: #4ade80; border: 1px solid #16a34a44; }
.prov-draft { background: #f59e0b22; color: #fbbf24; border: 1px solid #f59e0b44; }

/* ── Pagination ── */
.pagination { display: flex; align-items: center; gap: 6px; padding: 8px 0; font-size: 12px; color: var(--fg-dim); }
.pagination button { background: var(--bg-card); border: 1px solid var(--border); color: var(--fg); padding: 4px 10px; border-radius: 4px; cursor: pointer; font-size: 12px; }
.pagination button:hover { border-color: var(--accent); }
.pagination button:disabled { opacity: 0.3; cursor: default; }
.pagination .page-info { margin: 0 4px; }
</style>
</head>
<body>

<!-- Header -->
<div class="header">
  <h1>🕒 Illumio Rule Scheduler</h1>
  <span class="version">Web GUI</span>
  <button class="stop-btn" onclick="stopServer()">⏹ Stop WebGUI</button>
</div>

<!-- Tabs -->
<div class="tab-bar">
  <button class="tab-btn active" onclick="showTab('browse')">📋 Browse & Add</button>
  <button class="tab-btn" onclick="showTab('schedules')">⏱ Schedules</button>
  <button class="tab-btn" onclick="showTab('logs')">📜 Logs & Check</button>
  <button class="tab-btn" onclick="showTab('settings')">⚙ Settings</button>
</div>

<div style="padding:6px 20px;font-size:12px;color:var(--fg-dim);background:var(--bg-panel);border-bottom:1px solid var(--border)">
  Hint: <span style="color:var(--gold)">★</span> = RuleSet scheduled &nbsp;&nbsp; <span style="color:var(--accent)">●</span> = Child rule only
</div>

<div class="content">

<!-- Tab: Browse & Add -->
<div id="tab-browse" class="tab-panel active">
  
  <div class="split-pane">
    <div class="left-pane" id="left-pane">
      <div style="display:flex;gap:8px;margin-bottom:12px">
        <input type="text" id="rs-search-input" placeholder="Search RuleSets..." onkeypress="if(event.key==='Enter') searchRS()" style="flex:1" />
        <button class="btn" style="padding:0 12px;display:flex;align-items:center;gap:6px" onclick="searchRS()">🔍 Search</button>
        <button class="btn" style="padding:0 12px" onclick="clearRS()">↺ Refresh All</button>
      </div>
      
      <div class="pane-header"><span>RuleSets</span><span id="rs-count" style="color:var(--fg-dim)">0 items</span></div>
      <div class="table-wrap" style="flex:1">
        <table>
          <thead><tr><th style="width:10%">⚡</th><th style="width:50%">NAME</th><th style="width:15%">ID</th><th style="width:15%">PROV</th><th style="width:10%">📅</th></tr></thead>
          <tbody id="rs-table"></tbody>
        </table>
      </div>
      <div class="pagination" id="rs-pagination" style="margin-top:12px"></div>
    </div>
    
    <div class="resizer" id="resizer"></div>
    
    <div class="right-pane">
      <div class="pane-header"><span id="rules-title">Select a RuleSet...</span><button class="btn btn-accent" onclick="openScheduleModal()">+ Schedule Selected</button></div>
      <div class="table-wrap" style="flex:1">
        <table>
          <thead><tr><th>⚡</th><th>ID</th><th>DESC</th><th>SRC</th><th>DEST</th><th>SERVICE</th><th>PROV</th><th>📅</th></tr></thead>
          <tbody id="rules-table"><tr><td colspan="8" style="text-align:center;color:var(--fg-dim)">Empty</td></tr></tbody>
        </table>
      </div>
    </div>
  </div>
</div>

<!-- ━━━ Schedules Tab ━━━ -->
<div id="tab-schedules" class="tab-panel">
  <div class="toolbar">
    <button class="btn" onclick="loadSchedules()">↻ Refresh</button>
    <button class="btn btn-danger" onclick="deleteSelectedSchedules()">🗑 Delete Selected</button>
  </div>
  <div class="table-wrap">
    <table><thead><tr><th style="width:36px"><input type="checkbox" id="sch-select-all" onchange="toggleSchSelectAll(this)"></th><th style="width:50px">Type</th><th>RuleSet</th><th>Description</th><th style="width:70px">Action</th><th>Timing / Expires</th><th style="width:60px">ID</th></tr></thead>
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
    <h3>⚙ PCE API Configuration <span style="font-size:12px;color:var(--fg-dim);float:right">v1.0.0</span></h3>
    <div class="form-row"><label>PCE URL</label><input id="cfg-url" type="text" placeholder="https://pce.example.com:8443"></div>
    <div class="form-row"><label>Org ID</label><input id="cfg-org" type="text" placeholder="1"></div>
    <div class="form-row"><label>API Key</label><input id="cfg-key" type="text" placeholder="api_..."></div>
    <div class="form-row"><label>API Secret</label><input id="cfg-sec" type="password" placeholder="••••••••"></div>
    <div class="form-row">
      <label>Language</label>
      <select id="cfg-lang" style="background:var(--bg-input);border:1px solid var(--border);color:var(--fg);padding:8px 12px;border-radius:var(--radius);font-size:13px">
        <option value="en">English (en)</option>
        <option value="zh">繁體中文 (zh-TW)</option>
      </select>
    </div>
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

// ━━━ Helpers ━━━
let currentPage = 1;
let currentSearch = '';
function schIcon(type) {
  if (type === 'star') return '<span class="sch-star">★</span>';
  if (type === 'dot') return '<span class="sch-dot">●</span>';
  return '';
}
function provBadge(prov) {
  if (prov === 'active') return '<span class="badge-prov prov-active">ACTIVE</span>';
  return '<span class="badge-prov prov-draft">DRAFT</span>';
}

// ━━━ RuleSets (paginated) ━━━
async function loadAllRS(page) {
  currentSearch = '';
  currentPage = page || 1;
  try {
    const res = await fetch(`/api/rulesets?page=${currentPage}&size=50`);
    const data = await res.json();
    renderRS(data);
  } catch(e) { toast('Failed to load RuleSets: ' + e.message, 'error'); }
}
async function searchRS() {
  currentSearch = document.getElementById('search-input').value;
  currentPage = 1;
  try {
    const res = await fetch(`/api/rulesets?q=${encodeURIComponent(currentSearch)}&page=1&size=50`);
    const data = await res.json();
    renderRS(data);
  } catch(e) { toast('Search failed: ' + e.message, 'error'); }
}
function renderRS(data) {
  const list = data.items;
  const tb = document.getElementById('rs-table');
  tb.innerHTML = '';
  document.getElementById('rs-count').textContent = data.total + ' items';
  list.forEach(rs => {
    const tr = document.createElement('tr');
    tr.innerHTML = `<td><span class="badge ${rs.enabled?'badge-on':'badge-off'}">${rs.enabled?'ON':'OFF'}</span></td>
      <td title="${rs.name}">${rs.name}</td>
      <td>${rs.id}</td>
      <td>${provBadge(rs.prov)}</td>
      <td>${schIcon(rs.sch)}</td>`;
    tr.onclick = () => selectRS(rs, tr);
    tb.appendChild(tr);
  });
  // Pagination
  const pg = document.getElementById('rs-pagination');
  pg.innerHTML = '';
  if (data.pages > 1) {
    const prev = document.createElement('button');
    prev.textContent = '◀ Prev';
    prev.disabled = data.page <= 1;
    prev.onclick = () => currentSearch ? searchRSPage(data.page - 1) : loadAllRS(data.page - 1);
    pg.appendChild(prev);
    const info = document.createElement('span');
    info.className = 'page-info';
    info.textContent = `Page ${data.page} / ${data.pages}`;
    pg.appendChild(info);
    const next = document.createElement('button');
    next.textContent = 'Next ▶';
    next.disabled = data.page >= data.pages;
    next.onclick = () => currentSearch ? searchRSPage(data.page + 1) : loadAllRS(data.page + 1);
    pg.appendChild(next);
  }
}
async function searchRSPage(page) {
  try {
    const res = await fetch(`/api/rulesets?q=${encodeURIComponent(currentSearch)}&page=${page}&size=50`);
    const data = await res.json();
    renderRS(data);
  } catch(e) { toast('Search failed: ' + e.message, 'error'); }
}
async function selectRS(rs, tr) {
  selectedRS = rs;
  selectedRule = null;
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
      <td>${provBadge(r.prov)}</td>
      <td>${schIcon(r.sch)}</td>`;
    tr.onclick = () => {
      document.querySelectorAll('#rules-table tr').forEach(x => x.classList.remove('selected'));
      tr.classList.add('selected');
      selectedRule = { href: r.href, name: r.desc, is_ruleset: r.is_ruleset, detail_rs: rsName, src: r.src, dst: r.dst, svc: r.svc, prov: r.prov };
    };
    tb.appendChild(tr);
    if (idx === 0) {
      tr.classList.add('selected');
      selectedRule = { href: r.href, name: r.desc, is_ruleset: r.is_ruleset, detail_rs: rsName, src: r.src, dst: r.dst, svc: r.svc, prov: r.prov };
    }
  });
}

// ━━━ Schedule Modal ━━━
function openScheduleModal() {
  if (!selectedRS || !selectedRule) { toast('Please select a RuleSet on the left and a rule on the right first.', 'error'); return; }
  const r = selectedRule;
  // Block draft-only items
  if (r.prov === 'draft') {
    toast('Cannot schedule a draft-only (unprovisioned) rule. Please provision it first.', 'error');
    return;
  }
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

// ━━━ Schedules List (with checkboxes) ━━━
async function loadSchedules() {
  try {
    const res = await fetch('/api/schedules');
    const data = await res.json();
    const tb = document.getElementById('sch-table');
    tb.innerHTML = '';
    document.getElementById('sch-select-all').checked = false;
    data.forEach(s => {
      const tr = document.createElement('tr');
      tr.innerHTML = `<td><input type="checkbox" class="sch-check" data-href="${s.href}"></td>
        <td>${s.type}</td><td title="${s.rs_name}">${s.rs_name}</td><td title="${s.name}">${s.name}</td>
        <td><span class="badge ${s.action==='ALLOW'?'badge-on':(s.action==='BLOCK'?'badge-off':'')}">${s.action}</span></td>
        <td>${s.timing}</td><td>${s.id}</td>
        <td><button class="btn" style="padding:2px 6px;font-size:11px" onclick="editSchedule('${s.href}')">✎ Edit</button></td>`;
      tb.appendChild(tr);
    });
  } catch(e) { toast('Failed: ' + e.message, 'error'); }
}

async function editSchedule(href) {
  try {
    const res = await fetch('/api/schedules' + href);
    if (!res.ok) { toast('Error loading schedule.', 'error'); return; }
    const r = await res.json();
    
    selectedRule = {
      href: href, name: r.detail_name || r.name, is_ruleset: r.is_ruleset,
      detail_rs: r.detail_rs, src: r.detail_src, dst: r.detail_dst, svc: r.detail_svc, prov: 'active'
    };

    const typeLabel = r.is_ruleset ? '📦 RuleSet' : '📄 Rule';
    document.getElementById('modal-title').textContent = '✎ Edit Schedule';
    document.getElementById('modal-target-info').innerHTML = `
      <div style="background:var(--bg-card);border:1px solid var(--border);border-radius:var(--radius);padding:12px;margin-bottom:14px;font-size:13px">
        <div style="margin-bottom:6px"><span style="color:var(--fg-dim)">Type:</span> <strong style="color:var(--accent)">${typeLabel}</strong></div>
        <div style="margin-bottom:4px"><span style="color:var(--fg-dim)">RuleSet:</span> ${r.detail_rs || '-'}</div>
        <div style="margin-bottom:4px"><span style="color:var(--fg-dim)">Target:</span> <strong>${selectedRule.name}</strong></div>
        <div style="display:flex;gap:16px;margin-top:4px;color:var(--fg-dim);font-size:12px">
          <span>Src: ${r.detail_src || 'All'}</span><span>Dst: ${r.detail_dst || 'All'}</span><span>Svc: ${r.detail_svc || 'All'}</span>
        </div>
      </div>`;
    
    if (r.type === 'recurring') {
      document.querySelector('input[name="sch-type"][value="recurring"]').checked = true;
      document.getElementById('sch-action').value = r.action;
      document.getElementById('sch-days').value = (r.days || []).join(',');
      document.getElementById('sch-start').value = r.start || '08:00';
      document.getElementById('sch-end').value = r.end || '18:00';
    } else {
      document.querySelector('input[name="sch-type"][value="one_time"]').checked = true;
      document.getElementById('sch-expire').value = (r.expire_at || '').replace('T', ' ').substring(0, 16);
    }
    toggleSchType();
    document.getElementById('schedule-modal').style.display = 'flex';
  } catch(e) { toast('Error: ' + e.message, 'error'); }
}
function toggleSchSelectAll(master) {
  document.querySelectorAll('.sch-check').forEach(cb => cb.checked = master.checked);
}
async function deleteSelectedSchedules() {
  const checked = document.querySelectorAll('.sch-check:checked');
  if (checked.length === 0) { toast('Select at least one schedule to delete.', 'error'); return; }
  if (!confirm(`Delete ${checked.length} schedule(s)?`)) return;
  const hrefs = Array.from(checked).map(cb => cb.dataset.href);
  try {
    const res = await fetch('/api/schedules/delete', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({hrefs}) });
    const data = await res.json();
    if (data.ok) { toast(`${data.count} schedule(s) deleted.`); loadSchedules(); }
    else toast(data.error || 'Failed', 'error');
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
    if (data.lang) document.getElementById('cfg-lang').value = data.lang;
  } catch(e) { toast('Failed to load config', 'error'); }
}
async function saveConfig() {
  const payload = {
    pce_url: document.getElementById('cfg-url').value,
    org_id: document.getElementById('cfg-org').value,
    api_key: document.getElementById('cfg-key').value,
    api_secret: document.getElementById('cfg-sec').value,
    lang: document.getElementById('cfg-lang').value
  };
  if (!payload.pce_url || !payload.org_id || !payload.api_key) {
    toast('URL, Org ID and API Key are required.', 'error'); return;
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

// ━━━ Resizer Logic ━━━
let isResizing = false;
const resizer = document.getElementById('resizer');
const leftPane = document.getElementById('left-pane');
resizer.addEventListener('mousedown', (e) => {
  isResizing = true;
  resizer.classList.add('resizing');
  document.body.style.cursor = 'col-resize';
  e.preventDefault();
});
document.addEventListener('mousemove', (e) => {
  if (!isResizing) return;
  const newWidth = e.clientX - leftPane.getBoundingClientRect().left;
  if (newWidth > 200 && newWidth < Math.max(600, window.innerWidth * 0.5)) {
    leftPane.style.width = newWidth + 'px';
  }
});
document.addEventListener('mouseup', () => {
  if (isResizing) {
    isResizing = false;
    resizer.classList.remove('resizing');
    document.body.style.cursor = '';
  }
});

// ━━━ Init ━━━
document.addEventListener('DOMContentLoaded', () => { loadAllRS(); });
</script>
</body>
</html>
'''
