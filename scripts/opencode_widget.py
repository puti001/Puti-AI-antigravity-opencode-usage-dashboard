# -*- coding: utf-8 -*-
import sys, traceback, os, ctypes

def log_error(err):
    try:
        import time
        home = os.path.expanduser("~")
        with open(os.path.join(home, "widget_error.log"), "w", encoding="utf-8") as f:
            f.write(f"Error at: {time.strftime('%Y-%m-%d %H:%M:%S')}\n{str(err)}\n\n")
            traceback.print_exc(file=f)
    except Exception:
        pass

try:
    import tkinter as tk
    import sqlite3, json, subprocess, re, threading, time, socket, struct
    import urllib.request
    from datetime import datetime, timezone

    PORT_SINGLETON = 18787

    # ─── 單例 ───────────────────────────────────────────────
    def check_single_instance():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.5)
            s.connect(('127.0.0.1', PORT_SINGLETON))
            s.sendall(b'TOGGLE')
            s.close()
            sys.exit(0)
        except (ConnectionRefusedError, socket.timeout):
            pass

    check_single_instance()

    # ─── Windows 圓角 ────────────────────────────────────────
    def make_window_rounded(win):
        try:
            win.update()
            hwnd = ctypes.windll.user32.GetParent(win.winfo_id()) or win.winfo_id()
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, 33, ctypes.byref(ctypes.c_int(2)), 4)
        except Exception:
            pass

    # ─── 動態抓 Antigravity Language Server Port & CSRF ──────
    def get_antigravity_port_and_csrf():
        log_path = os.path.expanduser(
            "~\\AppData\\Roaming\\Antigravity\\logs\\language_server.log")
        http_port = None
        try:
            with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            matches = re.findall(
                r'Language server listening on random port at (\d+) for HTTP', content)
            if matches:
                http_port = int(matches[-1])
        except Exception:
            pass

        if not http_port:
            return None, None

        try:
            req = urllib.request.Request(
                f"http://localhost:{http_port}/",
                headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=3) as r:
                html = r.read().decode("utf-8", errors="ignore")
            m = re.search(r'"csrfToken"\s*:\s*"([^"]+)"', html)
            if m:
                return http_port, m.group(1)
        except Exception:
            pass
        return http_port, None

    # ─── 呼叫 Antigravity gRPC-Web API ──────────────────────
    def grpc_call(port, csrf, method, body="{}"):
        b = body.encode()
        grpc_body = b"\x00" + struct.pack(">I", len(b)) + b
        req = urllib.request.Request(
            f"http://localhost:{port}/exa.language_server_pb.LanguageServerService/{method}",
            data=grpc_body,
            method="POST",
            headers={
                "Content-Type": "application/grpc-web+json",
                "X-Grpc-Web": "1",
                "x-codeium-csrf-token": csrf,
                "x-user-agent": "CONNECT_ES_USER_AGENT",
            }
        )
        with urllib.request.urlopen(req, timeout=8) as r:
            raw = r.read()
        if raw and len(raw) > 5:
            fl = struct.unpack(">I", raw[1:5])[0]
            payload = raw[5:5 + fl]
            return json.loads(payload.decode("utf-8", errors="replace"))
        return {}

    # ─── 抓 Antigravity Quota ────────────────────────────────
    def get_antigravity_quota():
        port, csrf = get_antigravity_port_and_csrf()
        if not port or not csrf:
            return None

        # 1. 呼叫 GetUserStatus 取得 Credits 點數
        status_data = {}
        try:
            status_data = grpc_call(port, csrf, "GetUserStatus")
        except Exception:
            pass

        # 2. 呼叫 RetrieveUserQuotaSummary 取得真實 5H / Weekly Quotas
        summary_data = {}
        try:
            summary_data = grpc_call(port, csrf, "RetrieveUserQuotaSummary")
        except Exception:
            pass

        status = status_data.get("userStatus", {})
        plan_status = status.get("planStatus", {})
        plan = plan_status.get("planInfo", {})

        gemini_5h_rem = 1.0
        gemini_5h_reset = None
        gemini_wk_rem = 1.0
        gemini_wk_reset = None

        claude_5h_rem = 1.0
        claude_5h_reset = None
        claude_wk_rem = 1.0
        claude_wk_reset = None
        
        now_utc = datetime.now(timezone.utc)

        groups = summary_data.get("response", {}).get("groups", [])
        for group in groups:
            g_name = group.get("displayName", "").lower()
            for bucket in group.get("buckets", []):
                bid = bucket.get("bucketId", "").lower()
                rem = bucket.get("remainingFraction", 1.0)
                reset_t = bucket.get("resetTime", "")

                if "gemini" in g_name or "gemini" in bid:
                    if "5h" in bid:
                        gemini_5h_rem = rem
                        gemini_5h_reset = reset_t
                    elif "weekly" in bid:
                        gemini_wk_rem = rem
                        gemini_wk_reset = reset_t
                elif "claude" in g_name or "3p" in bid:
                    if "5h" in bid:
                        claude_5h_rem = rem
                        claude_5h_reset = reset_t
                    elif "weekly" in bid:
                        claude_wk_rem = rem
                        claude_wk_reset = reset_t

        def parse_reset_secs(reset_str):
            if not reset_str:
                return 0
            try:
                dt = datetime.fromisoformat(reset_str.replace("Z", "+00:00"))
                diff = (dt - now_utc).total_seconds()
                return max(0, int(diff))
            except Exception:
                return 0

        return {
            "gemini_5h_pct": int(gemini_5h_rem * 100),
            "gemini_5h_reset_secs": parse_reset_secs(gemini_5h_reset),
            "gemini_wk_pct": int(gemini_wk_rem * 100),
            "gemini_wk_reset_secs": parse_reset_secs(gemini_wk_reset),

            "claude_5h_pct": int(claude_5h_rem * 100),
            "claude_5h_reset_secs": parse_reset_secs(claude_5h_reset),
            "claude_wk_pct": int(claude_wk_rem * 100),
            "claude_wk_reset_secs": parse_reset_secs(claude_wk_reset),

            "prompt_credits": plan.get("monthlyPromptCredits", 0),
            "flow_credits": plan.get("monthlyFlowCredits", 0),
            "available_prompt": plan_status.get("availablePromptCredits", 0),
            "available_flow": plan_status.get("availableFlowCredits", 0),
        }

    # ─── 抓 OpenCode SQLite 真實 Token ──────────────────────
    def get_opencode_db_stats():
        db_path = os.path.expanduser("~/.local/share/opencode/opencode.db")
        if not os.path.exists(db_path):
            return None
        try:
            conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
            c = conn.cursor()
            now_ms = int(time.time() * 1000)
            five_h = 5 * 3600 * 1000
            seven_d = 7 * 24 * 3600 * 1000
            thirty_d = 30 * 24 * 3600 * 1000

            c.execute("SELECT data FROM message WHERE time_created > ?",
                      (now_ms - thirty_d,))
            rows = c.fetchall()
            conn.close()

            tok_5h = tok_7d = tok_30d = 0
            model_tokens = {}

            for r in rows:
                try:
                    js = json.loads(r[0])
                    tokens = js.get("tokens", {}).get("total", 0)
                    t_created = js.get("time", {}).get("created", 0)
                    model = js.get("modelID", "unknown")

                    model_tokens[model] = model_tokens.get(model, 0) + tokens
                    tok_30d += tokens
                    if now_ms - t_created < seven_d:
                        tok_7d += tokens
                    if now_ms - t_created < five_h:
                        tok_5h += tokens
                except Exception:
                    pass

            return {
                "tok_5h": tok_5h,
                "tok_7d": tok_7d,
                "tok_30d": tok_30d,
                "model_breakdown": model_tokens,
            }
        except Exception:
            return None

    # ─── 抓 OpenCode CLI Stats ───────────────────────────────
    def get_opencode_cli_stats():
        try:
            result = subprocess.run(
                ["powershell", "-Command", "opencode stats"],
                capture_output=True, text=True, encoding="utf-8", errors="ignore",
                creationflags=subprocess.CREATE_NO_WINDOW)
            out = result.stdout
            sessions = re.search(r'Sessions\s+([\d,]+)', out)
            messages = re.search(r'Messages\s+([\d,]+)', out)
            cost = re.search(r'Total Cost\s+\$([\d\.]+)', out)
            return {
                "sessions": sessions.group(1) if sessions else "0",
                "messages": messages.group(1) if messages else "0",
                "cost": cost.group(1) if cost else "0.00",
            }
        except Exception:
            return {"sessions": "--", "messages": "--", "cost": "--"}

    # ════════════════════════════════════════════════════════
    class FloatingDashboard:
        # ─── Colors ──────────────────────────────────────────
        BG        = "#F3F4F6"
        CARD      = "#FFFFFF"
        BORDER    = "#E5E7EB"
        TXT_PRI   = "#111827"
        TXT_SEC   = "#4B5563"
        GREEN     = "#059669"
        BLUE      = "#2563EB"
        ORANGE    = "#D97706"
        TAB_ON    = "#FFFFFF"
        TAB_OFF   = "#E5E7EB"

        def __init__(self, root):
            self.root = root
            self.root.title("Puti-AI Stats")
            self.root.overrideredirect(True)
            self.root.attributes("-alpha", 0.98, "-topmost", True)
            self.root.configure(bg=self.BG)
            self.root.geometry("295x440+300+300")
            make_window_rounded(self.root)

            # ── state ──
            self.current_tab = "antigravity"
            self.running = True
            self.edge_mode = ""
            self.resize_active = False
            self.drag_active = False
            self.EDGE = 8

            self._last_refresh = 0.0
            self._refresh_interval = 60
            self._refreshing = False

            # Antigravity
            self.ag_gemini_5h_pct = 100
            self.ag_gemini_5h_secs = 0
            self.ag_gemini_wk_pct = 100
            self.ag_gemini_wk_secs = 0
            
            self.ag_claude_5h_pct = 100
            self.ag_claude_5h_secs = 0
            self.ag_claude_wk_pct = 100
            self.ag_claude_wk_secs = 0

            self.ag_error = ""
            self.ag_prompt_credits = 0
            self.ag_flow_credits = 0
            self._ag_gemini_5h_secs_src = None
            self._ag_gemini_wk_secs_src = None
            self._ag_claude_5h_secs_src = None
            self._ag_claude_wk_secs_src = None
            self._ag_last_api_time = 0.0

            # OpenCode
            self.oc_tok_5h = 0
            self.oc_tok_7d = 0
            self.oc_tok_30d = 0
            self.oc_model_breakdown = {}
            self.oc_sessions = "--"
            self.oc_messages = "--"
            self.oc_cost = "--"

            self.menu = tk.Menu(self.root, tearoff=0, bg=self.CARD, fg=self.TXT_PRI)
            self.menu.add_command(label="Refresh", command=self.manual_refresh)
            self.menu.add_command(label="Exit", command=self.root.destroy)
            self.root.bind("<Button-3>", lambda e: self.menu.post(e.x_root, e.y_root))

            self.create_ui()
            self.bind_all_events()

            self.socket_thread = threading.Thread(target=self.listen_socket, daemon=True)
            self.socket_thread.start()

            self.refresh_data()
            self.tick()

        # ─── UI ──────────────────────────────────────────────
        def create_ui(self):
            nav = tk.Frame(self.root, bg=self.BG)
            nav.pack(fill="x", padx=12, pady=(12, 4))

            tabs = tk.Frame(nav, bg=self.BG)
            tabs.pack(side="left")
            self.tab_ag = tk.Label(tabs, text="Antigravity", font=("Microsoft JhengHei", 9, "bold"),
                                    bg=self.TAB_ON, fg=self.TXT_PRI, padx=12, pady=4, cursor="hand2")
            self.tab_ag.pack(side="left")
            self.tab_ag.bind("<Button-1>", lambda e: self.switch_tab("antigravity"))

            self.tab_oc = tk.Label(tabs, text="OpenCode", font=("Microsoft JhengHei", 9, "bold"),
                                    bg=self.TAB_OFF, fg=self.TXT_SEC, padx=12, pady=4, cursor="hand2")
            self.tab_oc.pack(side="left", padx=(4, 0))
            self.tab_oc.bind("<Button-1>", lambda e: self.switch_tab("opencode"))

            btns = tk.Frame(nav, bg=self.BG)
            btns.pack(side="right")
            self.refresh_lbl = tk.Label(btns, text="🔄", font=("Arial", 11), bg=self.BG,
                                        fg=self.TXT_SEC, cursor="hand2")
            self.refresh_lbl.pack(side="left", padx=(0, 8))
            self.refresh_lbl.bind("<Button-1>", lambda e: self.manual_refresh())
            close_btn = tk.Label(btns, text="×", font=("Arial", 16), bg=self.BG, fg=self.TXT_SEC, cursor="hand2")
            close_btn.pack(side="left")
            close_btn.bind("<Button-1>", lambda e: self.root.destroy())

            self.content = tk.Frame(self.root, bg=self.BG)
            self.content.pack(fill="both", expand=True, padx=12, pady=4)

            self._build_antigravity_view()
            self._build_opencode_view()
            self.show_view()

            bot = tk.Frame(self.root, bg=self.BG)
            bot.pack(side="bottom", fill="x")
            self.status_lbl = tk.Label(bot, text="啟動中...", font=("Microsoft JhengHei", 8),
                                        bg=self.BG, fg=self.TXT_SEC)
            self.status_lbl.pack(side="left", padx=14, pady=2)

        def _card(self, parent, title):
            card = tk.Frame(parent, bg=self.CARD,
                            highlightbackground=self.BORDER, highlightthickness=1)
            card.pack(fill="x", pady=4)
            tk.Label(card, text=title, font=("Microsoft JhengHei", 9, "bold"),
                     bg=self.CARD, fg=self.TXT_SEC).pack(anchor="w", padx=12, pady=(6, 2))
            return card

        def _ring_pair(self, parent, left_label, right_label):
            row = tk.Frame(parent, bg=self.CARD)
            row.pack(fill="x", padx=10, pady=(2, 6))

            lf = tk.Frame(row, bg=self.CARD); lf.pack(side="left", expand=True, fill="both")
            lc = tk.Canvas(lf, bg=self.CARD, highlightthickness=0); lc.pack(pady=2)
            ll = tk.Label(lf, text=left_label, font=("Microsoft JhengHei", 7),
                          bg=self.CARD, fg=self.TXT_SEC); ll.pack()

            rf = tk.Frame(row, bg=self.CARD); rf.pack(side="right", expand=True, fill="both")
            rc = tk.Canvas(rf, bg=self.CARD, highlightthickness=0); rc.pack(pady=2)
            rl = tk.Label(rf, text=right_label, font=("Microsoft JhengHei", 7),
                          bg=self.CARD, fg=self.TXT_SEC); rl.pack()

            return lc, ll, rc, rl

        def _stat_row(self, parent, label, val):
            f = tk.Frame(parent, bg=self.CARD); f.pack(fill="x", padx=14, pady=2)
            tk.Label(f, text=label, font=("Microsoft JhengHei", 9),
                     bg=self.CARD, fg=self.TXT_SEC).pack(side="left")
            v = tk.Label(f, text=val, font=("Consolas", 9, "bold"),
                         bg=self.CARD, fg=self.TXT_PRI); v.pack(side="right")
            return v

        def _build_antigravity_view(self):
            self.ag_view = tk.Frame(self.content, bg=self.BG)

            card_gem = self._card(self.ag_view, "✦ Puti-AI · Gemini Models")
            self.ring_gem_5h, self.lbl_gem_5h, self.ring_gem_wk, self.lbl_gem_wk = \
                self._ring_pair(card_gem, "5小時剩餘", "每週剩餘")

            card_cld = self._card(self.ag_view, "✦ Puti-AI · Claude & GPT models")
            self.ring_cld_5h, self.lbl_cld_5h, self.ring_cld_wk, self.lbl_cld_wk = \
                self._ring_pair(card_cld, "5小時剩餘", "每週剩餘")

            card_credit = self._card(self.ag_view, "✦ Puti-AI · 點數餘額")
            self.lbl_prompt_credit = self._stat_row(card_credit, "💰  Prompt Credits", "-- / --")
            self.lbl_flow_credit = self._stat_row(card_credit, "🌊  Flow Credits", "-- / --")

            self.ag_err_lbl = tk.Label(self.ag_view, text="", font=("Microsoft JhengHei", 8),
                                        bg=self.BG, fg=self.ORANGE, wraplength=260, justify="left")
            self.ag_err_lbl.pack(anchor="w", padx=4)

        def _build_opencode_view(self):
            self.oc_view = tk.Frame(self.content, bg=self.BG)

            card_tok = self._card(self.oc_view, "✦ Puti-AI · OpenCode Token 用量")
            self.lbl_tok_5h = self._stat_row(card_tok, "🕐  近 5 小時", "-- tok")
            self.lbl_tok_7d = self._stat_row(card_tok, "📅  近 7 天", "-- tok")
            self.lbl_tok_30d = self._stat_row(card_tok, "📆  近 30 天", "-- tok")

            card_stat = self._card(self.oc_view, "✦ Puti-AI · Session 統計")
            self.lbl_ses = self._stat_row(card_stat, "Sessions / Messages", "S: -- / M: --")
            self.lbl_cost = self._stat_row(card_stat, "Total Cost", "$--")

            card_model = self._card(self.oc_view, "✦ Top Models (30天)")
            self.model_text = tk.Label(card_model, text="載入中...",
                                       font=("Consolas", 8), bg=self.CARD, fg=self.TXT_SEC,
                                       justify="left", anchor="w")
            self.model_text.pack(anchor="w", padx=12, pady=(0, 8))

        # ─── View switching ───────────────────────────────────
        def show_view(self):
            if self.current_tab == "antigravity":
                self.oc_view.pack_forget()
                self.ag_view.pack(fill="both", expand=True)
                self.tab_ag.configure(bg=self.TAB_ON, fg=self.TXT_PRI)
                self.tab_oc.configure(bg=self.TAB_OFF, fg=self.TXT_SEC)
            else:
                self.ag_view.pack_forget()
                self.oc_view.pack(fill="both", expand=True)
                self.tab_ag.configure(bg=self.TAB_OFF, fg=self.TXT_SEC)
                self.tab_oc.configure(bg=self.TAB_ON, fg=self.TXT_PRI)

        def switch_tab(self, tab):
            self.current_tab = tab
            self.show_view()
            self.refresh_ui()

        # ─── Drawing ─────────────────────────────────────────
        def draw_ring(self, canvas, pct, color, scale=1.0):
            canvas.delete("all")
            w = max(45, int(60 * scale))
            canvas.configure(width=w, height=w)
            m = 5; r = w - m
            pw = max(3, int(5 * scale))
            canvas.create_arc(m, m, r, r, start=0, extent=359.9,
                              outline="#E5E7EB", width=pw, style="arc")
            ext = -359.99 if pct >= 100 else -3.6 * pct
            ring_color = self.ORANGE if pct <= 10 else (self.BLUE if pct <= 25 else color)
            canvas.create_arc(m, m, r, r, start=90, extent=ext,
                              outline=ring_color, width=pw, style="arc")
            fs_num = max(1, int(16 * scale)); fs_pct = max(1, int(8 * scale))
            canvas.create_text(w // 2, int(w * 0.40),
                               text=str(pct), font=("Segoe UI", fs_num, "bold"), fill=self.TXT_PRI)
            canvas.create_text(w // 2, int(w * 0.72),
                               text="%", font=("Segoe UI", fs_pct, "bold"), fill=self.TXT_SEC)

        def fmt_time(self, secs):
            if secs <= 0: return "--"
            h = secs // 3600; m = (secs % 3600) // 60
            if h >= 24:
                d = h // 24; hr = h % 24
                return f"{d}天 {hr}時" if hr else f"{d}天"
            return f"{h}時 {m}分" if h else f"{m}分"

        def fmt_k(self, n):
            if n >= 1_000_000: return f"{n/1_000_000:.1f}M"
            if n >= 1_000: return f"{n//1000}K"
            return str(n)

        def refresh_ui(self):
            sf = self.root.winfo_width() / 295.0

            # ── Antigravity Tab ──
            # Gemini
            self.draw_ring(self.ring_gem_5h, self.ag_gemini_5h_pct, self.GREEN, sf)
            self.lbl_gem_5h.configure(
                text=f"5小時剩餘 {self.ag_gemini_5h_pct}%\n重置 {self.fmt_time(self.ag_gemini_5h_secs)}",
                font=("Microsoft JhengHei", max(1, int(7 * sf))))
                
            self.draw_ring(self.ring_gem_wk, self.ag_gemini_wk_pct, self.GREEN, sf)
            self.lbl_gem_wk.configure(
                text=f"每週剩餘 {self.ag_gemini_wk_pct}%\n重置 {self.fmt_time(self.ag_gemini_wk_secs)}",
                font=("Microsoft JhengHei", max(1, int(7 * sf))))

            # Claude
            self.draw_ring(self.ring_cld_5h, self.ag_claude_5h_pct, self.BLUE, sf)
            self.lbl_cld_5h.configure(
                text=f"5小時剩餘 {self.ag_claude_5h_pct}%\n重置 {self.fmt_time(self.ag_claude_5h_secs)}",
                font=("Microsoft JhengHei", max(1, int(7 * sf))))

            self.draw_ring(self.ring_cld_wk, self.ag_claude_wk_pct, self.BLUE, sf)
            self.lbl_cld_wk.configure(
                text=f"每週剩餘 {self.ag_claude_wk_pct}%\n重置 {self.fmt_time(self.ag_claude_wk_secs)}",
                font=("Microsoft JhengHei", max(1, int(7 * sf))))

            self.ag_err_lbl.configure(text=self.ag_error)
            
            self.lbl_prompt_credit.configure(text=f"{self.ag_prompt_credits} / 50,000")
            self.lbl_flow_credit.configure(text=f"{self.ag_flow_credits} / 150,000")

            # ── OpenCode Tab ──
            self.lbl_tok_5h.configure(text=f"{self.fmt_k(self.oc_tok_5h)} tok")
            self.lbl_tok_7d.configure(text=f"{self.fmt_k(self.oc_tok_7d)} tok")
            self.lbl_tok_30d.configure(text=f"{self.fmt_k(self.oc_tok_30d)} tok")

            self.lbl_ses.configure(text=f"S: {self.oc_sessions} / M: {self.oc_messages}",
                                   font=("Consolas", max(1, int(9 * sf)), "bold"))
            self.lbl_cost.configure(text=f"${self.oc_cost}",
                                    font=("Consolas", max(1, int(9 * sf)), "bold"))

            if self.oc_model_breakdown:
                top = sorted(self.oc_model_breakdown.items(), key=lambda x: -x[1])[:5]
                lines = [f"{self.fmt_k(v):>6}  {k}" for k, v in top]
                self.model_text.configure(text="\n".join(lines))

        # ─── Data refresh ─────────────────────────────────────
        def refresh_data(self):
            if self._refreshing:
                return
            self._refreshing = True

            def task():
                try:
                    ag = None
                    for attempt in range(2):
                        ag = get_antigravity_quota()
                        if ag is not None:
                            break
                        time.sleep(0.5)

                    if ag:
                        def upd_ag():
                            self.ag_gemini_5h_pct = ag["gemini_5h_pct"]
                            self.ag_gemini_5h_secs = ag["gemini_5h_reset_secs"]
                            self.ag_gemini_wk_pct = ag["gemini_wk_pct"]
                            self.ag_gemini_wk_secs = ag["gemini_wk_reset_secs"]

                            self.ag_claude_5h_pct = ag["claude_5h_pct"]
                            self.ag_claude_5h_secs = ag["claude_5h_reset_secs"]
                            self.ag_claude_wk_pct = ag["claude_wk_pct"]
                            self.ag_claude_wk_secs = ag["claude_wk_reset_secs"]

                            self.ag_prompt_credits = ag.get("available_prompt", 0)
                            self.ag_flow_credits = ag.get("available_flow", 0)

                            self._ag_gemini_5h_secs_src = ag["gemini_5h_reset_secs"]
                            self._ag_gemini_wk_secs_src = ag["gemini_wk_reset_secs"]
                            self._ag_claude_5h_secs_src = ag["claude_5h_reset_secs"]
                            self._ag_claude_wk_secs_src = ag["claude_wk_reset_secs"]

                            self._ag_last_api_time = time.monotonic()
                            self.ag_error = ""
                            self.status_lbl.configure(
                                text=f"更新 {time.strftime('%H:%M:%S')} · 即時 API 監控")
                            self.refresh_ui()
                        self.root.after(0, upd_ag)
                    else:
                        self.root.after(0, lambda: self.ag_err_lbl.configure(
                            text="⚠ Antigravity Language Server 未偵測到（2次重試失敗），請確認 App 已開啟"))
                except Exception as e:
                    self.root.after(0, lambda err=e: self.ag_err_lbl.configure(
                        text=f"⚠ API 錯誤: {str(err)[:80]}"))

                try:
                    db = get_opencode_db_stats()
                    if db:
                        def upd_oc():
                            self.oc_tok_5h = db["tok_5h"]
                            self.oc_tok_7d = db["tok_7d"]
                            self.oc_tok_30d = db["tok_30d"]
                            self.oc_model_breakdown = db["model_breakdown"]
                            self.refresh_ui()
                        self.root.after(0, upd_oc)
                except Exception:
                    pass

                try:
                    cli = get_opencode_cli_stats()
                    def upd_cli():
                        self.oc_sessions = cli["sessions"]
                        self.oc_messages = cli["messages"]
                        self.oc_cost = cli["cost"]
                        self.refresh_ui()
                    self.root.after(0, upd_cli)
                except Exception:
                    pass

                def done():
                    self._refreshing = False
                self.root.after(0, done)

            threading.Thread(target=task, daemon=True).start()

        def manual_refresh(self):
            self.refresh_lbl.configure(fg=self.BLUE)
            self.status_lbl.configure(text="更新中...")
            self.refresh_data()
            self.root.after(800, lambda: self.refresh_lbl.configure(fg=self.TXT_SEC))

        # ─── Tick (每秒倒數 + 每 N 秒自動刷新) ──────────────
        def tick(self):
            now = time.monotonic()

            # 用 real API time 計算準確倒數，而非 local decrement
            if self._ag_gemini_5h_secs_src is not None:
                elapsed = int(now - self._ag_last_api_time)
                self.ag_gemini_5h_secs = max(0, self._ag_gemini_5h_secs_src - elapsed)
            if self._ag_gemini_wk_secs_src is not None:
                elapsed = int(now - self._ag_last_api_time)
                self.ag_gemini_wk_secs = max(0, self._ag_gemini_wk_secs_src - elapsed)

            if self._ag_claude_5h_secs_src is not None:
                elapsed = int(now - self._ag_last_api_time)
                self.ag_claude_5h_secs = max(0, self._ag_claude_5h_secs_src - elapsed)
            if self._ag_claude_wk_secs_src is not None:
                elapsed = int(now - self._ag_last_api_time)
                self.ag_claude_wk_secs = max(0, self._ag_claude_wk_secs_src - elapsed)

            # 定時刷新：monotonic 追蹤，漂移自癒合
            if now - self._last_refresh >= self._refresh_interval:
                self._last_refresh = now
                self.refresh_data()

            self.refresh_ui()
            if self.running:
                self.root.after(1000, self.tick)

        # ─── Drag / Resize ────────────────────────────────────
        def bind_all_events(self):
            def bind_r(w):
                cls = w.winfo_class()
                if cls not in ("Button", "Menu"):
                    w.bind("<Motion>", self.detect_edge, add="+")
                    w.bind("<Button-1>", self.on_press, add="+")
                    w.bind("<B1-Motion>", self.on_drag, add="+")
                    w.bind("<ButtonRelease-1>", self.on_release, add="+")
                for ch in w.winfo_children():
                    bind_r(ch)
            bind_r(self.root)

        def detect_edge(self, e):
            if self.resize_active or self.drag_active: return
            x = e.x_root - self.root.winfo_x()
            y = e.y_root - self.root.winfo_y()
            w = self.root.winfo_width(); h = self.root.winfo_height()
            E = self.EDGE
            nl, nr, nt, nb = x < E, x > w - E, y < E, y > h - E
            if nl and nt: m, c = "nw", "size_nw_se"
            elif nr and nt: m, c = "ne", "size_ne_sw"
            elif nl and nb: m, c = "sw", "size_ne_sw"
            elif nr and nb: m, c = "se", "size_nw_se"
            elif nl: m, c = "w", "size_we"
            elif nr: m, c = "e", "size_we"
            elif nt: m, c = "n", "size_ns"
            elif nb: m, c = "s", "size_ns"
            else: m, c = "", "arrow"
            self.edge_mode = m
            self.root.config(cursor=c)

        def on_press(self, e):
            self.sx, self.sy = e.x_root, e.y_root
            self.sw, self.sh = self.root.winfo_width(), self.root.winfo_height()
            self.spx, self.spy = self.root.winfo_x(), self.root.winfo_y()
            if self.edge_mode:
                self.resize_active = True; self.drag_active = False
            else:
                self.resize_active = False; self.drag_active = True
                self.ox = e.x_root - self.spx; self.oy = e.y_root - self.spy

        def on_drag(self, e):
            if self.resize_active:
                dx = e.x_root - self.sx; dy = e.y_root - self.sy
                nw, nh, nx, ny = self.sw, self.sh, self.spx, self.spy
                MIN = 260, 340
                if "e" in self.edge_mode: nw = max(MIN[0], self.sw + dx)
                elif "w" in self.edge_mode:
                    if self.sw - dx >= MIN[0]: nw = self.sw - dx; nx = self.spx + dx
                if "s" in self.edge_mode: nh = max(MIN[1], self.sh + dy)
                elif "n" in self.edge_mode:
                    if self.sh - dy >= MIN[1]: nh = self.sh - dy; ny = self.spy + dy
                self.root.geometry(f"{nw}x{nh}+{nx}+{ny}")
                self.refresh_ui()
            elif self.drag_active:
                self.root.geometry(f"+{e.x_root - self.ox}+{e.y_root - self.oy}")

        def on_release(self, e):
            self.resize_active = False; self.drag_active = False
            self.detect_edge(e)

        # ─── Socket listener ─────────────────────────────────
        def listen_socket(self):
            srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            srv.bind(('127.0.0.1', PORT_SINGLETON))
            srv.listen(1)
            while self.running:
                try:
                    conn, _ = srv.accept()
                    if conn.recv(1024) == b'TOGGLE':
                        self.running = False
                        self.root.after(0, self.root.destroy)
                        break
                    conn.close()
                except Exception:
                    break

    root = tk.Tk()
    app = FloatingDashboard(root)
    root.mainloop()

except Exception as e:
    log_error(e)
