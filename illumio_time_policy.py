import requests
import datetime
import time
import json
import os
import urllib3
import sys
import getpass
import re

try:
    import readline
except ImportError:
    pass

# ==========================================
# File Paths & Constants
# ==========================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(SCRIPT_DIR, "rule_schedules.json")
CONFIG_FILE = os.path.join(SCRIPT_DIR, "config.json")
PAGE_SIZE = 50 

HEADERS = {'Content-Type': 'application/json', 'Accept': 'application/json'}
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

CONFIG = {}
LABEL_CACHE = {}

# ==========================================
# 0. Color Engine & Formatters
# ==========================================
class Colors:

    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    RESET = '\033[0m'
    BOLD = '\033[1m'
    GREY = '\033[90m'

    @staticmethod
    def status(enabled):
        return f"{Colors.GREEN}✔ ON {Colors.RESET}" if enabled else f"{Colors.RED}✖ OFF{Colors.RESET}"
    
    @staticmethod
    def action(act):
        if act == 'allow': 
            return f"{Colors.GREEN}時段內啟動{Colors.RESET}"
        return f"{Colors.RED}時段內關閉{Colors.RESET}"
    
    @staticmethod
    def id(text):
        return f"{Colors.CYAN}{text}{Colors.RESET}"
    
    @staticmethod
    def mark_self():
        return f"{Colors.YELLOW}★{Colors.RESET}"
        
    @staticmethod
    def mark_child():
        return f"{Colors.CYAN}●{Colors.RESET}"

def truncate(text, width):
    if not text: return " " * width
    text = str(text).replace("\n", " ") 
    text = re.sub(r'\[📅 排程:.*?\]', '', text).strip()
    text = re.sub(r'\[⏳ 有效期限.*?\]', '', text).strip()
    
    if not text: return "-"
    
    if len(text) > width:
        return text[:width-3] + "..."
    return text.ljust(width)

# ==========================================
# 1. Configuration
# ==========================================

def load_config():
    global CONFIG
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                CONFIG = json.load(f)
            return True
        except: return False
    return False

def save_config(url, org, key, secret):
    data = {"pce_url": url.rstrip("/"), "org_id": org, "api_key": key, "api_secret": secret}
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f: json.dump(data, f, indent=4)
    global CONFIG
    CONFIG = data
    print(f"{Colors.GREEN}[+] 設定已儲存。{Colors.RESET}")

def setup_config_ui():
    print(f"\n{Colors.HEADER}--- API 設定 (輸入 q 取消) ---{Colors.RESET}")
    curr_url = CONFIG.get('pce_url','')
    u_in = clean_input(input(f"PCE URL (目前: {curr_url}): "))
    if u_in.lower() in ['q', 'b']: return
    url = u_in or curr_url

    curr_org = CONFIG.get('org_id','')
    o_in = clean_input(input(f"Org ID  (目前: {curr_org}): "))
    if o_in.lower() in ['q', 'b']: return
    org = o_in or curr_org

    curr_key = CONFIG.get('api_key','')
    k_in = clean_input(input(f"API Key (目前: {curr_key}): "))
    if k_in.lower() in ['q', 'b']: return
    key = k_in or curr_key

    sec_p = "API Secret (未變更)" if CONFIG.get('api_secret') else "API Secret"
    sec = getpass.getpass(f"{sec_p}: ")
    secret = sec if sec else CONFIG.get('api_secret')
    
    if url and org and key and secret: save_config(url, org, key, secret)

def get_auth(): return (CONFIG.get('api_key'), CONFIG.get('api_secret'))
def check_config_ready():
    if not CONFIG and not load_config():
        print(f"{Colors.RED}[!] 尚未設定 API，請先執行設定。{Colors.RESET}")
        return False
    return True

# ==========================================
# 2. Utility
# ==========================================

