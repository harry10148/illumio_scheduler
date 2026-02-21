"""
Illumio Rule Scheduler — i18n (Internationalisation)
English is the default language. Supports: en, zh-TW
"""

# Current language (default: English)
_current_lang = 'en'

def set_lang(lang_code):
    global _current_lang
    if lang_code in _STRINGS:
        _current_lang = lang_code
    else:
        _current_lang = 'en'

def get_lang():
    return _current_lang

def t(key):
    """Translate a key to the current language, fallback to English"""
    return _STRINGS.get(_current_lang, {}).get(key, _STRINGS['en'].get(key, key))

# ==========================================
# String Tables
# ==========================================
_STRINGS = {
    'en': {
        # Main Menu
        'app_title': 'Illumio Scheduler',
        'menu_version': 'v1.0.0',
        'menu_config': 'Settings',
        'menu_schedule': 'Schedule Management (Browse/List/Edit/Delete)',
        'menu_check': 'Run Check Now',
        'menu_webgui': 'Open Web GUI',
        'menu_lang': 'Language',
        'menu_quit': 'Quit',
        
        # Schedule Management Sub-menu
        'sch_mgmt_title': 'Schedule Management',
        'sch_hint': 'Hint',
        'sch_hint_rs': 'RuleSet schedule',
        'sch_hint_child': 'Child rule only',
        'sch_browse': 'Browse & Add schedule',
        'sch_list': 'List scheduled items (Grouped View)',
        'sch_edit': 'Edit schedule',
        'sch_delete': 'Delete schedule',
        'sch_back': 'Back to main menu',
        
        # Browse
        'browse_title': 'Browse & Add Schedule (q to return)',
        'browse_prompt': 'Enter ID or keyword (Enter for all):',
        'browse_loading': 'Loading all rulesets...',
        'browse_locate': 'Locating ID:',
        'browse_not_found': 'ID not found, searching by name...',
        'browse_no_result': 'No results found.',
        'browse_selected': 'Selected:',
        'browse_opt_rs': 'Schedule entire RuleSet',
        'browse_opt_rule': 'Browse and select a single Rule',
        'browse_action': 'Action (q=back) >',
        'browse_no_rules': 'No rules in this RuleSet.',
        
        # Ruleset/Rule Table Headers
        'hdr_no': 'No',
        'hdr_sch': 'Sch',
        'hdr_id': 'ID',
        'hdr_status': 'Status',
        'hdr_rules': 'Rules',
        'hdr_name': 'Name',
        'hdr_note': 'Note (Desc)',
        'hdr_source': 'Source',
        'hdr_dest': 'Dest',
        'hdr_service': 'Service',
        
        # Schedule Config
        'sch_target': 'Target',
        'sch_type_recurring': 'Schedule (recurring weekly)',
        'sch_type_expire': 'Expiration (auto-disable after time)',
        'sch_current': 'Current',
        'sch_action_label': 'Action',
        'sch_action_enable': 'Enable (ON during window)',
        'sch_action_disable': 'Disable (OFF during window)',
        'sch_days_prompt': 'Days (Mon,Tue...) [Enter=Everyday]:',
        'sch_start_prompt': 'Start (HH:MM) [q=back]:',
        'sch_end_prompt': 'End (HH:MM) [q=back]:',
        'sch_expire_prompt': 'Expire at (YYYY-MM-DD HH:MM) [q=back]:',
        'sch_expire_note': 'Format: YYYY-MM-DD HH:MM (auto-disable & remove)',
        'sch_time_error': 'Invalid time format.',
        'sch_time_invalid': 'Time error: Format must be HH:MM and End time cannot equal Start time.',
        'sch_time_format_hint': '(24H e.g. 09:00)',
        'sch_tag_recurring': 'Schedule',
        'sch_tag_expire': 'Expiration',
        'sch_saved': 'Schedule saved and provisioned!',
        'sch_updated': 'Schedule updated!',
        'sch_exists_warn': 'Warning: This item already has a schedule. Will overwrite.',
        'sch_confirm': 'Confirm? (y/n):',
        'sch_keep_enter': 'Press Enter to keep current value',
        
        # Grouped List
        'list_no_schedule': 'No schedules configured.',
        'list_type': 'Type',
        'list_hierarchy': 'Hierarchy & Note (Desc)',
        'list_mode': 'Mode/Action',
        'list_timing': 'Time/Expiration',
        'list_deleted': '[Deleted] (Removed from PCE)',
        'list_conn_fail': '(Connection failed)',
        'list_rule_deleted': '[Deleted] (Rule invalid)',
        
        # Actions
        'action_enable_in_window': 'Enable in window',
        'action_disable_in_window': 'Disable in window',
        'action_everyday': 'Everyday',
        
        # Edit/Delete
        'edit_prompt': 'Enter ID to Edit (q=back):',
        'edit_not_found': 'No schedule found for this ID.',
        'edit_editing': 'Editing schedule:',
        'delete_prompt': 'Enter ID to Delete (q=back):',
        'delete_confirm': 'Confirm delete? (y/n):',
        'delete_target': 'Target:',
        'delete_cleaning': 'Cleaning up note...',
        'delete_done': 'Schedule deleted.',
        'delete_not_found': 'ID not found.',
        
        # Config
        'config_title': 'API Configuration (q to cancel)',
        'config_saved': 'Configuration saved.',
        'config_not_ready': 'API not configured. Please configure first.',
        
        # Check
        'check_checking': 'Checking schedules...',
        'check_expired': 'EXPIRED',
        'check_expired_msg': 'has expired.',
        'check_toggle': 'Toggle status ->',
        'check_success': 'Provisioned successfully.',
        'check_cleanup': 'expired schedules removed.',
        
        # Language
        'lang_prompt': 'Select language:',
        'lang_en': 'English',
        'lang_zh': 'Traditional Chinese (繁體中文)',
        'lang_set': 'Language set to:',
        
        # Extended Config Labels
        'cfg_api_title': 'API Configuration',
        'cfg_alert_title': 'Alert Channels & Languages',
        'cfg_ssl_title': 'SSL Certificate Verification',
        'cfg_smtp_title': 'SMTP Settings',
        'cfg_ssl_current': 'Current',
        'cfg_ssl_ignore': 'Ignore',
        'cfg_ssl_verify': 'Verify',
        'cfg_auth_on': 'ON',
        'cfg_auth_off': 'OFF',
        'cfg_alerts_label': 'Alerts',
        'cfg_alert_mail': 'Mail',
        
        # Web GUI
        'gui_starting': 'Starting Web GUI...',
        'gui_flask_missing': 'Web GUI requires Flask. Install with:',
        'gui_no_core': 'Cannot start GUI (core_system not passed)',
        
        # General
        'select_prompt': 'Select',
        'back': 'Back',
        'next_page': 'Next',
        'prev_page': 'Prev',
        'invalid_input': 'Invalid input.',
        'invalid_number': 'Invalid number.',
    },
    
    'zh': {
        # Main Menu
        'app_title': 'Illumio Scheduler',
        'menu_version': 'v1.0.0',
        'menu_config': '系統設定',
        'menu_schedule': '排程管理 (瀏覽/列表/修改/刪除)',
        'menu_check': '立即檢查',
        'menu_webgui': '開啟 Web GUI',
        'menu_lang': '語系',
        'menu_quit': '離開',
        
        # Schedule Management Sub-menu
        'sch_mgmt_title': '排程管理',
        'sch_hint': '提示',
        'sch_hint_rs': '規則集排程',
        'sch_hint_child': '僅子規則排程',
        'sch_browse': '瀏覽與新增排程',
        'sch_list': '列表已排程項目 (Grouped View)',
        'sch_edit': '修改排程',
        'sch_delete': '刪除排程',
        'sch_back': '返回主選單',
        
        # Browse
        'browse_title': '瀏覽與新增排程 (輸入 q 返回)',
        'browse_prompt': '請輸入 ID 或 關鍵字 (直接按 Enter 瀏覽全部):',
        'browse_loading': '讀取全部清單...',
        'browse_locate': '定位 ID:',
        'browse_not_found': '找不到 ID，轉為搜尋名稱...',
        'browse_no_result': '找不到結果。',
        'browse_selected': '已選擇:',
        'browse_opt_rs': '排程控制「整個規則集」',
        'browse_opt_rule': '瀏覽並選擇「單條規則」',
        'browse_action': '動作 (q=返回) >',
        'browse_no_rules': '此規則集內無規則。',
        
        # Ruleset/Rule Table Headers
        'hdr_no': 'No',
        'hdr_sch': 'Sch',
        'hdr_id': 'ID',
        'hdr_status': 'Status',
        'hdr_rules': 'Rules',
        'hdr_name': 'Name',
        'hdr_note': 'Note (Desc)',
        'hdr_source': 'Source',
        'hdr_dest': 'Dest',
        'hdr_service': 'Service',
        
        # Schedule Config
        'sch_target': '目標',
        'sch_type_recurring': 'Schedule (週期性排程)',
        'sch_type_expire': 'Expiration (時間到自動關閉並刪除排程)',
        'sch_current': '目前',
        'sch_action_label': '行為',
        'sch_action_enable': '啟動 (時間內開啟)',
        'sch_action_disable': '關閉 (時間內關閉)',
        'sch_days_prompt': '星期 (Mon,Tue...) [Enter=每天]:',
        'sch_start_prompt': '開始 (HH:MM) [q=返回]:',
        'sch_end_prompt': '結束 (HH:MM) [q=返回]:',
        'sch_expire_prompt': '過期時間 (YYYY-MM-DD HH:MM) [q=返回]:',
        'sch_expire_note': '格式: YYYY-MM-DD HH:MM (時間到自動關閉並刪除)',
        'sch_time_error': '時間格式錯誤。',
        'sch_time_invalid': '時間錯誤：格式必須為 24 小時制 (HH:MM)，且起始與結束時間不可相同。',
        'sch_time_format_hint': '(24小時制 例如 09:00)',
        'sch_tag_recurring': '排程',
        'sch_tag_expire': '有效期限',
        'sch_saved': '排程已儲存並寫入 Note!',
        'sch_updated': '排程已更新!',
        'sch_exists_warn': '警告: 此規則已存在排程設定。將覆蓋舊設定。',
        'sch_confirm': '確認? (y/n):',
        'sch_keep_enter': '直接按 Enter 保留現有值',
        
        # Grouped List
        'list_no_schedule': '目前沒有設定排程。',
        'list_type': 'Type',
        'list_hierarchy': 'Hierarchy & Note (Desc)',
        'list_mode': 'Mode/Action',
        'list_timing': 'Time/Expiration',
        'list_deleted': '[已刪除] (規則已從 PCE 移除)',
        'list_conn_fail': '(連線失敗)',
        'list_rule_deleted': '[已刪除] (規則失效)',
        
        # Actions
        'action_enable_in_window': '時段內啟動',
        'action_disable_in_window': '時段內關閉',
        'action_everyday': '每天',
        
        # Edit/Delete
        'edit_prompt': '輸入要修改的 ID (q=返回):',
        'edit_not_found': '找不到該 ID 的排程。',
        'edit_editing': '修改排程:',
        'delete_prompt': '輸入要刪除的 ID (q=返回):',
        'delete_confirm': '確定刪除? (y/n):',
        'delete_target': '目標:',
        'delete_cleaning': '嘗試清除 Note 標記...',
        'delete_done': '排程已刪除。',
        'delete_not_found': '找不到該 ID。',
        
        # Config
        'config_title': 'API 設定 (輸入 q 取消)',
        'config_saved': '設定已儲存。',
        'config_not_ready': '尚未設定 API，請先執行設定。',
        
        # Check
        'check_checking': '檢查排程...',
        'check_expired': '已過期',
        'check_expired_msg': '已過期。',
        'check_toggle': '切換狀態 ->',
        'check_success': '已提交發布',
        'check_cleanup': '筆過期排程已移除。',
        
        # Language
        'lang_prompt': '選擇語系:',
        'lang_en': 'English',
        'lang_zh': '繁體中文 (Traditional Chinese)',
        'lang_set': '語系已切換為:',
        
        # Extended Config Labels
        'cfg_api_title': 'API 連線設定',
        'cfg_alert_title': '警報通道與語系設定',
        'cfg_ssl_title': 'SSL 憑證驗證',
        'cfg_smtp_title': 'SMTP 伺服器設定',
        'cfg_ssl_current': '目前狀態',
        'cfg_ssl_ignore': '忽略 (Ignore)',
        'cfg_ssl_verify': '驗證 (Verify)',
        'cfg_auth_on': '啟用',
        'cfg_auth_off': '停用',
        'cfg_alerts_label': '告警通知',
        'cfg_alert_mail': '郵件',
        
        # Web GUI
        'gui_starting': '啟動 Web GUI...',
        'gui_flask_missing': 'Web GUI 需要 Flask。請先安裝：',
        'gui_no_core': '無法啟動 GUI（core_system 未傳入）',
        
        # General
        'select_prompt': '請選擇',
        'back': '返回',
        'next_page': '下一頁',
        'prev_page': '上一頁',
        'invalid_input': '輸入無效。',
        'invalid_number': '序號無效。',
    }
}
