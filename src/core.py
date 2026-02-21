"""
Illumio Rule Scheduler — Core Engine (Zero External Dependencies)
All API calls use Python stdlib: urllib.request, http.client, ssl, base64
"""
import os
import json
import datetime
import re
import urllib.request
import urllib.error
import ssl
import base64

# Disable SSL verification globally for self-signed PCE certs
_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE

# ==========================================
# 0. Color Engine & Formatters (Shared)
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

def extract_id(href): 
    return href.split('/')[-1] if href else ""

# ==========================================
# 1. Config Manager
# ==========================================
class ConfigManager:
    def __init__(self, config_path):
        self.config_path = config_path
        self.config = {}

    def load(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
                return True
            except Exception: 
                return False
        return False

    def save(self, url, org, key, secret):
        data = {"pce_url": url.rstrip("/"), "org_id": org, "api_key": key, "api_secret": secret}
        with open(self.config_path, 'w', encoding='utf-8') as f: 
            json.dump(data, f, indent=4)
        self.config = data
        return True

    def get_auth_header(self):
        """Return HTTP Basic Auth header value"""
        cred = f"{self.config.get('api_key','')}:{self.config.get('api_secret','')}"
        b64 = base64.b64encode(cred.encode()).decode()
        return f"Basic {b64}"

    def is_ready(self):
        if not self.config:
            return self.load()
        return True

# ==========================================
# 2. Schedule Database
# ==========================================
class ScheduleDB:
    def __init__(self, db_path):
        self.db_path = db_path
        self.db = {}

    def load(self):
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, 'r', encoding='utf-8') as f: 
                    self.db = json.load(f)
            except Exception: 
                self.db = {}
        else:
            self.db = {}
        return self.db

    def save(self):
        with open(self.db_path, 'w', encoding='utf-8') as f: 
            json.dump(self.db, f, indent=4, ensure_ascii=False)

    def get_all(self):
        if not self.db:
            self.load()
        return self.db

    def get(self, href):
        return self.get_all().get(href)

    def put(self, href, data):
        self.get_all()[href] = data
        self.save()

    def delete(self, href):
        db = self.get_all()
        if href in db:
            del db[href]
            self.save()
            return True
        return False

    def get_schedule_type(self, rs):
        """0=無排程, 1=規則集本身(Self), 2=內部規則有(Child)"""
        db_keys = self.get_all().keys()
        if rs['href'] in db_keys: 
            return 1
        for r in rs.get('rules', []):
            if r['href'] in db_keys: 
                return 2
        return 0

# ==========================================
# 3. HTTP Response Wrapper (replaces requests.Response)
# ==========================================
class APIResponse:
    """Lightweight response wrapper mimicking requests.Response"""
    def __init__(self, status_code, body=b''):
        self.status_code = status_code
        self._body = body
    
    def json(self):
        return json.loads(self._body.decode('utf-8'))
    
    @property
    def text(self):
        return self._body.decode('utf-8', errors='replace')