def clean_input(text):
    if not text: return ""
    chars = []
    for char in text:
        if char in ('\x08', '\x7f'): 
            if chars: chars.pop()
        elif ord(char) >= 32 or char == '\t': chars.append(char)
    return "".join(chars).strip()

def get_valid_time(prompt):
    while True:
        raw = clean_input(input(prompt))
        if raw.lower() in ['q', 'b']: return None
        try:
            datetime.datetime.strptime(raw, "%H:%M")
            return raw
        except ValueError: print(f"{Colors.RED}[-] 格式錯誤，請輸入 HH:MM{Colors.RESET}")

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r', encoding='utf-8') as f: return json.load(f)
        except: return {}
    return {}

def save_db(db):
    with open(DB_FILE, 'w', encoding='utf-8') as f: json.dump(db, f, indent=4, ensure_ascii=False)

def extract_id(href): return href.split('/')[-1]

def paginate_and_select(items, format_func, title="搜尋結果", header_str=""):
    total = len(items)
    if total == 0:
        print(f"{Colors.YELLOW}[-] 無資料。{Colors.RESET}")
        return None

    page = 0
    while True:
        start = page * PAGE_SIZE
        end = start + PAGE_SIZE
        current_batch = items[start:end]
        
        print(f"\n{Colors.HEADER}--- {title} (顯示 {start+1}-{min(end, total)} / 共 {total} 筆) ---{Colors.RESET}")
        if header_str:
            print(f"{Colors.BOLD}{header_str}{Colors.RESET}")
            print("-" * 120)
        else:
            print("-" * 80)
            
        for i, item in enumerate(current_batch):
            real_idx = start + i + 1
            print(format_func(real_idx, item))
        print("-" * 120 if header_str else "-" * 80)

        prompt = "請選擇序號"
        opts = []
        if end < total: opts.append("(n)下一頁")
        if page > 0: opts.append("(p)上一頁")
        opts.append("(q)返回")
        
        ans = clean_input(input(f"{prompt} [{' '.join(opts)}]: ")).lower()

        if ans in ['q', 'b', '0']: return None
        elif ans == 'n' and end < total: page += 1
        elif ans == 'p' and page > 0: page -= 1
        elif ans.isdigit():
            idx = int(ans) - 1
            if 0 <= idx < total: return items[idx]
            else: print(f"{Colors.RED}[-] 序號無效。{Colors.RESET}")
        else: print(f"{Colors.RED}[-] 輸入無效。{Colors.RESET}")

# ==========================================
# 3. API Interaction
# ==========================================

def api_get(endpoint):
    url = f"{CONFIG['pce_url']}/api/v2{endpoint}"
    try: return requests.get(url, auth=get_auth(), headers=HEADERS, verify=False)
    except: return None

def update_label_cache():
    if "--monitor" in sys.argv or not check_config_ready(): return
    try:
        r1 = api_get(f"/orgs/{CONFIG['org_id']}/labels")
        if r1 and r1.status_code == 200:
            for i in r1.json(): LABEL_CACHE[i['href']] = f"{i.get('key')}:{i.get('value')}"
        r2 = api_get(f"/orgs/{CONFIG['org_id']}/sec_policy/draft/ip_lists")
        if r2 and r2.status_code == 200:
            for i in r2.json(): LABEL_CACHE[i['href']] = f"[IPList] {i.get('name')}"
    except: pass

def resolve_actor_str(actors):
    if not actors: return "Any"
    names = []
    for a in actors:
        if 'label' in a: names.append(LABEL_CACHE.get(a['label']['href'], "Label"))
        elif 'ip_list' in a: names.append(LABEL_CACHE.get(a['ip_list']['href'], "IPList"))
        elif 'actors' in a: names.append(a.get('actors'))
    return ", ".join(names)

