import sys
import getpass
import time
from src.core import Colors, truncate, extract_id
from src.i18n import t, set_lang, get_lang

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
            print(f"{Colors.RED}[-] {t('sch_time_error')}{Colors.RESET}")

def paginate_and_select(items, format_func, title="", header_str=""):
    PAGE_SIZE = 50
    total = len(items)
    if total == 0:
        print(f"{Colors.YELLOW}[-] {t('list_no_schedule')}{Colors.RESET}")
        return None

    page = 0
    while True:
        start = page * PAGE_SIZE
        end = start + PAGE_SIZE
        current_batch = items[start:end]
        
        print(f"\n{Colors.HEADER}--- {title} ({start+1}-{min(end, total)} / {total}) ---{Colors.RESET}")
        if header_str:
            print(f"{Colors.BOLD}{header_str}{Colors.RESET}")
            print("-" * 120)
        else:
            print("-" * 80)
            
        for i, item in enumerate(current_batch):
            real_idx = start + i + 1
            print(format_func(real_idx, item))
        print("-" * 120 if header_str else "-" * 80)

        prompt = t('select_prompt')
        opts = []
        if end < total: opts.append(f"(n){t('next_page')}")
        if page > 0: opts.append(f"(p){t('prev_page')}")
        opts.append(f"(q){t('back')}")
        
        ans = clean_input(input(f"{prompt} [{' '.join(opts)}]: ")).lower()

        if ans in ['q', 'b', '0']: return None
        elif ans == 'n' and end < total: page += 1
        elif ans == 'p' and page > 0: page -= 1
        elif ans.isdigit():
            idx = int(ans) - 1
            if 0 <= idx < total: return items[idx]
            else: print(f"{Colors.RED}[-] {t('invalid_number')}{Colors.RESET}")
        else: print(f"{Colors.RED}[-] {t('invalid_input')}{Colors.RESET}")

