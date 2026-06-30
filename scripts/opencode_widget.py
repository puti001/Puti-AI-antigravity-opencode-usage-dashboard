# -*- coding: utf-8 -*-
import sys
import traceback
import os
import ctypes

def log_error(err):
    try:
        with open(r"C:\Users\clong\widget_error.log", "w", encoding="utf-8") as f:
            f.write(f"Error occurred at: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Message: {str(err)}\n\n")
            traceback.print_exc(file=f)
    except Exception:
        pass

try:
    import tkinter as tk
    from tkinter import ttk
    from tkinter import simpledialog
    import subprocess
    import re
    import threading
    import time
    import socket

    PORT = 18787

    # 1. 單例與開關機制
    def check_single_instance():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.5)
            s.connect(('127.0.0.1', PORT))
            s.sendall(b'TOGGLE')
            s.close()
            sys.exit(0)
        except (ConnectionRefusedError, socket.timeout):
            pass

    check_single_instance()

    # Windows 圓角與邊框
    def make_window_rounded(root_win):
        try:
            root_win.update()
            hwnd = ctypes.windll.user32.GetParent(root_win.winfo_id())
            if not hwnd:
                hwnd = root_win.winfo_id()
            DWMWA_WINDOW_CORNER_PREFERENCE = 33
            DWMWCP_ROUND = 2
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, DWMWA_WINDOW_CORNER_PREFERENCE, ctypes.byref(ctypes.c_int(DWMWCP_ROUND)), 4
            )
        except Exception:
            pass

    def get_opencode_stats():
        try:
            result = subprocess.run(
                ['powershell', '-Command', 'opencode stats'],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='ignore',
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            output = result.stdout
            
            sessions = re.search(r'Sessions\s+([\d,]+)', output)
            messages = re.search(r'Messages\s+([\d,]+)', output)
            days = re.search(r'Days\s+([\d,]+)', output)
            total_cost = re.search(r'Total Cost\s+\$([\d\.]+)', output)
            avg_cost = re.search(r'Avg Cost/Day\s+\$([\d\.]+)', output)
            
            return {
                'sessions': sessions.group(1) if sessions else '0',
                'messages': messages.group(1) if messages else '0',
                'days': days.group(1) if days else '0',
                'cost': total_cost.group(1) if total_cost else '0.00',
                'avg_cost': avg_cost.group(1) if avg_cost else '0.00'
            }
        except Exception as e:
            return {'error': str(e)}

    class FloatingDashboard:
        def __init__(self, root):
            self.root = root
            self.root.title("Puti-AI Antigravity Stats")
            
            self.root.overrideredirect(True)
            self.root.attributes("-alpha", 0.98)
            self.root.attributes("-topmost", True)
            
            # 配色
            self.bg_color = "#F3F4F6"
            self.card_color = "#FFFFFF"
            self.border_color = "#E5E7EB"
            self.txt_primary = "#111827"
            self.txt_secondary = "#4B5563"
            self.txt_muted = "#6B7280"
            self.accent_green = "#059669"
            self.accent_blue = "#2563EB"
            self.tab_active = "#FFFFFF"
            self.tab_inactive = "#E5E7EB"
            
            self.root.configure(bg=self.bg_color)
            
            self.width = 295
            self.height = 425
            self.root.geometry(f"{self.width}x{self.height}+300+300")
            
            make_window_rounded(self.root)
            
            # 右鍵選單
            self.menu = tk.Menu(self.root, tearoff=0, bg=self.card_color, fg=self.txt_primary)
            self.menu.add_command(label="設定初始額度 (Set Limits)", command=self.set_limits_dialog)
            self.menu.add_command(label="重新整理 (Refresh)", command=self.refresh_data)
            self.menu.add_command(label="隱藏/關閉 (Exit)", command=self.root.destroy)
            self.root.bind("<Button-3>", self.show_menu)
            
            # --- 數據 Baseline (完美同步你最新的截圖數字) ---
            self.gemini_5h_percent = 63
            self.gemini_5h_seconds = 3 * 3600 + 58 * 60  # 3小時58分
            self.gemini_wk_percent = 74
            self.gemini_wk_seconds = 3 * 24 * 3600 + 23 * 3600  # 3天23小時
            
            self.claude_5h_percent = 100
            self.claude_wk_percent = 100
            
            self.opencode_5h_percent = 0
            self.opencode_5h_seconds = 4 * 3600 + 59 * 60
            self.opencode_wk_percent = 0
            self.opencode_wk_seconds = 6 * 24 * 3600
            self.opencode_mo_percent = 46
            self.opencode_mo_seconds = 8 * 24 * 3600 + 20 * 3600
            
            self.local_sessions = "--"
            self.local_messages = "--"
            self.local_cost = "--"
            self.local_avg_cost = "--"
            
            self.last_sessions = 0
            self.last_messages = 0
            
            self.current_tab = "antigravity"
            
            self.edge_mode = ""
            self.resize_active = False
            self.drag_active = False
            self.EDGE_WIDTH = 8
            
            self.create_layout()
            self.refresh_data()
            
            self.bind_events_recursive(self.root)
            self.bind_double_clicks() # 綁定雙擊極速編輯事件
            
            self.running = True
            self.socket_thread = threading.Thread(target=self.listen_socket, daemon=True)
            self.socket_thread.start()
            
            self.tick()

        def bind_events_recursive(self, widget):
            widget_class = widget.winfo_class()
            if widget_class not in ("Button", "Menu"):
                widget.bind("<Motion>", self.detect_edge, add="+")
                widget.bind("<Button-1>", self.on_press, add="+")
                widget.bind("<B1-Motion>", self.on_drag, add="+")
                widget.bind("<ButtonRelease-1>", self.on_release, add="+")
            for child in widget.winfo_children():
                self.bind_events_recursive(child)

        def bind_double_clicks(self):
            # 讓使用者直接在進度圈上「雙擊左鍵」就能立刻編輯該額度百分比，極速便利！
            self.ring_gem_5h.bind("<Double-1>", lambda e: self.edit_single_limit("gemini_5h"))
            self.ring_gem_wk.bind("<Double-1>", lambda e: self.edit_single_limit("gemini_wk"))
            self.ring_op_mo.bind("<Double-1>", lambda e: self.edit_single_limit("opencode_mo"))

        def edit_single_limit(self, limit_type):
            title_map = {
                "gemini_5h": "Gemini 5小時額度 (%)",
                "gemini_wk": "Gemini 每週額度 (%)",
                "opencode_mo": "OpenCode 每月使用量 (%)"
            }
            curr_val = {
                "gemini_5h": self.gemini_5h_percent,
                "gemini_wk": self.gemini_wk_percent,
                "opencode_mo": self.opencode_mo_percent
            }[limit_type]
            
            val = simpledialog.askinteger(
                "極速設定額度", 
                f"請輸入最新的 {title_map[limit_type]}：", 
                initialvalue=curr_val, 
                minvalue=0, maxvalue=100, 
                parent=self.root
            )
            if val is not None:
                if limit_type == "gemini_5h":
                    self.gemini_5h_percent = val
                elif limit_type == "gemini_wk":
                    self.gemini_wk_percent = val
                elif limit_type == "opencode_mo":
                    self.opencode_mo_percent = val
                self.refresh_ui()

        def detect_edge(self, event):
            if self.resize_active or self.drag_active:
                return
            x = event.x_root - self.root.winfo_x()
            y = event.y_root - self.root.winfo_y()
            w = self.root.winfo_width()
            h = self.root.winfo_height()
            
            self.edge_mode = ""
            cursor = "arrow"
            
            near_l = x < self.EDGE_WIDTH
            near_r = x > w - self.EDGE_WIDTH
            near_t = y < self.EDGE_WIDTH
            near_b = y > h - self.EDGE_WIDTH
            
            if near_l and near_t:
                self.edge_mode = "nw"
                cursor = "size_nw_se"
            elif near_r and near_t:
                self.edge_mode = "ne"
                cursor = "size_ne_sw"
            elif near_l and near_b:
                self.edge_mode = "sw"
                cursor = "size_ne_sw"
            elif near_r and near_b:
                self.edge_mode = "se"
                cursor = "size_nw_se"
            elif near_l:
                self.edge_mode = "w"
                cursor = "size_we"
            elif near_r:
                self.edge_mode = "e"
                cursor = "size_we"
            elif near_t:
                self.edge_mode = "n"
                cursor = "size_ns"
            elif near_b:
                self.edge_mode = "s"
                cursor = "size_ns"
            
            self.root.config(cursor=cursor)

        def on_press(self, event):
            self.start_x = event.x_root
            self.start_y = event.y_root
            self.start_w = self.root.winfo_width()
            self.start_h = self.root.winfo_height()
            self.start_pos_x = self.root.winfo_x()
            self.start_pos_y = self.root.winfo_y()
            
            if self.edge_mode != "":
                self.resize_active = True
                self.drag_active = False
            else:
                self.resize_active = False
                self.drag_active = True
                self.drag_offset_x = event.x_root - self.start_pos_x
                self.drag_offset_y = event.y_root - self.start_pos_y

        def on_drag(self, event):
            if self.resize_active:
                dx = event.x_root - self.start_x
                dy = event.y_root - self.start_y
                new_w = self.start_w
                new_h = self.start_h
                new_x = self.start_pos_x
                new_y = self.start_pos_y
                min_w, min_h = 260, 320
                
                if "e" in self.edge_mode:
                    new_w = max(min_w, self.start_w + dx)
                elif "w" in self.edge_mode:
                    possible_w = self.start_w - dx
                    if possible_w >= min_w:
                        new_w = possible_w
                        new_x = self.start_pos_x + dx
                
                if "s" in self.edge_mode:
                    new_h = max(min_h, self.start_h + dy)
                elif "n" in self.edge_mode:
                    possible_h = self.start_h - dy
                    if possible_h >= min_h:
                        new_h = possible_h
                        new_y = self.start_pos_y + dy
                
                self.root.geometry(f"{new_w}x{new_h}+{new_x}+{new_y}")
                self.refresh_ui()
            elif self.drag_active:
                x = event.x_root - self.drag_offset_x
                y = event.y_root - self.drag_offset_y
                self.root.geometry(f"+{x}+{y}")

        def on_release(self, event):
            self.resize_active = False
            self.drag_active = False
            self.detect_edge(event)

        def create_layout(self):
            self.nav_frame = tk.Frame(self.root, bg=self.bg_color)
            self.nav_frame.pack(fill="x", padx=12, pady=(12, 4))
            
            self.tabs_frame = tk.Frame(self.nav_frame, bg=self.bg_color)
            self.tabs_frame.pack(side="left")
            
            self.tab_anti_btn = tk.Label(self.tabs_frame, text="Antigravity", font=("Microsoft JhengHei", 9, "bold"), 
                                         bg=self.tab_active, fg=self.txt_primary, padx=12, pady=4, cursor="hand2", relief="flat")
            self.tab_anti_btn.pack(side="left")
            self.tab_anti_btn.bind("<Button-1>", lambda e: self.switch_tab("antigravity"))
            
            self.tab_open_btn = tk.Label(self.tabs_frame, text="OpenCode", font=("Microsoft JhengHei", 9, "bold"), 
                                         bg=self.tab_inactive, fg=self.txt_secondary, padx=12, pady=4, cursor="hand2", relief="flat")
            self.tab_open_btn.pack(side="left", padx=(4, 0))
            self.tab_open_btn.bind("<Button-1>", lambda e: self.switch_tab("opencode"))
            
            self.btns_frame = tk.Frame(self.nav_frame, bg=self.bg_color)
            self.btns_frame.pack(side="right")
            
            self.refresh_btn = tk.Label(self.btns_frame, text="🔄", font=("Arial", 11), bg=self.bg_color, fg=self.txt_secondary, cursor="hand2")
            self.refresh_btn.pack(side="left", padx=(0, 10))
            self.refresh_btn.bind("<Button-1>", lambda e: self.manual_refresh())
            
            close_btn = tk.Label(self.btns_frame, text="×", font=("Arial", 16), bg=self.bg_color, fg=self.txt_secondary, cursor="hand2")
            close_btn.pack(side="left")
            close_btn.bind("<Button-1>", lambda e: self.root.destroy())
            
            self.content_frame = tk.Frame(self.root, bg=self.bg_color)
            self.content_frame.pack(fill="both", expand=True, padx=12, pady=4)
            
            self.init_antigravity_view()
            self.init_opencode_view()
            self.show_current_view()
            
            self.bottom_frame = tk.Frame(self.root, bg=self.bg_color)
            self.bottom_frame.pack(side="bottom", fill="x", pady=(0, 4))
            self.status_lbl = tk.Label(self.bottom_frame, text="更新 剛才", font=("Microsoft JhengHei", 8), bg=self.bg_color, fg=self.txt_secondary)
            self.status_lbl.pack(side="left", padx=14, pady=2)

        def init_antigravity_view(self):
            self.anti_view = tk.Frame(self.content_frame, bg=self.bg_color)
            
            # Gemini Models
            self.card_gemini = tk.Frame(self.anti_view, bg=self.card_color, highlightbackground=self.border_color, highlightthickness=1)
            self.card_gemini.pack(fill="x", pady=4)
            
            self.lbl_gem_title = tk.Label(self.card_gemini, text="Puti-AI Gemini Models", font=("Microsoft JhengHei", 9, "bold"), bg=self.card_color, fg=self.txt_secondary)
            self.lbl_gem_title.pack(anchor="w", padx=12, pady=(6, 2))
            
            frame_gem_rings = tk.Frame(self.card_gemini, bg=self.card_color)
            frame_gem_rings.pack(fill="x", padx=10, pady=(2, 6))
            
            self.frame_gem_5h = tk.Frame(frame_gem_rings, bg=self.card_color)
            self.frame_gem_5h.pack(side="left", expand=True, fill="both")
            self.ring_gem_5h = tk.Canvas(self.frame_gem_5h, bg=self.card_color, highlightthickness=0)
            self.ring_gem_5h.pack(pady=2)
            self.lbl_gem_5h_txt = tk.Label(self.frame_gem_5h, text="5 小時額度\n--", font=("Microsoft JhengHei", 7), bg=self.card_color, fg=self.txt_secondary)
            self.lbl_gem_5h_txt.pack()
            
            self.frame_gem_wk = tk.Frame(frame_gem_rings, bg=self.card_color)
            self.frame_gem_wk.pack(side="right", expand=True, fill="both")
            self.ring_gem_wk = tk.Canvas(self.frame_gem_wk, bg=self.card_color, highlightthickness=0)
            self.ring_gem_wk.pack(pady=2)
            self.lbl_gem_wk_txt = tk.Label(self.frame_gem_wk, text="每週額度\n--", font=("Microsoft JhengHei", 7), bg=self.card_color, fg=self.txt_secondary)
            self.lbl_gem_wk_txt.pack()
            
            # Claude Models
            self.card_claude = tk.Frame(self.anti_view, bg=self.card_color, highlightbackground=self.border_color, highlightthickness=1)
            self.card_claude.pack(fill="x", pady=4)
            
            self.lbl_cld_title = tk.Label(self.card_claude, text="Puti-AI Claude & GPT", font=("Microsoft JhengHei", 9, "bold"), bg=self.card_color, fg=self.txt_secondary)
            self.lbl_cld_title.pack(anchor="w", padx=12, pady=(6, 2))
            
            frame_cld_rings = tk.Frame(self.card_claude, bg=self.card_color)
            frame_cld_rings.pack(fill="x", padx=10, pady=(2, 6))
            
            self.frame_cld_5h = tk.Frame(frame_cld_rings, bg=self.card_color)
            self.frame_cld_5h.pack(side="left", expand=True, fill="both")
            self.ring_cld_5h = tk.Canvas(self.frame_cld_5h, bg=self.card_color, highlightthickness=0)
            self.ring_cld_5h.pack(pady=2)
            self.lbl_cld_5h_txt = tk.Label(self.frame_cld_5h, text="5 小時限額\n滿額", font=("Microsoft JhengHei", 7), bg=self.card_color, fg=self.txt_secondary)
            self.lbl_cld_5h_txt.pack()
            
            self.frame_cld_wk = tk.Frame(frame_cld_rings, bg=self.card_color)
            self.frame_cld_wk.pack(side="right", expand=True, fill="both")
            self.ring_cld_wk = tk.Canvas(self.frame_cld_wk, bg=self.card_color, highlightthickness=0)
            self.ring_cld_wk.pack(pady=2)
            self.lbl_cld_wk_txt = tk.Label(self.frame_cld_wk, text="每週限額\n滿額", font=("Microsoft JhengHei", 7), bg=self.card_color, fg=self.txt_secondary)
            self.lbl_cld_wk_txt.pack()

        def init_opencode_view(self):
            self.open_view = tk.Frame(self.content_frame, bg=self.bg_color)
            
            # OpenCode Go
            self.card_op_go = tk.Frame(self.open_view, bg=self.card_color, highlightbackground=self.border_color, highlightthickness=1)
            self.card_op_go.pack(fill="x", pady=4)
            
            self.lbl_opg_title = tk.Label(self.card_op_go, text="Puti-AI OpenCode Go", font=("Microsoft JhengHei", 9, "bold"), bg=self.card_color, fg=self.txt_secondary)
            self.lbl_opg_title.pack(anchor="w", padx=12, pady=(6, 2))
            
            frame_op_rings = tk.Frame(self.card_op_go, bg=self.card_color)
            frame_op_rings.pack(fill="x", padx=6, pady=(2, 6))
            
            self.frame_op_5h = tk.Frame(frame_op_rings, bg=self.card_color)
            self.frame_op_5h.pack(side="left", expand=True, fill="both")
            self.ring_op_5h = tk.Canvas(self.frame_op_5h, bg=self.card_color, highlightthickness=0)
            self.ring_op_5h.pack(pady=2)
            self.lbl_op_5h_txt = tk.Label(self.frame_op_5h, text="滾動使用\n--", font=("Microsoft JhengHei", 7), bg=self.card_color, fg=self.txt_secondary)
            self.lbl_op_5h_txt.pack()
            
            self.frame_op_wk = tk.Frame(frame_op_rings, bg=self.card_color)
            self.frame_op_wk.pack(side="left", expand=True, fill="both")
            self.ring_op_wk = tk.Canvas(self.frame_op_wk, bg=self.card_color, highlightthickness=0)
            self.ring_op_wk.pack(pady=2)
            self.lbl_op_wk_txt = tk.Label(self.frame_op_wk, text="每週使用\n--", font=("Microsoft JhengHei", 7), bg=self.card_color, fg=self.txt_secondary)
            self.lbl_op_wk_txt.pack()
            
            self.frame_op_mo = tk.Frame(frame_op_rings, bg=self.card_color)
            self.frame_op_mo.pack(side="left", expand=True, fill="both")
            self.ring_op_mo = tk.Canvas(self.frame_op_mo, bg=self.card_color, highlightthickness=0)
            self.ring_op_mo.pack(pady=2)
            self.lbl_op_mo_txt = tk.Label(self.frame_op_mo, text="每月使用\n--", font=("Microsoft JhengHei", 7), bg=self.card_color, fg=self.txt_secondary)
            self.lbl_op_mo_txt.pack()
            
            # 本地統計
            self.card_op_stats = tk.Frame(self.open_view, bg=self.card_color, highlightbackground=self.border_color, highlightthickness=1)
            self.card_op_stats.pack(fill="x", pady=4)
            
            self.lbl_ops_title = tk.Label(self.card_op_stats, text="本地 Session 累計", font=("Microsoft JhengHei", 10, "bold"), bg=self.card_color, fg=self.txt_primary)
            self.lbl_ops_title.pack(anchor="w", padx=14, pady=(6, 2))
            
            self.lbl_ses = self.create_stats_row(self.card_op_stats, "🗂️ Sessions / Messages", "-- / --")
            self.lbl_cost = self.create_stats_row(self.card_op_stats, "💰 Total Cost (累計花費)", "$--")
            
            self.frame_toggle = tk.Frame(self.card_op_stats, bg=self.card_color)
            self.frame_toggle.pack(fill="x", padx=14, pady=(4, 6))
            self.lbl_toggle_txt = tk.Label(self.frame_toggle, text="達到限制後使用可用餘額", font=("Microsoft JhengHei", 9), bg=self.card_color, fg=self.txt_secondary)
            self.lbl_toggle_txt.pack(side="left")
            
            self.toggle_canvas = tk.Canvas(self.frame_toggle, bg=self.card_color, width=32, height=18, highlightthickness=0)
            self.toggle_canvas.pack(side="right")
            self.draw_toggle_button()

        def create_stats_row(self, parent, label_text, val_text):
            frame = tk.Frame(parent, bg=self.card_color)
            frame.pack(fill="x", padx=14, pady=2)
            lbl = tk.Label(frame, text=label_text, font=("Microsoft JhengHei", 9), bg=self.card_color, fg=self.txt_secondary)
            lbl.pack(side="left")
            val = tk.Label(frame, text=val_text, font=("Consolas", 9, "bold"), bg=self.card_color, fg=self.txt_primary)
            val.pack(side="right")
            return val

        def draw_toggle_button(self):
            self.toggle_canvas.delete("all")
            self.toggle_canvas.create_oval(2, 2, 16, 16, fill="#059669", outline="")
            self.toggle_canvas.create_oval(14, 2, 28, 16, fill="#059669", outline="")
            self.toggle_canvas.create_rectangle(8, 2, 22, 16, fill="#059669", outline="")
            self.toggle_canvas.create_oval(14, 3, 27, 15, fill="#FFFFFF", outline="")

        def show_current_view(self):
            if self.current_tab == "antigravity":
                self.open_view.pack_forget()
                self.anti_view.pack(fill="both", expand=True)
                self.tab_anti_btn.configure(bg=self.tab_active, fg=self.txt_primary)
                self.tab_open_btn.configure(bg=self.tab_inactive, fg=self.txt_secondary)
            else:
                self.anti_view.pack_forget()
                self.open_view.pack(fill="both", expand=True)
                self.tab_anti_btn.configure(bg=self.tab_inactive, fg=self.txt_secondary)
                self.tab_open_btn.configure(bg=self.tab_active, fg=self.txt_primary)

        def switch_tab(self, tab_name):
            self.current_tab = tab_name
            self.show_current_view()
            self.refresh_ui()

        def format_time(self, seconds):
            if seconds <= 0:
                return "--"
            h = seconds // 3600
            m = (seconds % 3600) // 60
            if h >= 24:
                d = h // 24
                h_rem = h % 24
                return f"{d}天 {h_rem}時" if h_rem > 0 else f"{d}天"
            return f"{h}時 {m}分" if h > 0 else f"{m}分"

        def draw_progress_ring(self, canvas, percent, color, scale_factor=1.0):
            canvas.delete("all")
            w = max(45, int(60 * scale_factor))
            canvas.configure(width=w, height=w)
            
            margin = 5
            r = w - margin
            pen_w = max(3, int(5 * scale_factor))
            
            canvas.create_arc(margin, margin, r, r, start=0, extent=359.9, outline="#E5E7EB", width=pen_w, style="arc")
            
            if percent >= 100:
                extent_val = -359.99
            else:
                extent_val = -3.6 * percent
                
            canvas.create_arc(margin, margin, r, r, start=90, extent=extent_val, outline=color, width=pen_w, style="arc")
            
            num_y = int(w * 0.40)
            pct_y = int(w * 0.72)
            
            num_font_size = int(16 * scale_factor)
            pct_font_size = int(8 * scale_factor)
            
            canvas.create_text(w//2, num_y, text=str(percent), font=("Segoe UI", num_font_size, "bold"), fill=self.txt_primary)
            canvas.create_text(w//2, pct_y, text="%", font=("Segoe UI", pct_font_size, "bold"), fill=self.txt_secondary)

        def refresh_ui(self):
            scale_factor = self.root.winfo_width() / 295.0
            
            font_title = ("Microsoft JhengHei", int(10 * scale_factor), "bold")
            font_txt = ("Microsoft JhengHei", int(7 * scale_factor))
            font_bold_title = ("Microsoft JhengHei", int(10 * scale_factor), "bold")
            
            self.lbl_gem_title.configure(font=font_title)
            self.lbl_cld_title.configure(font=font_title)
            self.lbl_opg_title.configure(font=font_title)
            self.lbl_ops_title.configure(font=font_bold_title)
            
            self.lbl_gem_5h_txt.configure(font=font_txt)
            self.lbl_gem_wk_txt.configure(font=font_txt)
            self.lbl_cld_5h_txt.configure(font=font_txt)
            self.lbl_cld_wk_txt.configure(font=font_txt)
            
            self.lbl_op_5h_txt.configure(font=font_txt)
            self.lbl_op_wk_txt.configure(font=font_txt)
            self.lbl_op_mo_txt.configure(font=font_txt)
            
            self.lbl_toggle_txt.configure(font=font_txt)
            
            # Gemini Models
            self.draw_progress_ring(self.ring_gem_5h, self.gemini_5h_percent, self.accent_green, scale_factor)
            self.lbl_gem_5h_txt.configure(text=f"5 小時額度\n重置 {self.format_time(self.gemini_5h_seconds)}")
            
            self.draw_progress_ring(self.ring_gem_wk, self.gemini_wk_percent, self.accent_green, scale_factor)
            self.lbl_gem_wk_txt.configure(text=f"每週額度\n重置 {self.format_time(self.gemini_wk_seconds)}")
            
            # Claude Models
            self.draw_progress_ring(self.ring_cld_5h, self.claude_5h_percent, self.accent_green, scale_factor)
            self.draw_progress_ring(self.ring_cld_wk, self.claude_wk_percent, self.accent_green, scale_factor)

            # OpenCode Go
            self.draw_progress_ring(self.ring_op_5h, self.opencode_5h_percent, self.accent_blue, scale_factor)
            self.lbl_op_5h_txt.configure(text=f"滾動使用\n重置 {self.format_time(self.opencode_5h_seconds)}")
            
            self.draw_progress_ring(self.ring_op_wk, self.opencode_wk_percent, self.accent_blue, scale_factor)
            self.lbl_op_wk_txt.configure(text=f"每週使用\n重置 {self.format_time(self.opencode_wk_seconds)}")
            
            self.draw_progress_ring(self.ring_op_mo, self.opencode_mo_percent, self.accent_blue, scale_factor)
            self.lbl_op_mo_txt.configure(text=f"每月使用\n重置 {self.format_time(self.opencode_mo_seconds)}")
            
            self.lbl_ses.configure(text=f"{self.local_sessions} 會話 / {self.local_messages} 訊息", font=("Consolas", int(9 * scale_factor), "bold"))
            self.lbl_cost.configure(text=f"${self.local_cost}", font=("Consolas", int(9 * scale_factor), "bold"))

        def manual_refresh(self):
            self.refresh_btn.configure(fg=self.accent_blue)
            self.status_lbl.configure(text="正在更新...")
            self.refresh_data()
            self.root.after(800, lambda: self.refresh_btn.configure(fg=self.txt_secondary))

        def set_limits_dialog(self):
            val = simpledialog.askstring(
                "手動設定額度 (Set Limits)", 
                "請輸入您後台看到的最新百分比，以逗號分隔\n格式: Gemini5H, GeminiWk, OpenCodeMo\n(例如: 63, 74, 46)", 
                parent=self.root
            )
            if val:
                try:
                    parts = [int(p.strip()) for p in val.split(',')]
                    if len(parts) >= 3:
                        self.gemini_5h_percent = parts[0]
                        self.gemini_wk_percent = parts[1]
                        self.opencode_mo_percent = parts[2]
                        self.refresh_ui()
                except Exception:
                    pass

        def refresh_data(self):
            def task():
                data = get_opencode_stats()
                if 'error' in data:
                    return
                
                def update_ui():
                    self.local_sessions = data['sessions']
                    self.local_messages = data['messages']
                    self.local_cost = data['cost']
                    self.local_avg_cost = data['avg_cost']
                    
                    s_count = int(data['sessions'].replace(',', ''))
                    m_count = int(data['messages'].replace(',', ''))
                    
                    if self.last_sessions > 0 and s_count > self.last_sessions:
                        diff_s = s_count - self.last_sessions
                        self.gemini_5h_percent = min(100, self.gemini_5h_percent + diff_s * 3)
                        self.gemini_wk_percent = min(100, self.gemini_wk_percent + diff_s * 1)
                        self.opencode_5h_percent = min(100, self.opencode_5h_percent + diff_s * 2)
                        
                    self.last_sessions = s_count
                    self.last_messages = m_count
                    
                    self.refresh_ui()
                    self.status_lbl.configure(text="更新 剛才")
                    
                self.root.after(0, update_ui)
                
            threading.Thread(target=task, daemon=True).start()

        def tick(self):
            if self.gemini_5h_seconds > 0:
                self.gemini_5h_seconds -= 1
            if self.gemini_wk_seconds > 0:
                self.gemini_wk_seconds -= 1
            if self.opencode_5h_seconds > 0:
                self.opencode_5h_seconds -= 1
            if self.opencode_wk_seconds > 0:
                self.opencode_wk_seconds -= 1
            if self.opencode_mo_seconds > 0:
                self.opencode_mo_seconds -= 1
                
            if time.time() % 30 < 1:
                self.refresh_data()
                
            self.refresh_ui()
            
            if self.running:
                self.root.after(1000, self.tick)

        def listen_socket(self):
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.bind(('127.0.0.1', PORT))
            server.listen(1)
            while self.running:
                try:
                    conn, addr = server.accept()
                    data = conn.recv(1024)
                    if data == b'TOGGLE':
                        self.running = False
                        self.root.after(0, self.root.destroy)
                        break
                    conn.close()
                except Exception:
                    break

        def show_menu(self, event):
            self.menu.post(event.x_root, event.y_root)

    root = tk.Tk()
    app = FloatingDashboard(root)
    root.mainloop()
except Exception as e:
    log_error(e)
