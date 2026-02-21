import sys
import getpass
import time
from src.core import Colors, truncate, extract_id

def clean_input(text):
    if not text: return ""
    chars = []
    for char in text:
        if char in ('\x08', '\x7f'): 
            if chars: chars.pop()
        elif ord(char) >= 32 or char == '\t': 
            chars.append(char)
    return "".join(chars).strip()

def get_valid_time(prompt):
    import datetime
    while True:
        raw = clean_input(input(prompt))
        if raw.lower() in ['q', 'b']: return None
        try:
            datetime.datetime.strptime(raw, "%H:%M")
            return raw
        except ValueError: 
            print(f"{Colors.RED}[-] 格式錯誤，請輸入 HH:MM{Colors.RESET}")

def paginate_and_select(items, format_func, title="搜尋結果", header_str=""):
    PAGE_SIZE = 50
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

class CLI:
    def __init__(self, core_system):
        self.cfg = core_system['cfg']
        self.db = core_system['db']
        self.pce = core_system['pce']
        self.engine = core_system['engine']

    def check_config_ready(self):
        if not self.cfg.is_ready():
            print(f"{Colors.RED}[!] 尚未設定 API，請先執行設定。{Colors.RESET}")
            return False
        return True

    def setup_config_ui(self):
        print(f"\n{Colors.HEADER}--- API 設定 (輸入 q 取消) ---{Colors.RESET}")
        curr_url = self.cfg.config.get('pce_url','')
        u_in = clean_input(input(f"PCE URL (目前: {curr_url}): "))
        if u_in.lower() in ['q', 'b']: return
        url = u_in or curr_url

        curr_org = self.cfg.config.get('org_id','')
        o_in = clean_input(input(f"Org ID  (目前: {curr_org}): "))
        if o_in.lower() in ['q', 'b']: return
        org = o_in or curr_org

        curr_key = self.cfg.config.get('api_key','')
        k_in = clean_input(input(f"API Key (目前: {curr_key}): "))
        if k_in.lower() in ['q', 'b']: return
        key = k_in or curr_key

        sec_p = "API Secret (未變更)" if self.cfg.config.get('api_secret') else "API Secret"
        sec = getpass.getpass(f"{sec_p}: ")
        secret = sec if sec else self.cfg.config.get('api_secret')
        
        if url and org and key and secret: 
            if self.cfg.save(url, org, key, secret):
                print(f"{Colors.GREEN}[+] 設定已儲存。{Colors.RESET}")

    def format_ruleset_row(self, idx, rs):
        r_count = len(rs.get('rules', []))
        status = Colors.status(rs.get('enabled'))
        rid = Colors.id(extract_id(rs['href']))
        name = truncate(rs['name'], 40)
        
        sType = self.db.get_schedule_type(rs)
        if sType == 1:
            mark = Colors.mark_self()
        elif sType == 2:
            mark = Colors.mark_child()
        else:
            mark = " "
        
        return f"{idx:<4} | {mark} | {rid:<18} | {status:<15} | Rules:{r_count:<4} | {name}"

    def format_rule_row(self, idx, r):
        rid = Colors.id(extract_id(r['href']))
        raw_desc = r.get('description') or ""
        note = truncate(raw_desc, 30)
        status = Colors.status(r.get('enabled'))
        
        # A1 Fix: Map to destinations (fallback to consumers for older PCEs)
        dest_field = r.get('destinations', r.get('consumers', []))
        src = truncate(self.pce.resolve_actor_str(dest_field), 15)
        dst = truncate(self.pce.resolve_actor_str(r.get('providers', [])), 15)
        svc = truncate(self.pce.resolve_service_str(r.get('ingress_services', [])), 10)
        
        is_sched = r['href'] in self.db.get_all()
        mark = Colors.mark_self() if is_sched else " " 
        
        return f"{idx:<4} | {mark} | {rid:<18} | {status:<15} | {note:<30} | {src:<15} | {dst:<15} | {svc}"

    def browse_and_select_ui(self):
        print(f"\n{Colors.HEADER}--- 瀏覽與新增排程 (輸入 q 返回) ---{Colors.RESET}")
        print(f"提示: {Colors.YELLOW}★{Colors.RESET}=規則集排程, {Colors.CYAN}●{Colors.RESET}=僅子規則排程")
        
        raw = clean_input(input("請輸入 ID 或 關鍵字 (直接按 Enter 瀏覽全部): "))
        if raw.lower() in ['q', 'b']: return
        
        selected_rs = None
        matches = []

        if not raw:
            print(f"{Colors.BLUE}[*] 讀取全部清單...{Colors.RESET}")
            matches = self.pce.get_all_rulesets()
        elif raw.isdigit():
            print(f"{Colors.BLUE}[*] 定位 ID: {raw} ...{Colors.RESET}")
            rs = self.pce.get_ruleset_by_id(raw)
            if rs: selected_rs = rs
            else:
                print(f"{Colors.YELLOW}[-] 找不到 ID，轉為搜尋名稱...{Colors.RESET}")
                matches = self.pce.search_rulesets(raw)
        else:
            matches = self.pce.search_rulesets(raw)

        if not selected_rs:
            if not matches: return print(f"{Colors.RED}[-] 找不到結果。{Colors.RESET}")
            header = f"{'No':<4} | {'Sch':<1} | {'ID':<8} | {'Status':<6} | {'Rules':<9} | {'Name'}"
            selected_rs = paginate_and_select(matches, self.format_ruleset_row, title="規則集清單", header_str=header)
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
            full_rs = self.pce.get_ruleset_by_id(extract_id(rs_href))
            rules = full_rs.get('rules', [])
            if not rules: return print(f"{Colors.RED}[-] 此規則集內無規則。{Colors.RESET}")

            header = f"{'No':<4} | {'Sch':<1} | {'ID':<6} | {'Status':<6} | {'Note (Desc)':<30} | {'Source':<15} | {'Dest':<15} | {'Service'}"
            r = paginate_and_select(rules, self.format_rule_row, title=f"規則清單 ({rs_name})", header_str=header)
            if not r: return

            target_href, target_name, is_rs = r['href'], r.get('description') or f"Rule {extract_id(r['href'])}", False
            
            # A1 Fix: Map to destinations
            dest_field = r.get('destinations', r.get('consumers', []))
            meta_src = self.pce.resolve_actor_str(dest_field)
            meta_dst = self.pce.resolve_actor_str(r.get('providers', []))
            meta_svc = self.pce.resolve_service_str(r.get('ingress_services', []))
        else: return

        if target_href in self.db.get_all():
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
            print(f"\n[行為] 1.{Colors.GREEN}啟動{Colors.RESET} (時間內開啟) / 2.{Colors.RED}關閉{Colors.RESET} (時間內關閉)")
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
            import datetime
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

        self.db.put(target_href, db_entry)
        self.pce.update_rule_note(target_href, note_msg)
        print(f"\n{Colors.GREEN}[+] 排程已儲存並寫入 Note! (ID: {extract_id(target_href)}){Colors.RESET}")

    def list_schedules_grouped(self):
        db_data = self.db.get_all()
        if not db_data: 
            return print(f"\n{Colors.YELLOW}[-] 目前沒有設定排程。{Colors.RESET}")
        
        groups = {}
        for href, conf in db_data.items():
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
            
            if rs_entry:
                h, c, act = rs_entry
                rid = Colors.id(extract_id(h))
                
                live_res = self.pce.get_live_item(h)
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

            for h, c, act in group['rules']:
                rid = Colors.id(extract_id(h))
                live_res = self.pce.get_live_item(h)
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

    def delete_schedule_ui(self):
        self.list_schedules_grouped()
        k = clean_input(input("輸入 ID 刪除 (q=返回): "))
        if k.lower() in ['q', 'b', '']: return
        
        db_data = self.db.get_all()
        found = [x for x in db_data if extract_id(x) == k]
        
        if found:
            href = found[0]
            print("[*] 嘗試清除 Note 標記...")
            try:
                self.pce.update_rule_note(href, "", remove=True)
            except Exception: pass
            
            self.db.delete(href)
            print(f"{Colors.GREEN}[OK] 排程已刪除。{Colors.RESET}")
        else:
            print(f"{Colors.RED}[-] 找不到該 ID。{Colors.RESET}")

    def run(self, core_system=None):
        if not self.check_config_ready(): 
            self.setup_config_ui()
            
        self.pce.update_label_cache()
        
        while True:
            print(f"\n{Colors.HEADER}=== Illumio Scheduler v4.1 (Hybrid UI) ==={Colors.RESET}")
            print("0. 設定 API")
            print("1. 瀏覽與新增排程")
            print("2. 列表 (Grouped View)")
            print("3. 刪除排程")
            print("4. 立即檢查")
            print(f"5. {Colors.CYAN}開啟 GUI 圖形介面{Colors.RESET}")
            print("q. 離開")
            ans = clean_input(input(">> "))
            
            try:
                if ans == '0': self.setup_config_ui()
                elif ans == '1': self.browse_and_select_ui()
                elif ans == '2': self.list_schedules_grouped()
                elif ans == '3': self.delete_schedule_ui()
                elif ans == '4': self.engine.check(silent=False)
                elif ans == '5':
                    if core_system:
                        print(f"{Colors.BLUE}[*] 啟動 Web GUI...{Colors.RESET}")
                        try:
                            from src.gui_ui import launch_gui
                            launch_gui(core_system)
                        except ImportError:
                            print(f"{Colors.RED}[!] Web GUI 需要 Flask。請先安裝：{Colors.RESET}")
                            print(f"      pip install flask")
                    else:
                        print(f"{Colors.RED}[-] 無法啟動 GUI（core_system 未傳入）{Colors.RESET}")
                elif ans.lower() in ['q', 'exit']: break
            except Exception as e:
                import traceback
                print(f"{Colors.RED}[FATAL ERROR] {e}{Colors.RESET}")
                traceback.print_exc()