class CLI:
    def __init__(self, core_system):
        self.cfg = core_system['cfg']
        self.db = core_system['db']
        self.pce = core_system['pce']
        self.engine = core_system['engine']

    def check_config_ready(self):
        if not self.cfg.is_ready():
            print(f"{Colors.RED}[!] {t('config_not_ready')}{Colors.RESET}")
            return False
        return True

    def setup_config_ui(self):
        while True:
            c = self.cfg.config
            url = c.get('pce_url', 'Not Set')
            key = c.get('api_key', '')
            masked_key = f"{key[:5]}..." if key else "Not Set"
            
            alert_mail = c.get('alert_mail', '')
            alert_str = f"{t('cfg_alert_mail')} ({alert_mail})" if alert_mail else "None"
            
            ssl_v = c.get('ssl_verify', False)
            ssl_str = t('cfg_ssl_verify') if ssl_v else t('cfg_ssl_ignore')
            
            smtp_h = c.get('smtp_host', '')
            smtp_p = c.get('smtp_port', '')
            smtp_a = t('cfg_auth_on') if c.get('smtp_auth', True) else t('cfg_auth_off')
            smtp_str = f"{smtp_h}:{smtp_p} | Auth:{smtp_a}" if smtp_h else "Not Configured"

            print(f"\n{Colors.HEADER}=== System Settings ==={Colors.RESET} {t('menu_version')}")
            print(f"API URL : {url}")
            print(f"API Key : {masked_key}")
            print(f"{t('cfg_alerts_label')}  : {alert_str}")
            print("-" * 40)
            print(f"1. {t('cfg_api_title')} (URL, Key, Secret)")
            print(f"2. {t('cfg_alert_title')}")
            print(f"3. {t('cfg_ssl_title')} ({t('cfg_ssl_current')}: {ssl_str})")
            print(f"4. {t('cfg_smtp_title')} ({smtp_str})")
            print(f"0. {t('back')}")
            
            ans = clean_input(input(f"\n{t('select_prompt')}: "))
            if ans == '0' or ans.lower() in ['q', 'b']: break

            if ans == '1':
                print(f"\n{Colors.CYAN}[*] {t('cfg_api_title')}{Colors.RESET}")
                u_in = clean_input(input(f"PCE URL ({t('sch_current')}: {url}): "))
                p_url = u_in or url

                curr_org = c.get('org_id','')
                o_in = clean_input(input(f"Org ID  ({t('sch_current')}: {curr_org}): "))
                p_org = o_in or curr_org

                curr_key = c.get('api_key','')
                k_in = clean_input(input(f"API Key ({t('sch_current')}: {curr_key}): "))
                p_key = k_in or curr_key

                sec_p = "API Secret (unchanged)" if c.get('api_secret') else "API Secret"
                sec = getpass.getpass(f"{sec_p}: ")
                p_secret = sec if sec else c.get('api_secret')
                
                if p_url and p_org and p_key and p_secret: 
                    self.cfg.save(p_url, p_org, p_key, p_secret)
                    print(f"{Colors.GREEN}[+] {t('config_saved')}{Colors.RESET}")
            
            elif ans == '2':
                # Alerts & Language
                print(f"\n{Colors.CYAN}[*] {t('cfg_alert_title')}{Colors.RESET}")
                m_in = clean_input(input(f"Alert Email ({t('sch_current')}: {alert_mail}): "))
                new_mail = m_in if m_in else alert_mail
                
                print(f"\n1. {t('lang_en')}")
                print(f"2. {t('lang_zh')}")
                l_ans = clean_input(input(f"{t('lang_prompt')} ({t('sch_current')}: {get_lang().upper()}): "))
                if l_ans == '1': set_lang('en'); self.cfg.save_lang('en')
                elif l_ans == '2': set_lang('zh'); self.cfg.save_lang('zh')
                
                self.cfg.save(c['pce_url'], c['org_id'], c['api_key'], c['api_secret'], alert_mail=new_mail)
                print(f"{Colors.GREEN}[+] {t('config_saved')}{Colors.RESET}")

            elif ans == '3':
                # SSL Toggle
                new_ssl = not ssl_v
                self.cfg.save(c['pce_url'], c['org_id'], c['api_key'], c['api_secret'], ssl_verify=new_ssl)
                print(f"{Colors.GREEN}[+] {t('cfg_ssl_title')} -> {t('cfg_ssl_verify') if new_ssl else t('cfg_ssl_ignore')}{Colors.RESET}")

            elif ans == '4':
                # SMTP Settings
                print(f"\n{Colors.CYAN}[*] {t('cfg_smtp_title')}{Colors.RESET}")
                h_in = clean_input(input(f"SMTP Host ({t('sch_current')}: {smtp_h}): "))
                new_host = h_in or smtp_h
                
                p_in = clean_input(input(f"SMTP Port ({t('sch_current')}: {smtp_p}): "))
                new_port = p_in or smtp_p
                
                a_in = clean_input(input(f"SMTP Auth (y/n) ({t('sch_current')}: {smtp_a}): "))
                new_auth = True if a_in.lower() == 'y' else (False if a_in.lower() == 'n' else c.get('smtp_auth', True))
                
                self.cfg.save(c['pce_url'], c['org_id'], c['api_key'], c['api_secret'], smtp_host=new_host, smtp_port=new_port, smtp_auth=new_auth)
                print(f"{Colors.GREEN}[+] {t('config_saved')}{Colors.RESET}")

    def select_language(self):
        # This is now integrated into option 2 of setup_config_ui, but keep it for direct access if needed
        print(f"\n{Colors.HEADER}--- {t('lang_prompt')} ---{Colors.RESET}")
        print(f"  1. {t('lang_en')}")
        print(f"  2. {t('lang_zh')}")
        ans = clean_input(input(">> "))
        if ans == '1': 
            set_lang('en')
            self.cfg.save_lang('en')
        elif ans == '2': 
            set_lang('zh')
            self.cfg.save_lang('zh')
        else: return
        print(f"{Colors.GREEN}[+] {t('lang_set')} {t('lang_en') if get_lang() == 'en' else t('lang_zh')}{Colors.RESET}")

    # ==========================================
    # Formatters
    # ==========================================
    def format_ruleset_row(self, idx, rs):
        r_count = len(rs.get('rules', []))
        
        # Format Status (apply color after padding)
        is_en = rs.get('enabled')
        st_text = "✔ ON" if is_en else "✖ OFF"
        st_pad = f"{st_text:<8}"
        status = f"{Colors.GREEN}{st_pad}{Colors.RESET}" if is_en else f"{Colors.RED}{st_pad}{Colors.RESET}"
        
        rid = Colors.id(f"{extract_id(rs['href']):<6}")
        name = truncate(rs['name'], 40)
        
        # Format PROV (apply color after padding)
        ut = rs.get('update_type')
        prov_text = "DRAFT" if ut else "ACTIVE"
        prov_pad = f"{prov_text:<6}"
        prov_state = f"{Colors.YELLOW}{prov_pad}{Colors.RESET}" if ut else f"{Colors.GREEN}{prov_pad}{Colors.RESET}"
        
        sType = self.db.get_schedule_type(rs)
        if sType == 1:
            mark = Colors.mark_self()
        elif sType == 2:
            mark = Colors.mark_child()
        else:
            mark = " "
        
        return f"{idx:<4} | {mark} | {rid} | {prov_state} | {status} | Rules:{str(r_count):<4} | {name}"

    def format_rule_row(self, idx, r):
        rid = Colors.id(f"{extract_id(r['href']):<6}")
        raw_desc = r.get('description') or ""
        note = truncate(raw_desc, 30)
        
        is_en = r.get('enabled')
        st_text = "✔ ON" if is_en else "✖ OFF"
        st_pad = f"{st_text:<8}"
        status = f"{Colors.GREEN}{st_pad}{Colors.RESET}" if is_en else f"{Colors.RED}{st_pad}{Colors.RESET}"
        
        dest_field = r.get('destinations', r.get('consumers', []))
        src = truncate(self.pce.resolve_actor_str(dest_field), 15)
        dst = truncate(self.pce.resolve_actor_str(r.get('providers', [])), 15)
        svc = truncate(self.pce.resolve_service_str(r.get('ingress_services', [])), 10)
        
        # Format PROV
        ut = r.get('update_type')
        prov_text = "DRAFT" if ut else "ACTIVE"
        prov_pad = f"{prov_text:<6}"
        prov_state = f"{Colors.YELLOW}{prov_pad}{Colors.RESET}" if ut else f"{Colors.GREEN}{prov_pad}{Colors.RESET}"
        
        is_sched = r['href'] in self.db.get_all()
        mark = Colors.mark_self() if is_sched else " " 
        
        return f"{idx:<4} | {mark} | {rid} | {prov_state} | {status} | {note:<30} | {src:<15} | {dst:<15} | {svc}"

    # ==========================================
    # Unified Schedule Management (List + Edit + Delete in one view)
    # ==========================================
    def schedule_management_ui(self):
        while True:
            # Show the grouped list every iteration
            self._list_grouped()
            
            # Show inline commands
            print(f"\n  {Colors.BOLD}{t('sch_hint')}: {Colors.YELLOW}★{Colors.RESET}={t('sch_hint_rs')}, {Colors.CYAN}●{Colors.RESET}={t('sch_hint_child')}")
            print(f"  {Colors.GREEN}a{Colors.RESET}={t('sch_browse')}  |  {Colors.CYAN}e <ID>{Colors.RESET}={t('sch_edit')}  |  {Colors.RED}d <ID,ID,...>{Colors.RESET}={t('sch_delete')}  |  r=Refresh  |  q={t('sch_back')}")
            
            ans = clean_input(input(">> ")).strip()
            if ans.lower() in ['q', 'b', '']: return
            
            try:
                if ans.lower() == 'a':
                    self._browse_and_add()
                elif ans.lower() == 'r':
                    continue  # will re-render the list
                elif ans.lower().startswith('e '):
                    # Edit: e <ID>
                    edit_id = ans[2:].strip()
                    if edit_id:
                        self._edit_by_id(edit_id)
                elif ans.lower().startswith('d '):
                    # Delete: d <ID> or d <ID1,ID2,...>
                    ids_str = ans[2:].strip()
                    if ids_str:
                        self._delete_by_ids(ids_str)
                else:
                    # If user just types a number, treat as edit
                    if ans.isdigit():
                        self._edit_by_id(ans)
                    else:
                        print(f"{Colors.RED}[-] {t('invalid_input')}{Colors.RESET}")
            except Exception as e:
                import traceback
                print(f"{Colors.RED}[ERROR] {e}{Colors.RESET}")
                traceback.print_exc()

    # ── Shared: Collect Schedule Parameters ──
    def _collect_schedule_params(self, target_name, is_rs, meta_rs, meta_src, meta_dst, meta_svc, existing=None):
        print(f"\n[{t('sch_target')}] {Colors.BOLD}{target_name}{Colors.RESET}")
        print(f"1. {Colors.GREEN}{t('sch_type_recurring')}{Colors.RESET}")
        print(f"2. {Colors.RED}{t('sch_type_expire')}{Colors.RESET}")
        
        default_mode = ""
        if existing:
            default_mode = "1" if existing.get('type') == 'recurring' else "2"
            curr_type = t('sch_type_recurring') if default_mode == '1' else t('sch_type_expire')
            print(f"{Colors.GREY}({t('sch_current')}: {curr_type}){Colors.RESET}")
        
        mode_sel = clean_input(input(f"{t('select_prompt')} (q={t('back')}) > "))
        if mode_sel.lower() in ['q', 'b']: return None, None
        if not mode_sel and default_mode: mode_sel = default_mode

        if mode_sel == '1':
            print(f"\n[{t('sch_action_label')}] 1.{Colors.GREEN}{t('sch_action_enable')}{Colors.RESET} / 2.{Colors.RED}{t('sch_action_disable')}{Colors.RESET}")
            default_act = ""
            if existing and existing.get('type') == 'recurring':
                default_act = "2" if existing.get('action') == 'block' else "1"
                print(f"{Colors.GREY}({t('sch_current')}: {'2' if default_act == '2' else '1'}){Colors.RESET}")
            
            act_in = clean_input(input(">> "))
            if act_in.lower() in ['q', 'b']: return None, None
            if not act_in and default_act: act_in = default_act
            act = 'block' if act_in == '2' else 'allow'

            default_days = ""
            if existing and existing.get('type') == 'recurring':
                default_days = ",".join(existing.get('days', []))
            print(f"[{t('sch_days_prompt')}]")
            if default_days:
                print(f"{Colors.GREY}({t('sch_current')}: {default_days}){Colors.RESET}")
            raw_days = clean_input(input(">> "))
            if raw_days.lower() in ['q', 'b']: return None, None
            if not raw_days and default_days: raw_days = default_days
            days = [d.strip() for d in raw_days.split(',')] if raw_days else ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            days_str = t('action_everyday') if not raw_days else raw_days
            
            default_start = existing.get('start', '') if existing and existing.get('type') == 'recurring' else ''
            default_end = existing.get('end', '') if existing and existing.get('type') == 'recurring' else ''
            
            prompt_s = t('sch_start_prompt')
            if default_start: prompt_s += f" ({t('sch_current')}: {default_start})"
            prompt_s += f" {t('sch_time_format_hint')} "
            s_time = clean_input(input(prompt_s))
            if s_time.lower() in ['q', 'b']: return None, None
            if not s_time and default_start: s_time = default_start
            
            prompt_e = t('sch_end_prompt')
            if default_end: prompt_e += f" ({t('sch_current')}: {default_end})"
            prompt_e += f" {t('sch_time_format_hint')} "
            e_time = clean_input(input(prompt_e))
            if e_time.lower() in ['q', 'b']: return None, None
            if not e_time and default_end: e_time = default_end

            import datetime
            try:
                t1 = datetime.datetime.strptime(s_time, "%H:%M")
                t2 = datetime.datetime.strptime(e_time, "%H:%M")
                if t1 >= t2:
                    raise ValueError
            except ValueError:
                print(f"{Colors.RED}[-] {t('sch_time_invalid')}{Colors.RESET}")
                return None, None

            act_str = t('action_enable_in_window') if act == 'allow' else t('action_disable_in_window')
            db_entry = {
                "type": "recurring", "name": target_name, "is_ruleset": is_rs, 
                "action": act, "days": days, "start": s_time, "end": e_time,
                "detail_rs": meta_rs, "detail_src": meta_src, "detail_dst": meta_dst, "detail_svc": meta_svc,
                "detail_name": target_name
            }
            note_msg = f"[📅 {t('sch_tag_recurring')}: {days_str} {s_time}-{e_time} {act_str}]"
            return db_entry, note_msg

        elif mode_sel == '2':
            import datetime
            default_expire = ''
            if existing and existing.get('type') == 'one_time':
                default_expire = existing.get('expire_at', '').replace('T', ' ')
            
            prompt_ex = t('sch_expire_prompt')
            if default_expire: prompt_ex += f" ({t('sch_current')}: {default_expire})"
            prompt_ex += " "
            raw_ex = clean_input(input(prompt_ex))
            if raw_ex.lower() in ['q', 'b']: return None, None
            if not raw_ex and default_expire: raw_ex = default_expire
            
            try:
                ex_fmt = raw_ex.replace(" ", "T")
                datetime.datetime.fromisoformat(ex_fmt)
            except ValueError:
                print(f"{Colors.RED}[-] {t('sch_time_error')}{Colors.RESET}")
                return None, None

            db_entry = {
                "type": "one_time", "name": target_name, "is_ruleset": is_rs, 
                "action": "allow", "expire_at": ex_fmt,
                "detail_rs": meta_rs, "detail_src": meta_src, "detail_dst": meta_dst, "detail_svc": meta_svc,
                "detail_name": target_name
            }
            note_msg = f"[⏳ {t('sch_tag_expire')}: {raw_ex}]"
            return db_entry, note_msg
        
        return None, None

    # ── 1. Browse & Add ──
    def _browse_and_add(self):
        print(f"\n{Colors.HEADER}--- {t('browse_title')} ---{Colors.RESET}")
        
        raw = clean_input(input(f"{t('browse_prompt')} "))
        if raw.lower() in ['q', 'b']: return
        
        selected_rs = None
        matches = []

        if not raw:
            print(f"{Colors.BLUE}[*] {t('browse_loading')}{Colors.RESET}")
            matches = self.pce.get_all_rulesets()
        elif raw.isdigit():
            print(f"{Colors.BLUE}[*] {t('browse_locate')} {raw} ...{Colors.RESET}")
            rs = self.pce.get_ruleset_by_id(raw)
            if rs: selected_rs = rs
            else:
                print(f"{Colors.YELLOW}[-] {t('browse_not_found')}{Colors.RESET}")
                matches = self.pce.search_rulesets(raw)
        else:
            matches = self.pce.search_rulesets(raw)

        if not selected_rs:
            if not matches: return print(f"{Colors.RED}[-] {t('browse_no_result')}{Colors.RESET}")
            header = f"{t('hdr_no'):<4} | {t('hdr_sch'):<1} | {t('hdr_id'):<6} | {'PROV':<6} | {t('hdr_status'):<8} | {t('hdr_rules'):<9} | {t('hdr_name')}"
            selected_rs = paginate_and_select(matches, self.format_ruleset_row, title="RuleSets", header_str=header)
            if not selected_rs: return

        rs_href = selected_rs['href']
        rs_name = selected_rs['name']
        
        print(f"\n{Colors.GREEN}[+] {t('browse_selected')} {rs_name} (ID: {extract_id(rs_href)}){Colors.RESET}")
        print(f"1. {t('browse_opt_rs')}")
        print(f"2. {t('browse_opt_rule')}")
        
        sub_act = clean_input(input(f"{t('browse_action')} "))
        if sub_act.lower() in ['q', 'b']: return

        target_href, target_name, is_rs = "", "", False
        meta_src, meta_dst, meta_svc, meta_rs = "All", "All", "All", rs_name

        if sub_act == '1':
            target_href, target_name, is_rs = rs_href, f"{rs_name}", True

        elif sub_act == '2':
            full_rs = self.pce.get_ruleset_by_id(extract_id(rs_href))
            rules = full_rs.get('rules', [])
            if not rules: return print(f"{Colors.RED}[-] {t('browse_no_rules')}{Colors.RESET}")

            header = f"{t('hdr_no'):<4} | {t('hdr_sch'):<1} | {t('hdr_id'):<6} | {'PROV':<6} | {t('hdr_status'):<8} | {t('hdr_note'):<30} | {t('hdr_source'):<15} | {t('hdr_dest'):<15} | {t('hdr_service')}"
            r = paginate_and_select(rules, self.format_rule_row, title=f"Rules ({rs_name})", header_str=header)
            if not r: return

            target_href, target_name, is_rs = r['href'], r.get('description') or f"Rule {extract_id(r['href'])}", False
            
            dest_field = r.get('destinations', r.get('consumers', []))
            meta_src = self.pce.resolve_actor_str(dest_field)
            meta_dst = self.pce.resolve_actor_str(r.get('providers', []))
            meta_svc = self.pce.resolve_service_str(r.get('ingress_services', []))
        else: return

        # Block draft-only scheduling
        if not self.pce.is_provisioned(target_href):
            print(f"{Colors.RED}[!] Cannot schedule a draft-only (unprovisioned) rule. Please provision it first.{Colors.RESET}")
            return

        if target_href in self.db.get_all():
            print(f"{Colors.YELLOW}[!] {t('sch_exists_warn')}{Colors.RESET}")
            if clean_input(input(f"{t('sch_confirm')} ")).lower() != 'y': return

        db_entry, note_msg = self._collect_schedule_params(target_name, is_rs, meta_rs, meta_src, meta_dst, meta_svc)
        if not db_entry: return

        self.db.put(target_href, db_entry)
        self.pce.update_rule_note(target_href, note_msg)
        print(f"\n{Colors.GREEN}[+] {t('sch_saved')} (ID: {extract_id(target_href)}){Colors.RESET}")

    # ── List Grouped ──
    def _list_grouped(self):
        db_data = self.db.get_all()
        if not db_data: 
            print(f"\n{Colors.YELLOW}[-] {t('list_no_schedule')}{Colors.RESET}")
            return
        
        groups = {}
        for href, conf in db_data.items():
            rs_name = conf.get('detail_rs', 'Uncategorized')
            if rs_name not in groups: groups[rs_name] = {'rs_config': None, 'rules': []}
            
            conf_action = conf.get('action', 'allow')
            entry_data = (href, conf, conf_action)
            
            if conf.get('is_ruleset'): groups[rs_name]['rs_config'] = entry_data
            else: groups[rs_name]['rules'].append(entry_data)
                
        print("\n" + "="*145)
        print(f"{t('hdr_sch'):<3} | {t('hdr_id'):<6} | {'Type':<6} | {t('hdr_note'):<25} | {t('hdr_source'):<12} | {t('hdr_dest'):<12} | {t('hdr_service'):<16} | {t('list_mode'):<10} | {t('list_timing')}")
        print("-" * 145)

        for rs_name in sorted(groups.keys()):
            group = groups[rs_name]
            rs_entry = group['rs_config']
            
            if rs_entry:
                h, c, act = rs_entry
                rid = Colors.id(f"{extract_id(h):<6}")
                mark = f"{Colors.YELLOW}★{Colors.RESET}"
                
                live_res = self.pce.get_live_item(h)
                if live_res and live_res.status_code == 200:
                    live_name = live_res.json().get('name', c['name'])
                    raw_name = truncate(f"[RS] {live_name}", 25)
                    display_name = f"{Colors.BOLD}{raw_name:<25}{Colors.RESET}"
                elif live_res is None:
                    raw_name = truncate(f"[RS] {c.get('name', rs_name)} (Failed)", 25)
                    display_name = f"{Colors.YELLOW}{raw_name:<25}{Colors.RESET}"
                else:
                    raw_name = truncate(f"[RS] {t('list_deleted')}", 25)
                    display_name = f"{Colors.RED}{raw_name:<25}{Colors.RESET}"

                if c['type'] == 'recurring':
                    mode_raw = t('sch_action_enable') if act == 'allow' else t('sch_action_disable')
                    mode_pad = f"{mode_raw:<10}"
                    mode = f"{Colors.GREEN}{mode_pad}{Colors.RESET}" if act == 'allow' else f"{Colors.RED}{mode_pad}{Colors.RESET}"
                    d_str = t('action_everyday') if len(c['days'])==7 else ",".join([d[:3] for d in c['days']])
                    time_str = f"{d_str} {c['start']}-{c['end']}"
                else:
                    mode = f"{Colors.RED}EXPIRE    {Colors.RESET}"
                    time_str = f"Until {c['expire_at'].replace('T', ' ')}"

                print(f" {mark}  | {rid} | {'RS':<6} | {display_name} | {'-':<12} | {'-':<12} | {'-':<16} | {mode} | {time_str}")
            else:
                if group['rules']:
                    name = truncate(f"[RS] {rs_name}", 25)
                    print(f" {' ':1}  | {' ':6} | {'      '} | {Colors.BOLD}{Colors.GREY}{name:<25}{Colors.RESET} | {' ':12} | {' ':12} | {' ':16} | {' ':10} | {' '}")

            for h, c, act in group['rules']:
                rid = Colors.id(f"{extract_id(h):<6}")
                mark = f"{Colors.CYAN}●{Colors.RESET}"
                
                live_res = self.pce.get_live_item(h)
                if live_res and live_res.status_code == 200:
                    r_obj = live_res.json()
                    dest_field = r_obj.get('destinations', r_obj.get('consumers', []))
                    src = truncate(self.pce.resolve_actor_str(dest_field), 12)
                    dst = truncate(self.pce.resolve_actor_str(r_obj.get('providers', [])), 12)
                    svc = truncate(self.pce.resolve_service_str(r_obj.get('ingress_services', [])), 16)
                    
                    rule_action = r_obj.get('action', 'allow')
                    if 'deny' in rule_action.lower():
                        type_str = f"{Colors.RED}{'Deny':<6}{Colors.RESET}"
                    else:
                        type_str = f"{Colors.GREEN}{'Allow':<6}{Colors.RESET}"
                    
                    desc = r_obj.get('description', '').strip()
                    if not desc or desc == '-':
                        desc = "(No description)"
                    else:
                        desc = desc.split('\n')[0]
                        
                    raw_name = truncate(f" └─ {desc}", 25)
                    display_name = f"{Colors.GREY}{raw_name:<25}{Colors.RESET}"
                elif live_res is None:
                    type_str = f"{Colors.YELLOW}{'Wait':<6}{Colors.RESET}"
                    src = dst = svc = "-"
                    raw_name = truncate(f" └─ (Failed connection)", 25)
                    display_name = f"{Colors.YELLOW}{raw_name:<25}{Colors.RESET}"
                else:
                    type_str = f"{Colors.RED}{'-':<6}{Colors.RESET}"
                    src = dst = svc = "-"
                    raw_name = truncate(f" └─ {t('list_rule_deleted')}", 25)
                    display_name = f"{Colors.RED}{raw_name:<25}{Colors.RESET}"

                if c['type'] == 'recurring':
                    mode_raw = t('sch_action_enable') if act == 'allow' else t('sch_action_disable')
                    mode_pad = f"{mode_raw:<10}"
                    mode = f"{Colors.GREEN}{mode_pad}{Colors.RESET}" if act == 'allow' else f"{Colors.RED}{mode_pad}{Colors.RESET}"
                    d_str = t('action_everyday') if len(c['days'])==7 else ",".join([d[:3] for d in c['days']])
                    time_str = f"{d_str} {c['start']}-{c['end']}"
                else:
                    mode = f"{Colors.RED}EXPIRE    {Colors.RESET}"
                    time_str = f"Until {c['expire_at'].replace('T', ' ')}"
                
                print(f" {mark}  | {rid} | {type_str} | {display_name} | {src:<12} | {dst:<12} | {svc:<16} | {mode} | {time_str}")
                
        print("="*145)

    # ── Edit by ID ──
    def _edit_by_id(self, edit_id):
        db_data = self.db.get_all()
        found = [x for x in db_data if extract_id(x) == edit_id]
        if not found:
            return print(f"{Colors.RED}[-] {t('edit_not_found')}{Colors.RESET}")
        
        href = found[0]
        existing = db_data[href]
        
        print(f"\n{Colors.CYAN}[*] {t('edit_editing')} {existing.get('detail_name', existing['name'])} (ID: {edit_id}){Colors.RESET}")
        print(f"{Colors.GREY}{t('sch_keep_enter')}{Colors.RESET}")
        
        target_name = existing.get('detail_name', existing.get('name', ''))
        is_rs = existing.get('is_ruleset', False)
        meta_rs = existing.get('detail_rs', '')
        meta_src = existing.get('detail_src', 'All')
        meta_dst = existing.get('detail_dst', 'All')
        meta_svc = existing.get('detail_svc', 'All')
        
        db_entry, note_msg = self._collect_schedule_params(target_name, is_rs, meta_rs, meta_src, meta_dst, meta_svc, existing=existing)
        if not db_entry: return
        
        self.db.put(href, db_entry)
        self.pce.update_rule_note(href, note_msg)
        print(f"\n{Colors.GREEN}[+] {t('sch_updated')} (ID: {extract_id(href)}){Colors.RESET}")

    # ── Delete by IDs (multi-delete) ──
    def _delete_by_ids(self, ids_str):
        db_data = self.db.get_all()
        ids = [x.strip() for x in ids_str.replace(' ', ',').split(',') if x.strip()]
        
        to_delete = []
        for k in ids:
            found = [x for x in db_data if extract_id(x) == k]
            if found:
                href = found[0]
                conf = db_data[href]
                to_delete.append((href, conf, k))
                print(f"  {t('delete_target')} {conf.get('detail_name', conf['name'])} (ID: {k})")
            else:
                print(f"  {Colors.RED}[-] ID {k}: {t('delete_not_found')}{Colors.RESET}")
        
        if not to_delete:
            return
        
        if clean_input(input(f"\n  {t('delete_confirm')} ({len(to_delete)} items) ")).lower() != 'y':
            return
        
        for href, conf, k in to_delete:
            try:
                self.pce.update_rule_note(href, "", remove=True)
            except Exception: pass
            self.db.delete(href)
            print(f"  {Colors.GREEN}[OK] ID {k} {t('delete_done')}{Colors.RESET}")

    # ==========================================
    # Main Menu
    # ==========================================
    def run(self, core_system=None):
        if not self.check_config_ready(): 
            self.setup_config_ui()
            
        self.pce.update_label_cache()
        
        while True:
            print(f"\n{Colors.HEADER}=== {t('app_title')} ==={Colors.RESET}")
            print(f"0. {t('menu_config')}")
            print(f"1. {t('menu_schedule')}")
            print(f"2. {t('menu_check')}")
            print(f"3. {Colors.CYAN}{t('menu_webgui')}{Colors.RESET}")
            print(f"q. {t('menu_quit')}")
            ans = clean_input(input(">> "))
            
            try:
                if ans == '0': self.setup_config_ui()
                elif ans == '1': self.schedule_management_ui()
                elif ans == '2': self.engine.check(silent=False)
                elif ans == '3':
                    if core_system:
                        print(f"{Colors.BLUE}[*] {t('gui_starting')}{Colors.RESET}")
                        try:
                            from src.gui_ui import launch_gui
                            launch_gui(core_system)
                        except ImportError:
                            print(f"{Colors.RED}[!] {t('gui_flask_missing')}{Colors.RESET}")
                            print(f"      pip install flask")
                    else:
                        print(f"{Colors.RED}[-] {t('gui_no_core')}{Colors.RESET}")
                elif ans.lower() in ['q', 'exit']: break
            except Exception as e:
                import traceback
                print(f"{Colors.RED}[FATAL ERROR] {e}{Colors.RESET}")
                traceback.print_exc()