def resolve_service_str(services):
    if not services: return "All Services"
    svcs = []
    for s in services:
        if 'port' in s:
            p, proto = s.get('port'), "UDP" if s.get('proto')==17 else "TCP"
            top = f"-{s['to_port']}" if s.get('to_port') else ""
            svcs.append(f"{proto}/{p}{top}")
        else: svcs.append("RefObj")
    return ", ".join(svcs)

def get_all_rulesets():
    print(f"{Colors.BLUE}[*] 正在讀取所有規則集...{Colors.RESET}")
    res = api_get(f"/orgs/{CONFIG['org_id']}/sec_policy/draft/rule_sets")
    if res and res.status_code == 200: return res.json()
    return []

def search_rulesets(keyword):
    print(f"{Colors.BLUE}[*] 搜尋規則集: '{keyword}' ...{Colors.RESET}")
    res = api_get(f"/orgs/{CONFIG['org_id']}/sec_policy/draft/rule_sets")
    matches = []
    if res and res.status_code == 200:
        for rs in res.json():
            if keyword.lower() in rs['name'].lower(): matches.append(rs)
    return matches

def get_ruleset_by_id(rs_id):
    res = api_get(f"/orgs/{CONFIG['org_id']}/sec_policy/draft/rule_sets/{rs_id}")
    return res.json() if res and res.status_code == 200 else None

def provision_changes(rs_href):
    payload = {"update_description": "Auto-Scheduler: Update Note", "change_subset": {"rule_sets": [{"href": rs_href}]}}
    prov_url = f"{CONFIG['pce_url']}/api/v2/orgs/{CONFIG['org_id']}/sec_policy"
    res = requests.post(prov_url, auth=get_auth(), headers=HEADERS, json=payload, verify=False)
    return res.status_code == 201

def update_rule_note(href, schedule_info, remove=False):
    print(f"{Colors.BLUE}[NOTE] 更新規則備註 (Note)...{Colors.RESET}")
    
    draft_href = href.replace("/active/", "/draft/")
    url = f"{CONFIG['pce_url']}/api/v2{draft_href}"
    res = requests.get(url, auth=get_auth(), headers=HEADERS, verify=False)
    if res.status_code != 200: return False
    
    data = res.json()
    current_desc = data.get('description', '') or ''
    
    clean_desc = re.sub(r'\s*\[📅 排程:.*?\]', '', current_desc)
    clean_desc = re.sub(r'\s*\[⏳ 有效期限.*?\]', '', clean_desc)
    clean_desc = clean_desc.strip()
    
    new_desc = clean_desc
    if not remove:
        if clean_desc:
            new_desc = f"{clean_desc}\n{schedule_info}"
        else:
            new_desc = schedule_info
    
    if new_desc == current_desc: return True

    requests.put(url, auth=get_auth(), headers=HEADERS, json={"description": new_desc}, verify=False)
    rs_href = "/".join(draft_href.split("/")[:7])
    provision_changes(rs_href)
    return True

def toggle_and_provision(href, target_enabled, is_ruleset=False):
    draft_href = href.replace("/active/", "/draft/")
    r_id = extract_id(href)
    status_str = f"{Colors.GREEN}Enabled{Colors.RESET}" if target_enabled else f"{Colors.RED}Disabled{Colors.RESET}"
    print(f"[ACTION] 切換狀態 -> {status_str} (ID: {Colors.CYAN}{r_id}{Colors.RESET})")
    
    url = f"{CONFIG['pce_url']}/api/v2{draft_href}"
    requests.put(url, auth=get_auth(), headers=HEADERS, json={"enabled": target_enabled}, verify=False)
    
    if is_ruleset: rs_href = draft_href
    else: rs_href = "/".join(draft_href.split("/")[:7])

    if provision_changes(rs_href):
        print(f"{Colors.GREEN}[SUCCESS] 已提交發布 (RuleSet ID: {extract_id(rs_href)}){Colors.RESET}")
        return True
    return False

# ==========================================
# 4. Core Logic
# ==========================================