# ==========================================
# 4. PCE API Client (stdlib only)
# ==========================================
class PCEClient:
    def __init__(self, config_manager, timeout=30):
        self.cfg = config_manager
        self.timeout = timeout
        self.label_cache = {}
        self.ruleset_cache = []

    def _request(self, method, endpoint, payload=None):
        """Core HTTP method using urllib.request"""
        if not self.cfg.is_ready(): return None
        url = f"{self.cfg.config['pce_url']}/api/v2{endpoint}"
        
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': self.cfg.get_auth_header()
        }
        
        body = json.dumps(payload).encode('utf-8') if payload else None
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        
        try:
            resp = urllib.request.urlopen(req, timeout=self.timeout, context=_SSL_CTX)
            return APIResponse(resp.status, resp.read())
        except urllib.error.HTTPError as e:
            return APIResponse(e.code, e.read() if e.fp else b'')
        except Exception as e:
            print(f"[API_ERROR] {method} {endpoint}: {e}")
            return None

    def _api_get(self, endpoint):
        return self._request('GET', endpoint)

    def _api_put(self, endpoint, payload):
        return self._request('PUT', endpoint, payload)

    def _api_post(self, endpoint, payload):
        return self._request('POST', endpoint, payload)

    def update_label_cache(self, silent=False):
        if not self.cfg.is_ready(): return
        try:
            r1 = self._api_get(f"/orgs/{self.cfg.config['org_id']}/labels")
            if r1 and r1.status_code == 200:
                for i in r1.json(): 
                    self.label_cache[i['href']] = f"{i.get('key')}:{i.get('value')}"
            
            r2 = self._api_get(f"/orgs/{self.cfg.config['org_id']}/sec_policy/draft/ip_lists")
            if r2 and r2.status_code == 200:
                for i in r2.json(): 
                    self.label_cache[i['href']] = f"[IPList] {i.get('name')}"
        except Exception as e: 
            if not silent: print(f"[Cache Error] {e}")

    def resolve_actor_str(self, actors):
        if not actors: return "Any"
        names = []
        for a in actors:
            if 'label' in a: 
                names.append(self.label_cache.get(a['label']['href'], "Label"))
            elif 'ip_list' in a: 
                names.append(self.label_cache.get(a['ip_list']['href'], "IPList"))
            elif 'actors' in a: 
                names.append(str(a.get('actors')))
        return ", ".join(names)

    def resolve_service_str(self, services):
        if not services: return "All Services"
        svcs = []
        for s in services:
            if 'port' in s:
                p, proto = s.get('port'), "UDP" if s.get('proto') == 17 else "TCP"
                top = f"-{s['to_port']}" if s.get('to_port') else ""
                svcs.append(f"{proto}/{p}{top}")
            elif 'href' in s:
                svcs.append(f"Service({extract_id(s['href'])})")
            else: 
                svcs.append("RefObj")
        return ", ".join(svcs)

    def get_all_rulesets(self, force_refresh=False):
        if self.ruleset_cache and not force_refresh:
            return self.ruleset_cache
        res = self._api_get(f"/orgs/{self.cfg.config['org_id']}/sec_policy/draft/rule_sets")
        if res and res.status_code == 200: 
            self.ruleset_cache = res.json()
            return self.ruleset_cache
        return []

    def search_rulesets(self, keyword):
        all_rs = self.get_all_rulesets()
        return [rs for rs in all_rs if keyword.lower() in rs['name'].lower()]

    def get_ruleset_by_id(self, rs_id):
        res = self._api_get(f"/orgs/{self.cfg.config['org_id']}/sec_policy/draft/rule_sets/{rs_id}")
        return res.json() if res and res.status_code == 200 else None

    def provision_changes(self, rs_href):
        """Dependency-aware provisioning: discovers required dependencies first"""
        org = self.cfg.config['org_id']
        
        # Step 1: Check what dependencies this ruleset needs
        dep_payload = {"change_subset": {"rule_sets": [{"href": rs_href}]}}
        dep_res = self._api_post(f"/orgs/{org}/sec_policy/draft/dependencies", dep_payload)
        
        # Step 2: Build complete change_subset including all dependencies
        final_subset = {"rule_sets": [{"href": rs_href}]}
        
        if dep_res and dep_res.status_code == 200:
            deps = dep_res.json()
            # Merge any dependent objects into the change_subset
            for obj_type in ['rule_sets', 'ip_lists', 'services', 'label_groups', 
                             'virtual_services', 'firewall_settings', 'enforcement_boundaries',
                             'virtual_servers', 'secure_connect_gateways']:
                dep_items = deps.get(obj_type, [])
                if dep_items:
                    existing = final_subset.get(obj_type, [])
                    existing_hrefs = {item['href'] for item in existing}
                    for item in dep_items:
                        if item.get('href') and item['href'] not in existing_hrefs:
                            existing.append({"href": item['href']})
                    final_subset[obj_type] = existing
        
        # Step 3: Provision with full dependency set
        payload = {
            "update_description": "Auto-Scheduler: Status/Note Update", 
            "change_subset": final_subset
        }
        res = self._api_post(f"/orgs/{org}/sec_policy", payload)
        if res and res.status_code == 201:
            return True
        err = res.text if res else "Connection Error"
        print(f"{Colors.RED}[PROVISION FAILED] RuleSet {extract_id(rs_href)}: {err}{Colors.RESET}")
        return False

    def update_rule_note(self, href, schedule_info, remove=False):
        draft_href = href.replace("/active/", "/draft/")
        res = self._api_get(draft_href)
        if not res or res.status_code != 200: 
            return False
            
        data = res.json()
        current_desc = data.get('description', '') or ''
        
        clean_desc = re.sub(r'\s*\[📅 排程:.*?\]', '', current_desc)
        clean_desc = re.sub(r'\s*\[⏳ 有效期限.*?\]', '', clean_desc)
        clean_desc = clean_desc.strip()
        
        new_desc = clean_desc
        if not remove:
            new_desc = f"{clean_desc}\n{schedule_info}".strip() if clean_desc else schedule_info
        
        if new_desc == current_desc: 
            return True

        put_res = self._api_put(draft_href, {"description": new_desc})
        if put_res and put_res.status_code == 204:
            rs_href = "/".join(draft_href.split("/")[:7])
            return self.provision_changes(rs_href)
        return False

    def toggle_and_provision(self, href, target_enabled, is_ruleset=False):
        draft_href = href.replace("/active/", "/draft/")
        
        put_res = self._api_put(draft_href, {"enabled": target_enabled})
        if not put_res or put_res.status_code != 204:
            print(f"{Colors.RED}[UPDATE FAILED] Target: {extract_id(href)}{Colors.RESET}")
            return False
            
        rs_href = draft_href if is_ruleset else "/".join(draft_href.split("/")[:7])
        return self.provision_changes(rs_href)

    def get_live_item(self, href):
        """Try both active and draft paths to find the item"""
        # Try active first (most common for status checks)
        active_href = href.replace("/draft/", "/active/")
        res = self._api_get(active_href)
        if res and res.status_code == 200:
            return res
        # Fallback to draft
        draft_href = href.replace("/active/", "/draft/")
        if draft_href != active_href:
            res = self._api_get(draft_href)
            if res and res.status_code == 200:
                return res
        return res  # return last response for error handling

    def get_provision_state(self, href):
        """Check provision state: 'active' if provisioned, 'draft' if draft-only, 'unknown' on error"""
        active_href = href.replace("/draft/", "/active/")
        res = self._api_get(active_href)
        if res is None:
            return 'unknown'
        if res.status_code == 200:
            return 'active'
        return 'draft'

    def is_provisioned(self, href):
        return self.get_provision_state(href) == 'active'