def check_logic(silent=False):
    if not check_config_ready(): return
    db = load_db()
    now = datetime.datetime.now()
    curr_t, curr_d = now.strftime("%H:%M"), now.strftime("%A").lower()
    
    if not silent: print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] 檢查排程...", flush=True)
    
    expired_hrefs = []

    for href, c in db.items():
        is_allow = (c.get('action', 'allow') == 'allow')
        in_window = False
        target = False
        
        if c['type'] == 'recurring':
            if curr_d in [d.lower() for d in c['days']] and c['start'] <= curr_t < c['end']:
                in_window = True
            target = in_window if is_allow else (not in_window)

        elif c['type'] == 'one_time':
            expire_dt = datetime.datetime.fromisoformat(c['expire_at'])
            if now > expire_dt:
                print(f"{Colors.RED}[EXPIRED] 規則 {c['name']} (ID:{extract_id(href)}) 已過期。{Colors.RESET}")
                toggle_and_provision(href, False, c.get('is_ruleset'))
                update_rule_note(href, "", remove=True)
                expired_hrefs.append(href)
                continue
            else:
                target = True

        active_href = href.replace("/draft/", "/active/")
        res = api_get(active_href)
        
        if res and res.status_code == 200:
            curr_status = res.json().get('enabled')
            if curr_status != target:
                r_name = c.get('detail_name', c['name'])
                print(f"{Colors.YELLOW}[WARN] 狀態不符: {r_name} (ID:{extract_id(href)}) 目標:{target} != 現狀:{curr_status}{Colors.RESET}")
                toggle_and_provision(href, target, c.get('is_ruleset'))

    if expired_hrefs:
        for h in expired_hrefs: del db[h]
        save_db(db)
        print(f"{Colors.YELLOW}[CLEANUP] 已移除 {len(expired_hrefs)} 筆過期排程。{Colors.RESET}")

# ==========================================
# 5. UI - Browsing
# ==========================================

# [New] 判斷排程類型: 0=無, 1=Self, 2=Child
def get_schedule_type(rs):
    db_keys = load_db().keys()
    if rs['href'] in db_keys: return 1 # Self
    for r in rs.get('rules', []):
        if r['href'] in db_keys: return 2 # Child
    return 0

def format_ruleset_row(idx, rs):
    r_count = len(rs.get('rules', []))
    status = Colors.status(rs.get('enabled'))
    rid = Colors.id(extract_id(rs['href']))
    name = truncate(rs['name'], 40)
    
    # [New] Dual Indicator
    sType = get_schedule_type(rs)
    if sType == 1:
        mark = Colors.mark_self()
    elif sType == 2:
        mark = Colors.mark_child()
    else:
        mark = " "
    
    return f"{idx:<4} | {mark} | {rid:<18} | {status:<15} | Rules:{r_count:<4} | {name}"

def format_rule_row(idx, r):
    rid = Colors.id(extract_id(r['href']))
    raw_desc = r.get('description') or ""
    note = truncate(raw_desc, 30)
    status = Colors.status(r.get('enabled'))
    src = truncate(resolve_actor_str(r.get('consumers', [])), 15)
    dst = truncate(resolve_actor_str(r.get('providers', [])), 15)
    svc = truncate(resolve_service_str(r.get('ingress_services', [])), 10)
    
    is_sched = r['href'] in load_db()
    mark = Colors.mark_self() if is_sched else " " # Rule 只有自己有沒有
    
    return f"{idx:<4} | {mark} | {rid:<18} | {status:<15} | {note:<30} | {src:<15} | {dst:<15} | {svc}"

def browse_and_select_ui():
    print(f"\n{Colors.HEADER}--- 瀏覽與新增排程 (輸入 q 返回) ---{Colors.RESET}")
    print(f"提示: {Colors.YELLOW}★{Colors.RESET}=規則集排程, {Colors.CYAN}●{Colors.RESET}=僅子規則排程")
    
    raw = clean_input(input("請輸入 ID 或 關鍵字 (直接按 Enter 瀏覽全部): "))
    if raw.lower() in ['q', 'b']: return
    
    selected_rs = None
    matches = []

    if not raw:
        print(f"{Colors.BLUE}[*] 讀取全部清單...{Colors.RESET}")
        matches = get_all_rulesets()
    elif raw.isdigit():
        print(f"{Colors.BLUE}[*] 定位 ID: {raw} ...{Colors.RESET}")
        rs = get_ruleset_by_id(raw)
        if rs: selected_rs = rs
        else:
            print(f"{Colors.YELLOW}[-] 找不到 ID，轉為搜尋名稱...{Colors.RESET}")
            matches = search_rulesets(raw)
    else:
        matches = search_rulesets(raw)

    if not selected_rs:
        if not matches: return print(f"{Colors.RED}[-] 找不到結果。{Colors.RESET}")
        header = f"{'No':<4} | {'Sch':<1} | {'ID':<8} | {'Status':<6} | {'Rules':<9} | {'Name'}"
        selected_rs = paginate_and_select(matches, format_ruleset_row, title="規則集清單", header_str=header)
        if not selected_rs: return

    rs_href = selected_rs['href']
    rs_name = selected_rs['name']
    
    print(f"\n{Colors.GREEN}[+] 已選擇: {rs_name} (ID: {extract_id(rs_href)}){Colors.RESET}")
    print("1. 排程控制「整個規則集」")
    print("2. 瀏覽並選擇「單條規則」")
    
    sub_act = clean_input(input("動作 (q=返回) > "))
    if sub_act.lower() in ['q', 'b']: return

    target_href, target_name, is_rs = "", "", False
    meta_src, meta_dst, meta_svc, meta_rs = "All", "All", "All", rs_name

    if sub_act == '1':
        target_href, target_name, is_rs = rs_href, f"{rs_name}", True

    elif sub_act == '2':
        full_rs = get_ruleset_by_id(extract_id(rs_href))
        rules = full_rs.get('rules', [])
        if not rules: return print(f"{Colors.RED}[-] 此規則集內無規則。{Colors.RESET}")

        header = f"{'No':<4} | {'Sch':<1} | {'ID':<6} | {'Status':<6} | {'Note (Desc)':<30} | {'Source':<15} | {'Dest':<15} | {'Service'}"
        r = paginate_and_select(rules, format_rule_row, title=f"規則清單 ({rs_name})", header_str=header)
        if not r: return

        target_href, target_name, is_rs = r['href'], r.get('description') or f"Rule {extract_id(r['href'])}", False
        meta_src = resolve_actor_str(r.get('consumers', []))
        meta_dst = resolve_actor_str(r.get('providers', []))
        meta_svc = resolve_service_str(r.get('ingress_services', []))
    else: return

    # 新增前檢查
    if target_href in load_db():
        print(f"{Colors.YELLOW}[!] 警告: 此規則已存在排程設定。將覆蓋舊設定。{Colors.RESET}")
        if clean_input(input("確認? (y/n): ")).lower() != 'y': return

    print(f"\n[目標] {Colors.BOLD}{target_name}{Colors.RESET}")
    print(f"1. {Colors.GREEN}Schedule{Colors.RESET} (週期性排程)")
    print(f"2. {Colors.RED}Expiration{Colors.RESET} (時間到自動關閉並刪除排程)")
    
    mode_sel = clean_input(input("選單 (q=返回) > "))
    if mode_sel.lower() in ['q', 'b']: return

    db_entry = {}
    note_msg = ""

    if mode_sel == '1':
        print(f"\n[行為] 1.{Colors.GREEN}啟動{Colors.RESET} (時間內开启) / 2.{Colors.RED}關閉{Colors.RESET} (時間內关闭)")
        act_in = clean_input(input(">> "))
        if act_in.lower() in ['q', 'b']: return
        act = 'block' if act_in == '2' else 'allow'
        act_str = "啟動" if act == 'allow' else "關閉"

        print("[時間] 星期 (Mon,Tue...) [Enter=每天]:")
        raw_days = clean_input(input(">> "))
        if raw_days.lower() in ['q', 'b']: return
        days = [d.strip() for d in raw_days.split(',')] if raw_days else ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        days_str = "每天" if not raw_days else raw_days
        
        s_time = get_valid_time("開始 (HH:MM) [q=返回]: ")
        if not s_time: return
        e_time = get_valid_time("結束 (HH:MM) [q=返回]: ")
        if not e_time: return

        db_entry = {
            "type": "recurring", "name": target_name, "is_ruleset": is_rs, 
            "action": act, "days": days, "start": s_time, "end": e_time,
            "detail_rs": meta_rs, "detail_src": meta_src, "detail_dst": meta_dst, "detail_svc": meta_svc,
            "detail_name": target_name
        }
        note_msg = f"[📅 排程: {days_str} {s_time}-{e_time} {act_str}]"

    elif mode_sel == '2':
        raw_ex = clean_input(input("過期時間 (YYYY-MM-DD HH:MM) [q=返回]: "))
        if raw_ex.lower() in ['q', 'b']: return
        try:
            ex_fmt = raw_ex.replace(" ", "T")
            datetime.datetime.fromisoformat(ex_fmt)
        except ValueError:
            return print(f"{Colors.RED}[-] 時間格式錯誤。{Colors.RESET}")

        db_entry = {
            "type": "one_time", "name": target_name, "is_ruleset": is_rs, 
            "action": "allow", "expire_at": ex_fmt,
            "detail_rs": meta_rs, "detail_src": meta_src, "detail_dst": meta_dst, "detail_svc": meta_svc,
            "detail_name": target_name
        }
        note_msg = f"[⏳ 有效期限至: {raw_ex} 止]"

    db = load_db()
    db[target_href] = db_entry
    save_db(db)
    
    update_rule_note(target_href, note_msg)
    print(f"\n{Colors.GREEN}[+] 排程已儲存並寫入 Note! (ID: {extract_id(target_href)}){Colors.RESET}")