# ==========================================
# 5. Schedule Engine (Core Logic)
# ==========================================
class ScheduleEngine:
    DAY_MAP = {
        "mon": "monday", "tue": "tuesday", "wed": "wednesday", 
        "thu": "thursday", "fri": "friday", "sat": "saturday", "sun": "sunday"
    }

    def __init__(self, db, pce_client):
        self.db = db
        self.pce = pce_client

    @staticmethod
    def normalize_day(day_str):
        d = day_str.lower().strip()
        return ScheduleEngine.DAY_MAP.get(d[:3], d)

    def check(self, silent=False):
        if not self.pce.cfg.is_ready(): 
            return []
            
        db_data = self.db.get_all()
        now = datetime.datetime.now()
        curr_t = now.strftime("%H:%M")
        curr_d = now.strftime("%A").lower()
        prev_d = (now - datetime.timedelta(days=1)).strftime("%A").lower()
        
        logs = []
        def log(msg):
            logs.append(msg)
            if not silent: print(msg, flush=True)

        log(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] 檢查排程...")
        
        expired_hrefs = []

        for href, c in list(db_data.items()):
            is_allow = (c.get('action', 'allow') == 'allow')
            in_window = False
            target = False
            
            if c['type'] == 'recurring':
                days_list = [self.normalize_day(d) for d in c['days']]
                day_match = curr_d in days_list
                prev_day_match = prev_d in days_list
                start_t, end_t = c['start'], c['end']
                
                if start_t <= end_t:
                    in_window = day_match and (start_t <= curr_t < end_t)
                else:
                    in_window = (day_match and curr_t >= start_t) or \
                                (prev_day_match and curr_t < end_t)
                
                target = in_window if is_allow else (not in_window)

            elif c['type'] == 'one_time':
                expire_dt = datetime.datetime.fromisoformat(c['expire_at'])
                if now > expire_dt:
                    log(f"{Colors.RED}[EXPIRED] {c['name']} (ID:{extract_id(href)}) 已過期。{Colors.RESET}")
                    self.pce.toggle_and_provision(href, False, c.get('is_ruleset'))
                    self.pce.update_rule_note(href, "", remove=True)
                    expired_hrefs.append(href)
                    continue
                else:
                    target = True

            res = self.pce.get_live_item(href)
            if res and res.status_code == 200:
                curr_status = res.json().get('enabled')
                if curr_status != target:
                    r_name = c.get('detail_name', c['name'])
                    status_str = f"{Colors.GREEN}Enabled{Colors.RESET}" if target else f"{Colors.RED}Disabled{Colors.RESET}"
                    log(f"[ACTION] 切換狀態 -> {status_str} (ID: {Colors.CYAN}{extract_id(href)}{Colors.RESET}) - {r_name}")
                    if self.pce.toggle_and_provision(href, target, c.get('is_ruleset')):
                        log(f"{Colors.GREEN}[SUCCESS] 已提交發布{Colors.RESET}")

        for h in expired_hrefs: 
            self.db.delete(h)
        if expired_hrefs:
            log(f"{Colors.YELLOW}[CLEANUP] 已移除 {len(expired_hrefs)} 筆過期排程。{Colors.RESET}")
            
        return logs