# ==========================================
# 6. UI - Grouped List View (Live Sync)
# ==========================================

def list_schedules_grouped():
    db = load_db()
    if not db: return print(f"\n{Colors.YELLOW}[-] 目前沒有設定排程。{Colors.RESET}")
    
    groups = {}
    for href, conf in db.items():
        rs_name = conf.get('detail_rs', 'Uncategorized')
        if rs_name not in groups: groups[rs_name] = {'rs_config': None, 'rules': []}
        
        conf_action = conf.get('action', 'allow')
        entry_data = (href, conf, conf_action)
        
        if conf.get('is_ruleset'): groups[rs_name]['rs_config'] = entry_data
        else: groups[rs_name]['rules'].append(entry_data)
            
    print("\n" + "="*120)
    print(f"{'ID':<10} | {'Type':<6} | {'Hierarchy & Note (Desc)':<50} | {'Mode/Action':<15} | {'Time/Expiration'}")
    print("-" * 120)

    for rs_name in sorted(groups.keys()):
        group = groups[rs_name]
        rs_entry = group['rs_config']
        
        # --- RuleSet Row ---
        if rs_entry:
            h, c, act = rs_entry
            rid = Colors.id(extract_id(h))
            
            active_href = h.replace("/draft/", "/active/")
            live_res = api_get(active_href)
            
            if not live_res or live_res.status_code != 200:
                display_name = f"{Colors.RED}[已刪除] (規則已從 PCE 移除){Colors.RESET}"
            else:
                live_name = live_res.json().get('name', c['name'])
                display_name = truncate(f"[RS] {live_name}", 50)

            if c['type'] == 'recurring':
                mode = Colors.action(act)
                d_str = "Everyday" if len(c['days'])==7 else ",".join([d[:3] for d in c['days']])
                time_str = f"{d_str} {c['start']}-{c['end']}"
            else:
                mode = f"{Colors.RED}EXPIRE{Colors.RESET}"
                time_str = f"Until {c['expire_at'].replace('T', ' ')}"

            print(f"{rid:<20} | {'RS':<6} | {Colors.BOLD}{display_name:<50}{Colors.RESET} | {mode:<25} | {time_str}")
        else:
            if group['rules']:
                name = truncate(f"[RS] {rs_name}", 50)
                print(f"{'':<10} | {'':<6} | {Colors.BOLD}{Colors.GREY}{name:<50}{Colors.RESET} | {'':<15} |")

        # --- Child Rules ---
        for h, c, act in group['rules']:
            rid = Colors.id(extract_id(h))
            
            active_href = h.replace("/draft/", "/active/")
            live_res = api_get(active_href)
            
            tree_prefix = f" {Colors.YELLOW}└──{Colors.RESET} "
            
            if not live_res or live_res.status_code != 200:
                display_name = tree_prefix + f"{Colors.RED}[已刪除] (規則失效){Colors.RESET}"
            else:
                live_desc = live_res.json().get('description') or f"Rule {extract_id(h)}"
                display_name = tree_prefix + truncate(live_desc, 45)

            if c['type'] == 'recurring':
                mode = Colors.action(act)
                d_str = "Everyday" if len(c['days'])==7 else ",".join([d[:3] for d in c['days']])
                time_str = f"{d_str} {c['start']}-{c['end']}"
            else:
                mode = f"{Colors.RED}EXPIRE{Colors.RESET}"
                time_str = f"Until {c['expire_at'].replace('T', ' ')}"
            
            print(f"{rid:<20} | {'Rule':<6} | {display_name:<60} | {mode:<25} | {time_str}")
            
    print("="*120)

def delete_schedule_ui():
    list_schedules_grouped()
    k = clean_input(input("輸入 ID 刪除 (q=返回): "))
    if k.lower() in ['q', 'b', '']: return
    
    db = load_db()
    found = [x for x in db if extract_id(x) == k]
    
    if found:
        href = found[0]
        print("[*] 嘗試清除 Note 標記...")
        try:
            update_rule_note(href, "", remove=True)
        except: pass
        
        del db[href]
        save_db(db)
        print(f"{Colors.GREEN}[OK] 排程已刪除。{Colors.RESET}")
    else:
        print(f"{Colors.RED}[-] 找不到該 ID。{Colors.RESET}")

def main_menu():
    if not check_config_ready(): setup_config_ui()
    update_label_cache()
    while True:
        print(f"\n{Colors.HEADER}=== Illumio Scheduler v3.2 (Dual Indicator) ==={Colors.RESET}")
        print("0. 設定 API")
        print("1. 瀏覽與新增排程")
        print("2. 列表 (Grouped View)")
        print("3. 刪除排程")
        print("4. 立即檢查")
        print("q. 離開")
        ans = clean_input(input(">> "))
        
        try:
            if ans == '0': setup_config_ui()
            elif ans == '1': browse_and_select_ui()
            elif ans == '2': list_schedules_grouped()
            elif ans == '3': delete_schedule_ui()
            elif ans == '4': check_logic(silent=False)
            elif ans.lower() in ['q', 'exit']: break
        except Exception as e:
            print(f"{Colors.RED}[FATAL ERROR] {e}{Colors.RESET}")

if __name__ == "__main__":
    if "--monitor" in sys.argv:
        if not check_config_ready(): sys.exit(1)
        print(f"[*] Service Started. DB: {DB_FILE}")
        while True:
            try: check_logic(silent=True)
            except Exception as e: print(f"[Err] {e}")
            time.sleep(300)
    else:
        try: main_menu()
        except KeyboardInterrupt: print("\nBye.")
