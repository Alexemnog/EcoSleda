# ═══════════════════════════════════════════════
#  app.py  —  Главно приложение CarbonFootprintApp
# ═══════════════════════════════════════════════

import tkinter as tk
from tkinter import colorchooser
import threading
import hashlib
from tkinter import messagebox, ttk, filedialog
from geopy.distance import geodesic
from geopy.geocoders import Nominatim
import webbrowser
import requests
from bs4 import BeautifulSoup
import tempfile
import os
import json
import calendar
from datetime import datetime, timedelta
import matplotlib
matplotlib.use('TkAgg')
from database import init_db
from auth import AuthWindow
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# ── Optional: PDF export ──
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors as rl_colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import cm
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

from theme import (
    BG, SURFACE, SURFACE2, SURFACE3,
    ACCENT, ACCENT2, ACCENT3, GREEN, TEAL,
    DIM, TEXT, TEXTDIM, ERROR, WARN, WHITE, PURPLE, PINK,
    FONT_HEAD, FONT_SUB, FONT_BODY, FONT_LARGE,
    lbl, entry_widget, card, sty_btn, divider, gradient_bar,
)
from database import (
    load_entries, save_entry, get_profile,
    update_name, update_password, get_road_route,
)
from map_server import MAP_PORT, build_map_html, set_map_callback

class CarbonFootprintApp:
    def __init__(self, root, user_id, user_name):
        self.root      = root
        self.user_id   = user_id
        self.user_name = user_name

        self.root.title(f"🌿 ЕкоСледа — {user_name}")
        self.root.geometry("1280x900")
        self.root.minsize(1000, 750)
        # Maximize window cross-platform
        try:
            self.root.state('zoomed')  # Windows
        except Exception:
            try:
                self.root.attributes('-zoomed', True)  # Linux
            except Exception:
                self.root.geometry("1280x900")
        self.root.configure(bg=BG)

        # Style
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self._configure_styles()

        # Data — real data only, no mock generation
        self.history_data = load_entries(self.user_id)

        # Build UI
        self._build_header()
        self._build_notebook()
        self._build_menu()

    # ── Styles ──
    def _configure_styles(self):
        s = self.style
        s.configure('TFrame',        background=BG)
        s.configure('TLabel',        background=BG, foreground=TEXT, font=FONT_BODY)
        s.configure('TNotebook',     background=BG, borderwidth=0)
        s.configure('TNotebook.Tab',
                    font=("Helvetica", 10, "bold"),
                    padding=[16, 10],
                    background=SURFACE2,
                    foreground=TEXTDIM)
        s.map('TNotebook.Tab',
              background=[('selected', ACCENT2)],
              foreground=[('selected', WHITE)])
        s.configure('TScrollbar',    background=SURFACE3, troughcolor=BG,
                    borderwidth=0, arrowcolor=DIM)
        s.configure('TCombobox',     fieldbackground=SURFACE3, background=SURFACE3,
                    foreground=TEXT, selectbackground=ACCENT2)
        s.configure('TRadiobutton',  background=SURFACE, foreground=TEXT, font=FONT_BODY)
        s.map('TRadiobutton',
              background=[('active', SURFACE)],
              foreground=[('active', ACCENT)])

    # ── Header strip ──
    def _build_header(self):
        # Gradient accent bar at top
        bar = tk.Frame(self.root, bg=BG, height=4)
        bar.pack(fill='x', side='top')
        bar.pack_propagate(False)
        for clr in [ACCENT2, ACCENT3, TEAL, GREEN, TEAL, ACCENT3, ACCENT2]:
            tk.Frame(bar, bg=clr, height=4).pack(side='left', fill='both', expand=True)

        hdr = tk.Frame(self.root, bg=SURFACE, height=58)
        hdr.pack(fill='x', side='top')
        hdr.pack_propagate(False)

        left = tk.Frame(hdr, bg=SURFACE)
        left.pack(side='left', padx=20, pady=10)
        lbl(left, "🌿", font=("Helvetica", 20), bg=SURFACE, fg=GREEN).pack(side='left', padx=(0, 6))
        lbl(left, "ЕкоСледа", font=("Helvetica", 16, "bold"),
            fg=WHITE, bg=SURFACE).pack(side='left')
        lbl(left, " Pro", font=("Helvetica", 11), fg=ACCENT, bg=SURFACE).pack(side='left', pady=(4, 0))

        # Right side — user info
        user_f = tk.Frame(hdr, bg=SURFACE)
        user_f.pack(side='right', padx=20, pady=8)

        profile = get_profile(self.user_id)
        member_since = profile[2] if profile else "?"

        # Online indicator
        online_f = tk.Frame(user_f, bg=SURFACE)
        online_f.pack(side='left', padx=(0, 12))
        tk.Canvas(online_f, width=8, height=8, bg=SURFACE, highlightthickness=0).pack(side='left', padx=(0, 4))
        online_dot = tk.Canvas(online_f, width=8, height=8, bg=SURFACE, highlightthickness=0)
        online_dot.pack(side='left', padx=(0, 4))
        online_dot.create_oval(1, 1, 7, 7, fill=GREEN, outline="")
        lbl(online_f, "онлайн", font=("Helvetica", 8), fg=GREEN, bg=SURFACE).pack(side='left')

        user_pill = tk.Frame(user_f, bg=SURFACE3)
        user_pill.pack(side='left', padx=4)
        lbl(user_pill, f"👤  {self.user_name}", font=("Helvetica", 10, "bold"),
            fg=WHITE, bg=SURFACE3).pack(side='left', padx=10, pady=6)
        lbl(user_pill, f"| від {member_since}", font=FONT_SUB,
            fg=TEXTDIM, bg=SURFACE3).pack(side='left', padx=(0, 10))

        logout_btn = tk.Button(user_f, text="⏻  Изход",
                               command=self._logout,
                               bg=SURFACE3, fg=TEXTDIM, font=("Helvetica", 9),
                               relief=tk.FLAT, cursor="hand2", padx=10, pady=6,
                               activebackground=ERROR, activeforeground=WHITE)
        logout_btn.pack(side='left', padx=(8, 0))

    # ── Sidebar + Content area ──
    def _build_notebook(self):
        # Main container: sidebar left, content right
        self._main_frame = tk.Frame(self.root, bg=BG)
        self._main_frame.pack(fill='both', expand=True)

        # ── Sidebar ──
        self._sidebar = tk.Frame(self._main_frame, bg=SURFACE, width=220)
        self._sidebar.pack(side='left', fill='y')
        self._sidebar.pack_propagate(False)

        # Thin accent line on right edge of sidebar
        tk.Frame(self._main_frame, bg=ACCENT2, width=1).pack(side='left', fill='y')

        # ── Content area ──
        self._content = tk.Frame(self._main_frame, bg=BG)
        self._content.pack(side='left', fill='both', expand=True)

        # Build all tab frames (hidden initially)
        self._pages = {}
        self._create_welcome_tab()
        self._create_calculator_tab()
        self._create_map_tab()
        self._create_progress_tab()
        self._create_impact_tab()
        self._create_history_tab()
        self._create_compare_tab()
        self._create_achievements_tab()
        self._create_goals_tab()
        self._create_ai_tab()
        self._create_leaderboard_tab()
        self._create_habits_tab()
        self._create_statistics_tab()
        self._create_budget_tab()
        self._create_tips_tab()
        self._create_community_tab()
        self._create_profile_tab()

        # Build sidebar nav
        self._nav_buttons = {}
        self._active_page = None
        self._build_sidebar_nav()

        # Show default page
        self._show_page("welcome")

        # Weekly summary
        if datetime.now().weekday() == 0 and self.history_data:
            self.root.after(2500, self._show_weekly_summary)

    def _build_sidebar_nav(self):
        """Build grouped sidebar navigation."""
        # Logo area
        logo_f = tk.Frame(self._sidebar, bg=SURFACE)
        logo_f.pack(fill='x', pady=(16, 8))
        lbl(logo_f, "🌿  ЕкоСледа", font=("Helvetica", 13, "bold"),
            fg=GREEN, bg=SURFACE).pack(padx=16, anchor='w')
        tk.Frame(self._sidebar, bg=SURFACE3, height=1).pack(fill='x', padx=12, pady=(0, 8))

        nav_groups = [
            ("ГЛАВНО", [
                ("welcome",      "🏠", "Начало"),
                ("calculator",   "🧮", "Калкулатор"),
                ("map",          "🗺️",  "Карта"),
            ]),
            ("АНАЛИЗИ", [
                ("progress",     "📈", "Прогрес"),
                ("impact",       "🌿", "Въздействие"),
                ("history",      "📋", "История"),
                ("compare",      "⚖️",  "Сравни"),
                ("statistics",   "📊", "Статистика"),
            ]),
            ("МОТИВАЦИЯ", [
                ("achievements", "🏆", "Постижения"),
                ("goals",        "🎯", "Цели"),
                ("habits",       "📅", "Навици"),
                ("leaderboard",  "🏅", "Лидерборд"),
            ]),
            ("ОБЩНОСТ & AI", [
                ("ai",           "🤖", "AI Съветник"),
                ("community",    "👥", "Общност"),
                ("tips",         "💡", "Съвети"),
            ]),
            ("АКАУНТ", [
                ("budget",       "💰", "Бюджет CO₂"),
                ("profile",      "👤", "Профил"),
            ]),
        ]

        scrollable = tk.Frame(self._sidebar, bg=SURFACE)
        scrollable.pack(fill='both', expand=True)

        for group_name, items in nav_groups:
            # Group label
            lbl(scrollable, group_name,
                font=("Helvetica", 7, "bold"), fg=DIM, bg=SURFACE).pack(
                anchor='w', padx=18, pady=(10, 2))

            for page_key, icon, title in items:
                btn_frame = tk.Frame(scrollable, bg=SURFACE, cursor="hand2")
                btn_frame.pack(fill='x', padx=8, pady=1)

                icon_lbl = tk.Label(btn_frame, text=icon,
                                    font=("Helvetica", 13),
                                    bg=SURFACE, fg=TEXTDIM,
                                    width=2, anchor='center')
                icon_lbl.pack(side='left', padx=(8, 6), pady=6)

                title_lbl = tk.Label(btn_frame, text=title,
                                     font=("Helvetica", 10),
                                     bg=SURFACE, fg=TEXTDIM, anchor='w')
                title_lbl.pack(side='left', fill='x', expand=True)

                # Click anywhere on the row
                def make_click(key):
                    return lambda e: self._show_page(key)

                for widget in (btn_frame, icon_lbl, title_lbl):
                    widget.bind("<Button-1>", make_click(page_key))
                    widget.bind("<Enter>", lambda e, f=btn_frame, i=icon_lbl, t=title_lbl:
                                self._nav_hover(f, i, t, True))
                    widget.bind("<Leave>", lambda e, f=btn_frame, i=icon_lbl, t=title_lbl:
                                self._nav_hover(f, i, t, False))

                self._nav_buttons[page_key] = (btn_frame, icon_lbl, title_lbl)

    def _nav_hover(self, frame, icon, title, entering):
        """Hover effect for nav items."""
        key = next((k for k, v in self._nav_buttons.items()
                    if v == (frame, icon, title)), None)
        if key == self._active_page:
            return
        bg = SURFACE3 if entering else SURFACE
        fg = WHITE if entering else TEXTDIM
        frame.config(bg=bg)
        icon.config(bg=bg, fg=fg)
        title.config(bg=bg, fg=fg)

    def _show_page(self, key):
        """Switch to a page by key."""
        # Deactivate old
        if self._active_page and self._active_page in self._nav_buttons:
            f, i, t = self._nav_buttons[self._active_page]
            f.config(bg=SURFACE)
            i.config(bg=SURFACE, fg=TEXTDIM)
            t.config(bg=SURFACE, fg=TEXTDIM)
            # Remove active indicator
            for child in f.winfo_children():
                if getattr(child, '_is_indicator', False):
                    child.destroy()

        # Hide all pages
        for page_key, frame in self._pages.items():
            frame.pack_forget()

        # Show new page
        if key in self._pages:
            self._pages[key].pack(fill='both', expand=True)

        # Activate nav button
        if key in self._nav_buttons:
            f, i, t = self._nav_buttons[key]
            f.config(bg=SURFACE2)
            i.config(bg=SURFACE2, fg=GREEN)
            t.config(bg=SURFACE2, fg=WHITE, font=("Helvetica", 10, "bold"))
            # Active indicator bar
            indicator = tk.Frame(f, bg=GREEN, width=3)
            indicator._is_indicator = True
            indicator.place(relx=0, rely=0, relheight=1, x=0)

        self._active_page = key


    # ── Menu ──
    def _build_menu(self):
        menubar = tk.Menu(self.root, bg=SURFACE, fg=TEXT, activebackground=ACCENT2, activeforeground=BG)

        file_m = tk.Menu(menubar, tearoff=0, bg=SURFACE, fg=TEXT)
        file_m.add_command(label="Опресни данни", command=self._refresh_all)
        file_m.add_command(label="Експортирай CSV", command=self._export_data)
        file_m.add_separator()
        file_m.add_command(label="Изход", command=self.root.quit)
        menubar.add_cascade(label="Файл", menu=file_m)

        help_m = tk.Menu(menubar, tearoff=0, bg=SURFACE, fg=TEXT)
        help_m.add_command(label="Относно", command=self._show_about)
        help_m.add_command(label="Еко новини", command=self._fetch_eco_news)
        menubar.add_cascade(label="Помощ", menu=help_m)

        self.root.config(menu=menubar)

    # ─────────────── SCROLLABLE FRAME HELPER ───────────────
    def _scrollable(self, parent):
        """Returns (canvas, inner_scrollable_frame).
        Inner frame fills the FULL width of the canvas — no more top-left corner problem."""
        canvas = tk.Canvas(parent, bg=BG, highlightthickness=0)
        vsb    = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        inner  = tk.Frame(canvas, bg=BG)

        # ── КЛЮЧОВА ПОПРАВКА: разтяга вътрешния frame по цялата ширина ──
        win_id = canvas.create_window((0, 0), window=inner, anchor="nw")

        def _on_canvas_resize(event):
            canvas.itemconfig(win_id, width=event.width)

        canvas.bind("<Configure>", _on_canvas_resize)
        inner.bind("<Configure>",
                   lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.configure(yscrollcommand=vsb.set)

        canvas.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        def _on_scroll(event):
            if event.delta:
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            elif event.num == 4:
                canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                canvas.yview_scroll(1, "units")

        def _bind(event):
            canvas.bind_all("<MouseWheel>", _on_scroll)
            canvas.bind_all("<Button-4>",   _on_scroll)
            canvas.bind_all("<Button-5>",   _on_scroll)

        def _unbind(event):
            canvas.unbind_all("<MouseWheel>")
            canvas.unbind_all("<Button-4>")
            canvas.unbind_all("<Button-5>")

        canvas.bind("<Enter>", _bind)
        canvas.bind("<Leave>", _unbind)
        inner.bind("<Enter>", _bind)
        inner.bind("<Leave>", _unbind)

        return canvas, inner

    def _section_card(self, parent, title="", pady_inner=16):
        c = tk.Frame(parent, bg=SURFACE, bd=0)
        c.pack(fill='x', padx=18, pady=8)
        if title:
            tk.Frame(c, bg=ACCENT2, width=4).pack(side='left', fill='y')
            lbl(c, f"  {title}", font=("Georgia", 13, "bold"), fg=TEXT, bg=SURFACE).pack(
                side='left', padx=10, pady=pady_inner)
        return c

    # ──────────────────────────────────────────────
    #  TAB: WELCOME
    # ──────────────────────────────────────────────
    def _create_welcome_tab(self):
        tab = tk.Frame(self._content, bg=BG)
        self._pages["welcome"] = tab
        _, inner = self._scrollable(tab)

        # Hero banner
        hero = tk.Frame(inner, bg=SURFACE2)
        hero.pack(fill='x', padx=18, pady=(16, 8))

        # Left side
        left = tk.Frame(hero, bg=SURFACE2)
        left.pack(side='left', padx=30, pady=24, fill='both', expand=True)

        # Greeting with animated-style decoration
        greet_f = tk.Frame(left, bg=SURFACE2)
        greet_f.pack(anchor='w', fill='x')
        lbl(greet_f, "👋", font=("Helvetica", 32), bg=SURFACE2).pack(side='left', padx=(0, 10))
        greet_right = tk.Frame(greet_f, bg=SURFACE2)
        greet_right.pack(side='left')
        lbl(greet_right, f"Здравей, {self.user_name}!",
            font=("Helvetica", 22, "bold"), fg=WHITE, bg=SURFACE2).pack(anchor='w')
        lbl(greet_right, "Продължи да намаляваш своя въглероден отпечатък",
            font=("Helvetica", 10), fg=TEXTDIM, bg=SURFACE2).pack(anchor='w')

        # Quick action buttons
        btns = tk.Frame(left, bg=SURFACE2)
        btns.pack(anchor='w', pady=(16, 0))
        calc_btn = tk.Button(btns, text="⚡  Нов запис",
                             command=lambda: self._show_page("calculator"))
        sty_btn(calc_btn, accent=True)
        calc_btn.pack(side='left', padx=(0, 8))
        prog_btn = tk.Button(btns, text="📊  Прогрес",
                             command=lambda: self._show_page("progress"))
        sty_btn(prog_btn)
        prog_btn.pack(side='left', padx=(0, 8))

        # Right: Quick stats
        right = tk.Frame(hero, bg=SURFACE3)
        right.pack(side='right', padx=20, pady=20, ipadx=10)
        self._welcome_stats_frame = right

        today  = datetime.now()
        last30 = [e for e in self.history_data if (today - e['date']).days <= 30]
        total_all = sum(e['total_co2'] for e in self.history_data)
        total_30  = sum(e['total_co2'] for e in last30)
        days_used = len(set(e['date'].date() for e in self.history_data))

        if self.history_data:
            for icon, label, val, clr in [
                ("📊", "Последни 30 дни", f"{total_30:.0f} kg CO₂", ACCENT),
                ("🌍", "Общо записано",   f"{total_all:.0f} kg CO₂", GREEN),
                ("📅", "Дни активност",   str(days_used),             TEAL),
            ]:
                self._stat_pill(right, f"{icon}  {label}", val, clr)
        else:
            # Empty state — покажи бутон за нов запис
            ep = tk.Frame(right, bg=SURFACE3)
            ep.pack(padx=20, pady=20)
            lbl(ep, "🌱", font=("Helvetica", 40), bg=SURFACE3).pack(pady=(10, 4))
            lbl(ep, "Все още няма данни", font=("Helvetica", 11, "bold"),
                fg=ACCENT, bg=SURFACE3).pack()
            lbl(ep, "Добави първия запис\nи виж статистиките!", font=("Helvetica", 9),
                fg=TEXTDIM, bg=SURFACE3, justify='center').pack(pady=(4, 10))
            start_btn = tk.Button(ep, text="⚡  Започни сега",
                                  command=lambda: self._show_page("calculator"))
            sty_btn(start_btn, accent=True)
            start_btn.pack(pady=(0, 14), padx=14, fill='x')

        # Feature cards row — кликаеми!
        row = tk.Frame(inner, bg=BG)
        row.pack(fill='x', padx=18, pady=8)
        features = [
            ("🚗", "Калкулатор",   "Изчисли CO₂ от\nпътуванията", ACCENT2, "calculator"),
            ("🗺️",  "Карта",        "Интерактивен\nмаршрут",        TEAL,   "map"),
            ("🏆", "Постижения",   "Спечели значки\nи награди",     PURPLE, "achievements"),
            ("🎯", "Цели",         "Задай месечна\nCO₂ цел",        GREEN,  "goals"),
        ]
        for icon, title, body_txt, clr, page_key in features:
            c = tk.Frame(row, bg=SURFACE, bd=0, cursor="hand2")
            c.pack(side='left', expand=True, fill='x', padx=6, pady=4)
            tk.Frame(c, bg=clr, height=3).pack(fill='x')
            lbl(c, icon, font=("Helvetica", 28), bg=SURFACE).pack(pady=(16, 4))
            lbl(c, title, font=("Helvetica", 11, "bold"), fg=clr, bg=SURFACE).pack()
            lbl(c, body_txt, font=("Helvetica", 9), fg=TEXTDIM, bg=SURFACE,
                justify='center').pack(pady=(4, 6))
            lbl(c, "→ Отвори", font=("Helvetica", 8, "bold"), fg=clr,
                bg=SURFACE).pack(pady=(0, 14))
            for widget in c.winfo_children():
                widget.bind("<Button-1>", lambda _, k=page_key: self._show_page(k))
                widget.configure(cursor="hand2")
            c.bind("<Button-1>", lambda _, k=page_key: self._show_page(k))
            # Hover ефект
            def on_enter(e, frame=c, color=clr):
                frame.config(bg=SURFACE2)
                for w in frame.winfo_children():
                    try: w.config(bg=SURFACE2)
                    except: pass
            def on_leave(e, frame=c):
                frame.config(bg=SURFACE)
                for w in frame.winfo_children():
                    try: w.config(bg=SURFACE)
                    except: pass
            c.bind("<Enter>", on_enter)
            c.bind("<Leave>", on_leave)

        # Recent activity
        if self.history_data:
            act_c = card(inner, accent_color=ACCENT2)
            act_c.pack(fill='x', padx=18, pady=8)
            body_f = tk.Frame(act_c, bg=SURFACE)
            body_f.pack(fill='x', padx=16, pady=14)
            hdr_row = tk.Frame(body_f, bg=SURFACE)
            hdr_row.pack(fill='x', pady=(0, 10))
            lbl(hdr_row, "🕐  Последна Активност",
                font=("Helvetica", 12, "bold"), fg=WHITE, bg=SURFACE).pack(side='left')
            see_all_btn = tk.Label(hdr_row, text="Виж всичко →",
                                   font=("Helvetica", 9, "bold"),
                                   fg=ACCENT2, bg=SURFACE, cursor="hand2")
            see_all_btn.pack(side='right')
            see_all_btn.bind("<Button-1>", lambda _: self._show_page("history"))

            recent = sorted(self.history_data, key=lambda x: x['date'], reverse=True)[:6]
            for e in recent:
                r = tk.Frame(body_f, bg=SURFACE2)
                r.pack(fill='x', pady=2)
                mode_icons = {"car":"🚗","bus":"🚌","train":"🚆",
                              "bicycle":"🚲","walking":"🚶","":"🌍"}
                icon = mode_icons.get(e['transport_mode'], "🌍")
                lbl(r, f"  {icon}  {e['date'].strftime('%d.%m.%Y')}",
                    font=("Helvetica", 9), fg=TEXTDIM, bg=SURFACE2).pack(
                    side='left', padx=6, pady=7)
                co2_clr = GREEN if e['total_co2'] < 10 else WARN if e['total_co2'] < 50 else ERROR
                lbl(r, f"{e['total_co2']:.1f} kg CO₂  ",
                    font=("Helvetica", 9, "bold"), fg=co2_clr, bg=SURFACE2).pack(
                    side='right', padx=8)
        else:
            # Голям empty-state CTA за нови потребители
            cta = card(inner, accent_color=GREEN)
            cta.pack(fill='x', padx=18, pady=8)
            cta_b = tk.Frame(cta, bg=SURFACE)
            cta_b.pack(fill='both', expand=True, padx=24, pady=24)

            lbl(cta_b, "👋  Добре дошъл в ЕкоСледа!",
                font=("Helvetica", 16, "bold"), fg=WHITE, bg=SURFACE).pack(anchor='w')
            lbl(cta_b,
                "Започни да следиш своя въглероден отпечатък.\n"
                "Добави първия запис чрез Калкулатора или Картата.",
                font=("Helvetica", 10), fg=TEXTDIM, bg=SURFACE, justify='left').pack(
                anchor='w', pady=(8, 16))

            btns_row = tk.Frame(cta_b, bg=SURFACE)
            btns_row.pack(anchor='w')
            b1 = tk.Button(btns_row, text="🧮  Отвори Калкулатора",
                           command=lambda: self._show_page("calculator"))
            sty_btn(b1, accent=True)
            b1.pack(side='left', padx=(0, 10))
            b2 = tk.Button(btns_row, text="🗺️  Отвори Картата",
                           command=lambda: self._show_page("map"))
            sty_btn(b2)
            b2.pack(side='left')

    def _stat_pill(self, parent, label, value, color=None):
        color = color or ACCENT
        f = tk.Frame(parent, bg=SURFACE3, bd=0)
        f.pack(anchor='e', pady=6, padx=10)
        tk.Frame(f, bg=color, width=3).pack(side='left', fill='y')
        inner = tk.Frame(f, bg=SURFACE3)
        inner.pack(side='left', padx=10, pady=8)
        lbl(inner, label, font=("Helvetica", 8), fg=TEXTDIM, bg=SURFACE3).pack(anchor='w')
        lbl(inner, value, font=("Helvetica", 15, "bold"), fg=color, bg=SURFACE3).pack(anchor='w')

    def _empty_state(self, parent, icon, title, subtitle, compact=False):
        """Renders a styled empty-state placeholder inside the given parent frame."""
        f = tk.Frame(parent, bg=SURFACE2, bd=0)
        f.pack(fill='x', padx=14, pady=8 if compact else 20)
        pad_y = (12, 4) if compact else (28, 8)
        lbl(f, icon, font=("Helvetica", 32 if compact else 48), bg=SURFACE2).pack(pady=pad_y)
        lbl(f, title, font=("Georgia", 12 if compact else 14, "bold"),
            fg=ACCENT, bg=SURFACE2).pack()
        lbl(f, subtitle, font=("Helvetica", 9 if compact else 10),
            fg=TEXTDIM, bg=SURFACE2, justify='center').pack(pady=(4, 20 if not compact else 12))

    # ──────────────────────────────────────────────
    #  TAB: CALCULATOR
    # ──────────────────────────────────────────────
    def _create_calculator_tab(self):
        tab = tk.Frame(self._content, bg=BG)
        self._pages["calculator"] = tab
        _, inner = self._scrollable(tab)

        # header
        hc = card(inner, accent_color=ACCENT2)
        hc.pack(fill='x', padx=18, pady=(16, 4))
        hb = tk.Frame(hc, bg=SURFACE)
        hb.pack(fill='x', padx=20, pady=14)
        lbl(hb, "Калкулатор за Въглероден Отпечатък", font=FONT_HEAD,
            fg=WHITE, bg=SURFACE).pack(anchor='w')
        lbl(hb, "Изчисли въздействието от транспорт, електричество и отопление",
            font=FONT_SUB, fg=TEXTDIM, bg=SURFACE).pack(anchor='w', pady=(2, 0))

        # ── Transport card ──
        tc = card(inner, accent_color=GREEN)
        tc.pack(fill='x', padx=18, pady=8)
        body = tk.Frame(tc, bg=SURFACE)
        body.pack(fill='both', expand=True, padx=16, pady=16)

        lbl(body, "🚗  Транспорт", font=("Helvetica", 13, "bold"), fg=GREEN, bg=SURFACE).pack(anchor='w', pady=(0, 10))

        self.start_var = tk.StringVar()
        self.end_var   = tk.StringVar()
        self.transport_var = tk.StringVar(value="car")

        lbl(body, "Начало:", font=("Helvetica", 9), fg=TEXTDIM, bg=SURFACE).pack(anchor='w')
        entry_widget(body, self.start_var, width=44).pack(anchor='w', pady=(2, 8))

        lbl(body, "Дестинация:", font=("Helvetica", 9), fg=TEXTDIM, bg=SURFACE).pack(anchor='w')
        entry_widget(body, self.end_var, width=44).pack(anchor='w', pady=(2, 12))

        lbl(body, "Превозно средство:", font=("Helvetica", 9), fg=TEXTDIM, bg=SURFACE).pack(anchor='w', pady=(0, 6))
        trans_row = tk.Frame(body, bg=SURFACE)
        trans_row.pack(anchor='w')
        for txt, val in [("🚗 Кола","car"),("🚌 Автобус","bus"),("🚆 Влак","train"),
                         ("🚲 Колело","bicycle"),("🚶 Пеша","walking")]:
            ttk.Radiobutton(trans_row, text=txt, variable=self.transport_var, value=val).pack(side='left', padx=6)

        # ── Electricity card ──
        ec = card(inner, accent_color=WARN)
        ec.pack(fill='x', padx=18, pady=8)
        ebody = tk.Frame(ec, bg=SURFACE)
        ebody.pack(fill='both', expand=True, padx=16, pady=16)

        lbl(ebody, "💡  Електричество", font=("Helvetica", 13, "bold"), fg=WARN, bg=SURFACE).pack(anchor='w', pady=(0, 10))
        lbl(ebody, "Месечна консумация (kWh):", font=("Helvetica", 9), fg=TEXTDIM, bg=SURFACE).pack(anchor='w')
        self.electricity_var = tk.StringVar()
        entry_widget(ebody, self.electricity_var, width=20).pack(anchor='w', pady=(2, 4))
        lbl(ebody, "Средно домакинство: ~0.5 kg CO₂/kWh",
            font=("Helvetica", 8), fg=DIM, bg=SURFACE).pack(anchor='w', pady=(4, 0))


        # ── Heating card ──
        hec = card(inner, accent_color=ERROR)
        hec.pack(fill='x', padx=18, pady=8)
        hebod = tk.Frame(hec, bg=SURFACE)
        hebod.pack(fill='both', expand=True, padx=16, pady=16)

        lbl(hebod, "🏠  Отопление и Газ", font=("Helvetica", 13, "bold"), fg=ERROR, bg=SURFACE).pack(anchor='w', pady=(0, 10))

        row3 = tk.Frame(hebod, bg=SURFACE)
        row3.pack(fill='x', pady=(0, 8))
        left3 = tk.Frame(row3, bg=SURFACE)
        left3.pack(side='left', fill='x', expand=True, padx=(0, 16))
        right3 = tk.Frame(row3, bg=SURFACE)
        right3.pack(side='left', fill='x', expand=True)

        lbl(left3, "Природен газ (м³/месец):", font=("Helvetica", 9), fg=TEXTDIM, bg=SURFACE).pack(anchor='w')
        self.gas_var = tk.StringVar(value="0")
        entry_widget(left3, self.gas_var, width=10).pack(anchor='w', pady=(2, 0), ipady=3)
        lbl(left3, "~2.0 kg CO₂ на м³", font=("Helvetica", 8), fg=DIM, bg=SURFACE).pack(anchor='w')

        lbl(right3, "Централно парно (месеца активно):", font=("Helvetica", 9), fg=TEXTDIM, bg=SURFACE).pack(anchor='w')
        self.heating_months_var = tk.StringVar(value="0")
        entry_widget(right3, self.heating_months_var, width=10).pack(anchor='w', pady=(2, 0), ipady=3)
        lbl(right3, "~120 kg CO₂ на месец", font=("Helvetica", 8), fg=DIM, bg=SURFACE).pack(anchor='w')

        lbl(hebod, "Дърва/пелети (кг/месец):", font=("Helvetica", 9), fg=TEXTDIM, bg=SURFACE).pack(anchor='w', pady=(8, 0))
        self.wood_var = tk.StringVar(value="0")
        entry_widget(hebod, self.wood_var, width=14).pack(anchor='w', pady=(2, 0), ipady=3)
        lbl(hebod, "~0.4 kg CO₂ на кг дърва", font=("Helvetica", 8), fg=DIM, bg=SURFACE).pack(anchor='w')

        # ── Calculate button ──
        btn_row = tk.Frame(inner, bg=BG)
        btn_row.pack(fill='x', padx=18, pady=12)
        calc_btn = tk.Button(btn_row, text="  ⚡  Изчисли моя отпечатък  ",
                             command=self._calculate_footprint)
        sty_btn(calc_btn, accent=True)
        calc_btn.pack(side='left')

        # ── Result card ──
        self.result_card = card(inner)
        self.result_card.pack(fill='x', padx=18, pady=8)
        tk.Frame(self.result_card, bg=DIM, height=1).pack(fill='x')
        self.result_inner = tk.Frame(self.result_card, bg=SURFACE)
        self.result_inner.pack(fill='x', padx=20, pady=16)
        lbl(self.result_inner, "Попълни формата, за да видиш резултатите.",
            font=FONT_BODY, fg=TEXTDIM, bg=SURFACE).pack(anchor='w')

    # ── Calculation logic ──
    def _calculate_footprint(self):
        start_location = self.start_var.get().strip()
        end_location   = self.end_var.get().strip()
        transport_mode = self.transport_var.get()

        travel_co2    = 0.0
        start_lat_lon = end_lat_lon = None
        road_dist_km  = None
        road_dur_min  = None
        road_geom     = None
        straight_km   = None
        used_road     = False

        if start_location and end_location:
            # ── Use pre-fetched route from map tab if available ──
            prefill = getattr(self, '_prefilled_route', None)
            if (prefill
                    and self.start_var.get().strip() == start_location
                    and self.end_var.get().strip() == end_location):
                start_lat_lon = (prefill['start_lat'], prefill['start_lng'])
                end_lat_lon   = (prefill['end_lat'],   prefill['end_lng'])
                straight_km   = geodesic(start_lat_lon, end_lat_lon).kilometers
                road_dist_km  = prefill.get('road_dist_km')
                road_dur_min  = prefill.get('road_dur_min')
                used_road     = prefill.get('is_road_route', road_dist_km is not None)
                road_geom     = None  # geometry already shown in map tab
                distance      = road_dist_km if road_dist_km else straight_km
                self._prefilled_route = None  # consume it
            else:
                # ── Fresh geocode + OSRM routing ──
                # Show loading state
                for w in self.result_inner.winfo_children():
                    w.destroy()
                lbl(self.result_inner, "⏳  Изчислявам маршрута по улиците…",
                    font=FONT_BODY, fg=TEXTDIM, bg=SURFACE).pack(anchor='w')
                self.root.update()

                geolocator = Nominatim(user_agent="eko_otpechatuk_v3")
                try:
                    sc = geolocator.geocode(start_location)
                    ec = geolocator.geocode(end_location)
                except Exception as e:
                    messagebox.showerror("Грешка", f"Геокодирането неуспешно: {e}")
                    return
                if not sc or not ec:
                    messagebox.showerror("Грешка", "Не може да намери едно от местоположенията.")
                    return

                start_lat_lon = (sc.latitude, sc.longitude)
                end_lat_lon   = (ec.latitude, ec.longitude)
                straight_km   = geodesic(start_lat_lon, end_lat_lon).kilometers

                route_result = get_road_route(start_lat_lon, end_lat_lon, transport_mode)
                if route_result:
                    road_dist_km, road_dur_min, road_geom = route_result
                    used_road = True
                    distance  = road_dist_km
                else:
                    distance  = straight_km

            factors = {"car": 0.12, "bus": 0.05, "train": 0.03,
                       "bicycle": 0.0, "walking": 0.0}
            travel_co2 = distance * factors.get(transport_mode, 0.12)

        electricity_co2 = 0.0
        elec_str = self.electricity_var.get().strip()
        if elec_str:
            try:
                electricity_co2 = float(elec_str) * 0.5
            except ValueError:
                messagebox.showerror("Грешка", "Невалидна стойност за електричество.")
                return

        # ── Отопление ──
        heating_co2 = 0.0
        try:
            heating_co2 += float(self.gas_var.get() or 0) * 2.0
            heating_co2 += float(self.heating_months_var.get() or 0) * 120
            heating_co2 += float(self.wood_var.get() or 0) * 0.4
        except ValueError:
            messagebox.showerror("Грешка", "Невалидна стойност за отопление.")
            return

        total_co2 = travel_co2 + electricity_co2 + heating_co2

        entry = {
            'date':            datetime.now(),
            'travel_co2':      travel_co2,
            'electricity_co2': electricity_co2 + heating_co2,
            'total_co2':       total_co2,
            'start_location':  start_location,
            'end_location':    end_location,
            'transport_mode':  transport_mode,
            # Допълнителни категории (само в паметта)
            'heating_co2':     heating_co2,
            'pure_elec_co2':   electricity_co2,
        }
        self.history_data.append(entry)
        save_entry(self.user_id, entry)

        # ── Rebuild result card ──
        for w in self.result_inner.winfo_children():
            w.destroy()

        tk.Frame(self.result_inner, bg=ACCENT2, height=2).pack(fill='x', pady=(0, 12))
        lbl(self.result_inner, f"📊 Твоят отпечатък  —  {total_co2:.2f} kg CO₂",
            font=("Georgia", 14, "bold"), fg=ACCENT, bg=SURFACE).pack(anchor='w')

        # Distance row — show road vs straight-line if available
        if used_road and straight_km is not None:
            dist_row = tk.Frame(self.result_inner, bg=SURFACE)
            dist_row.pack(fill='x', pady=3)
            lbl(dist_row, "🛣️  Разстояние по улиците",
                font=FONT_BODY, fg=TEXTDIM, bg=SURFACE).pack(side='left')
            lbl(dist_row, f"{road_dist_km:.2f} km",
                font=("Helvetica", 11, "bold"), fg=TEXT, bg=SURFACE).pack(side='right')

            straight_row = tk.Frame(self.result_inner, bg=SURFACE)
            straight_row.pack(fill='x', pady=1)
            lbl(straight_row, "📐  Право разстояние",
                font=("Helvetica", 9), fg=DIM, bg=SURFACE).pack(side='left')
            lbl(straight_row, f"{straight_km:.2f} km",
                font=("Helvetica", 9), fg=DIM, bg=SURFACE).pack(side='right')

            if road_dur_min is not None:
                dur_row = tk.Frame(self.result_inner, bg=SURFACE)
                dur_row.pack(fill='x', pady=1)
                h, m = divmod(int(road_dur_min), 60)
                dur_str = f"{h}ч {m}мин" if h else f"{m} мин"
                lbl(dur_row, "⏱️  Прибл. време",
                    font=("Helvetica", 9), fg=DIM, bg=SURFACE).pack(side='left')
                lbl(dur_row, dur_str,
                    font=("Helvetica", 9), fg=DIM, bg=SURFACE).pack(side='right')

            tk.Frame(self.result_inner, bg=SURFACE2, height=1).pack(fill='x', pady=6)
        elif start_lat_lon and straight_km:
            # Only straight-line (OSRM unavailable)
            dist_row = tk.Frame(self.result_inner, bg=SURFACE)
            dist_row.pack(fill='x', pady=3)
            lbl(dist_row, "📐  Разстояние (право)",
                font=FONT_BODY, fg=TEXTDIM, bg=SURFACE).pack(side='left')
            lbl(dist_row, f"{straight_km:.2f} km  ⚠️ без интернет",
                font=("Helvetica", 11, "bold"), fg=WARN, bg=SURFACE).pack(side='right')
            tk.Frame(self.result_inner, bg=SURFACE2, height=1).pack(fill='x', pady=6)

        rows = [
            ("🚗 Транспорт",          f"{travel_co2:.2f} kg CO₂"),
            ("💡 Електричество",       f"{electricity_co2:.2f} kg CO₂"),
            ("🏠 Отопление и газ",     f"{heating_co2:.2f} kg CO₂"),
            ("🌍 Общо",                f"{total_co2:.2f} kg CO₂"),
        ]
        for lab, val in rows:
            r = tk.Frame(self.result_inner, bg=SURFACE)
            r.pack(fill='x', pady=3)
            lbl(r, lab, font=FONT_BODY, fg=TEXTDIM, bg=SURFACE).pack(side='left')
            lbl(r, val, font=("Helvetica", 11, "bold"), fg=TEXT, bg=SURFACE).pack(side='right')

        # Source note
        src = "🛣️ Изчислено по реален маршрут (OSRM)" if used_road else "📐 Изчислено по право разстояние"
        lbl(self.result_inner, src, font=("Helvetica", 8), fg=DIM, bg=SURFACE).pack(anchor='w', pady=(8, 0))

        self._display_personalized_tips(total_co2, travel_co2, electricity_co2, heating_co2=heating_co2)

        if start_lat_lon and end_lat_lon:
            self._generate_map(start_lat_lon, end_lat_lon,
                               start_location, end_location,
                               road_geom=road_geom,
                               road_dist_km=road_dist_km,
                               road_dur_min=road_dur_min,
                               straight_km=straight_km)
        self._refresh_all()
        self._show_toast(f"✅ Записано! Общо CO₂: {total_co2:.2f} kg", ACCENT2)

    def _display_personalized_tips(self, total_co2, travel_co2, electricity_co2,
                                    heating_co2=0):
        tips = []
        if total_co2 > 500:
            tips.append("🌟 Отпечатъкът ти е висок. Съсредоточи се върху намаляване.")
        elif total_co2 > 200:
            tips.append("🌟 Справяш се добре — има място за подобрение!")
        else:
            tips.append("🌟 Отличен отпечатък! Продължавай!")
        if travel_co2 > 30:
            tips.append("🚗 Обмисли алтернативен транспорт.")
        if electricity_co2 > 80:
            tips.append("💡 Висока консумация на ток — потърси как да спестиш.")
        if heating_co2 > 100:
            tips.append("🏠 Топлоизолацията намалява разходите за отопление с до 40%.")

        try:
            self.personal_tips_text.config(state='normal')
            self.personal_tips_text.delete(1.0, tk.END)
            self.personal_tips_text.insert(tk.END, "\n".join(tips))
            self.personal_tips_text.config(state='disabled')
        except AttributeError:
            pass

    def _generate_map(self, sc, ec, sn, en,
                       road_geom=None, road_dist_km=None,
                       road_dur_min=None, straight_km=None):
        """Update map tab and open browser map with real road polyline if available."""
        dist_for_preview = road_dist_km if road_dist_km else (straight_km or geodesic(sc, ec).kilometers)
        factors = {"car": 0.12, "bus": 0.05, "train": 0.03,
                   "bicycle": 0.0, "walking": 0.0}
        co2 = dist_for_preview * factors.get(self.transport_var.get(), 0.12)

        fake_data = {
            'start_lat': sc[0], 'start_lng': sc[1], 'start_name': sn,
            'end_lat':   ec[0], 'end_lng':   ec[1], 'end_name':   en,
            'road_dist_km': road_dist_km,
            'road_dur_min': road_dur_min,
            'straight_km':  straight_km,
        }
        self._map_data = fake_data

        self._map_draw_route_preview(sc[0], sc[1], ec[0], ec[1],
                                      sn, en, dist_for_preview, co2,
                                      road_geom=road_geom)
        try:
            self._map_update_ui(fake_data)
        except Exception:
            pass

        # Build browser map HTML with real road polyline
        html = build_map_html(sc, ec, sn, en, road_geom=road_geom)
        path = os.path.join(tempfile.gettempdir(), "eko_map.html")
        with open(path, 'w', encoding='utf-8') as f:
            f.write(html)
        webbrowser.open_new_tab(f"file://{path}")

    # ──────────────────────────────────────────────
    #  TAB: MAP
    # ──────────────────────────────────────────────
    def _create_map_tab(self):
        # Register map callback via map_server
        tab = tk.Frame(self._content, bg=BG)
        self._pages["map"] = tab

        # ── Header ──
        hdr = tk.Frame(tab, bg=SURFACE, height=52)
        hdr.pack(fill='x', side='top')
        hdr.pack_propagate(False)
        tk.Frame(hdr, bg=ACCENT2, height=3).pack(fill='x', side='top')
        row = tk.Frame(hdr, bg=SURFACE)
        row.pack(fill='x', padx=14, pady=8)

        lbl(row, "🗺️  Интерактивна Карта", font=("Helvetica", 12, "bold"),
            fg=TEXT, bg=SURFACE).pack(side='left')

        # Status label in header
        self.map_status_lbl = lbl(row, "Отвори картата и кликни за маршрут",
                                  font=("Helvetica", 9), fg=TEXTDIM, bg=SURFACE)
        self.map_status_lbl.pack(side='left', padx=18)

        open_btn = tk.Button(row, text="🌐  Отвори Картата в Браузъра",
                             command=self._open_map_browser)
        sty_btn(open_btn, accent=True)
        open_btn.pack(side='right')

        # ── Instruction card ──
        inst = tk.Frame(tab, bg=SURFACE2, bd=0)
        inst.pack(fill='x', padx=14, pady=6)

        steps = [
            ("1️⃣", "Натисни \"Отвори Картата\""),
            ("2️⃣", "Кликни на началната точка (зелен маркер)"),
            ("3️⃣", "Кликни на крайната точка (червен маркер)"),
            ("4️⃣", "Натисни \"Потвърди маршрута\" в браузъра"),
            ("5️⃣", "Калкулаторът се попълва автоматично!"),
        ]
        steps_row = tk.Frame(inst, bg=SURFACE2)
        steps_row.pack(fill='x', padx=16, pady=14)
        for icon, text in steps:
            sc = tk.Frame(steps_row, bg=SURFACE)
            sc.pack(side='left', expand=True, fill='x', padx=4)
            lbl(sc, icon, font=("Helvetica", 20), bg=SURFACE).pack(pady=(10, 2))
            lbl(sc, text, font=("Helvetica", 8), fg=TEXTDIM, bg=SURFACE,
                wraplength=120, justify='center').pack(pady=(0, 10))

        # ── Live preview of chosen route ──
        preview_outer = tk.Frame(tab, bg=BG)
        preview_outer.pack(fill='both', expand=True, padx=14, pady=6)

        # Left: current route info
        left_card = tk.Frame(preview_outer, bg=SURFACE, width=260)
        left_card.pack(side='left', fill='y', padx=(0, 6))
        left_card.pack_propagate(False)

        tk.Frame(left_card, bg=ACCENT2, width=4).pack(side='left', fill='y')
        left_body = tk.Frame(left_card, bg=SURFACE)
        left_body.pack(side='left', fill='both', expand=True, padx=12, pady=14)

        lbl(left_body, "📍  Текущ Маршрут",
            font=("Georgia", 11, "bold"), fg=TEXT, bg=SURFACE).pack(anchor='w', pady=(0, 10))

        self.map_start_lbl = lbl(left_body, "🟢  Начало: —",
                                  font=FONT_BODY, fg=TEXT, bg=SURFACE, wraplength=210, justify='left')
        self.map_start_lbl.pack(anchor='w', pady=4)

        self.map_end_lbl = lbl(left_body, "🔴  Край: —",
                                font=FONT_BODY, fg=TEXT, bg=SURFACE, wraplength=210, justify='left')
        self.map_end_lbl.pack(anchor='w', pady=4)

        tk.Frame(left_body, bg=SURFACE2, height=1).pack(fill='x', pady=10)

        self.map_dist_lbl = lbl(left_body, "📏  Разстояние: —",
                                 font=("Helvetica", 11, "bold"), fg=ACCENT, bg=SURFACE)
        self.map_dist_lbl.pack(anchor='w', pady=4)

        self.map_co2_lbl = lbl(left_body, "🌿  CO₂: —",
                                font=("Helvetica", 11, "bold"), fg=ACCENT, bg=SURFACE)
        self.map_co2_lbl.pack(anchor='w', pady=4)

        tk.Frame(left_body, bg=SURFACE2, height=1).pack(fill='x', pady=10)

        # Transport selector in map tab
        lbl(left_body, "Превозно средство:", font=("Helvetica", 9),
            fg=TEXTDIM, bg=SURFACE).pack(anchor='w')
        self.map_transport_var = tk.StringVar(value="car")
        for txt, val in [("🚗 Кола","car"),("🚌 Автобус","bus"),
                          ("🚆 Влак","train"),("🚲 Колело","bicycle"),("🚶 Пеша","walking")]:
            rb = ttk.Radiobutton(left_body, text=txt,
                                 variable=self.map_transport_var, value=val,
                                 command=self._map_recalc_co2)
            rb.pack(anchor='w', pady=1)

        tk.Frame(left_body, bg=SURFACE2, height=1).pack(fill='x', pady=10)

        send_btn = tk.Button(left_body, text="➡  Пренеси в Калкулатора",
                             command=self._map_send_to_calculator)
        sty_btn(send_btn, accent=True)
        send_btn.pack(fill='x', pady=4)

        open_btn2 = tk.Button(left_body, text="🔄  Отвори Картата",
                              command=self._open_map_browser)
        sty_btn(open_btn2)
        open_btn2.pack(fill='x', pady=4)

        # Right: mini matplotlib preview
        right_card = tk.Frame(preview_outer, bg=SURFACE)
        right_card.pack(side='left', fill='both', expand=True)
        self.map_preview_frame = right_card

        self._map_draw_empty_preview()

        # Store route data
        self._map_data = None
        self._prefilled_route = None

        # Register callback so browser map can send data back
        set_map_callback(self._on_map_coords_received)

    def _map_draw_empty_preview(self):
        for w in self.map_preview_frame.winfo_children():
            w.destroy()
        self._empty_state(self.map_preview_frame,
            "🗺️", "Картата не е отворена",
            "Натисни \"Отвори Картата\" и избери\nначална и крайна точка с щракване.")

    def _open_map_browser(self):
        """Write map HTML to temp file and open in default browser."""
        start_coords = end_coords = None
        start_name = end_name = ""
        if self._map_data:
            d = self._map_data
            start_coords = (d['start_lat'], d['start_lng'])
            end_coords   = (d['end_lat'],   d['end_lng'])
            start_name   = d.get('start_name', '')
            end_name     = d.get('end_name', '')

        html = build_map_html(start_coords, end_coords, start_name, end_name)
        path = os.path.join(tempfile.gettempdir(), "eko_map.html")
        with open(path, 'w', encoding='utf-8') as f:
            f.write(html)
        webbrowser.open_new_tab(f"file://{path}")
        self.map_status_lbl.config(
            text="⏳ Чакам избор на маршрут от браузъра…", fg=WARN)

    def _on_map_coords_received(self, data):
        """Called from the HTTP server thread when user clicks 'Confirm' in browser."""
        self._map_data = data
        # Schedule UI update on main thread
        self.root.after(0, lambda: self._map_update_ui(data))

    def _map_update_ui(self, data):
        sn = data.get('start_name', '')
        en = data.get('end_name', '')
        slat, slng = data['start_lat'], data['start_lng']
        elat, elng = data['end_lat'],   data['end_lng']

        # Prefer road distance if available (from browser or Python routing)
        road_km   = data.get('road_dist_km')
        dur_min   = data.get('road_dur_min')
        is_road   = data.get('is_road_route', road_km is not None)
        straight  = geodesic((slat, slng), (elat, elng)).kilometers
        dist_km   = road_km if road_km else straight

        factors = {"car": 0.12, "bus": 0.05, "train": 0.03,
                   "bicycle": 0.0, "walking": 0.0}
        mode = self.map_transport_var.get()
        co2  = dist_km * factors.get(mode, 0.12)

        def short(n): return n[:45] + "…" if len(n) > 45 else n

        route_label = "🛣️ По улиците" if is_road else "📐 Право (без интернет)"
        dist_label  = f"📏  {dist_km:.1f} km  ({route_label})"
        if dur_min:
            h, m = divmod(int(dur_min), 60)
            dur_str = f"{h}ч {m}мин" if h else f"{m} мин"
            dist_label += f"  ⏱️ {dur_str}"

        self.map_start_lbl.config(text=f"🟢  Начало: {short(sn)}")
        self.map_end_lbl.config(text=f"🔴  Край: {short(en)}")
        self.map_dist_lbl.config(text=dist_label)
        self.map_co2_lbl.config(text=f"🌿  CO₂: {co2:.2f} kg")
        self.map_status_lbl.config(
            text=f"✅ Маршрут: {dist_km:.1f} km по улиците" if is_road
                 else f"⚠️ Право: {dist_km:.1f} km",
            fg=ACCENT if is_road else WARN)

        road_geom = data.get('road_geom')  # may be None
        self._map_draw_route_preview(slat, slng, elat, elng,
                                      sn, en, dist_km, co2,
                                      road_geom=road_geom, is_road=is_road)

    def _map_recalc_co2(self):
        if not self._map_data:
            return
        d = self._map_data
        road_km  = d.get('road_dist_km')
        straight = geodesic((d['start_lat'], d['start_lng']),
                            (d['end_lat'],   d['end_lng'])).kilometers
        dist_km  = road_km if road_km else straight
        factors  = {"car": 0.12, "bus": 0.05, "train": 0.03,
                    "bicycle": 0.0, "walking": 0.0}
        co2 = dist_km * factors.get(self.map_transport_var.get(), 0.12)
        self.map_co2_lbl.config(text=f"🌿  CO₂: {co2:.2f} kg")

    def _map_draw_route_preview(self, slat, slng, elat, elng,
                                 sn, en, dist_km, co2,
                                 road_geom=None, is_road=False):
        for w in self.map_preview_frame.winfo_children():
            w.destroy()

        plt.rcParams['axes.facecolor']   = SURFACE
        plt.rcParams['figure.facecolor'] = SURFACE
        plt.rcParams['text.color']       = TEXT
        plt.rcParams['axes.labelcolor']  = TEXTDIM
        plt.rcParams['xtick.color']      = TEXTDIM
        plt.rcParams['ytick.color']      = TEXTDIM

        fig, ax = plt.subplots(figsize=(6, 4), dpi=96)
        fig.patch.set_facecolor(SURFACE)

        # Draw a simple map-style route line
        def short(n): return n.split(',')[0][:22]

        if road_geom and len(road_geom) > 1:
            # Draw the real road polyline
            road_lats = [p[0] for p in road_geom]
            road_lngs = [p[1] for p in road_geom]
            ax.plot(road_lngs, road_lats,
                    color=ACCENT, linewidth=2.5, zorder=2,
                    solid_capstyle='round', solid_joinstyle='round',
                    label="Маршрут по улиците")
            # Bounding box from road
            lat_pad = max((max(road_lats)-min(road_lats))*0.15, 0.005)
            lng_pad = max((max(road_lngs)-min(road_lngs))*0.15, 0.005)
            ax.set_xlim(min(road_lngs)-lng_pad, max(road_lngs)+lng_pad)
            ax.set_ylim(min(road_lats)-lat_pad, max(road_lats)+lat_pad)
            # Dashed straight-line for comparison
            ax.plot([slng, elng], [slat, elat],
                    color=DIM, linewidth=1.2, zorder=1,
                    linestyle='--', alpha=0.5, label="Право разстояние")
            route_label = "🛣️ По улиците"
        else:
            # Straight-line fallback (dashed, amber)
            ax.plot([slng, elng], [slat, elat],
                    color=WARN, linewidth=2.5, zorder=2, linestyle='--',
                    label="Право разстояние")
            lat_pad = max(abs(elat-slat)*0.3, 0.05)
            lng_pad = max(abs(elng-slng)*0.3, 0.05)
            ax.set_xlim(min(slng,elng)-lng_pad, max(slng,elng)+lng_pad)
            ax.set_ylim(min(slat,elat)-lat_pad, max(slat,elat)+lat_pad)
            route_label = "📐 Право"

        ax.scatter([slng], [slat], color="#22c55e", s=130, zorder=4)
        ax.scatter([elng], [elat], color="#ef4444", s=130, zorder=4)
        ax.annotate(f"  🟢 {short(sn)}", xy=(slng, slat),
                    fontsize=8, color="#22c55e", va='bottom')
        ax.annotate(f"  🔴 {short(en)}", xy=(elng, elat),
                    fontsize=8, color="#ef4444", va='bottom')

        # Centre-route annotation box
        if road_geom and len(road_geom) > 1:
            mid_idx = len(road_geom) // 2
            mid_lat, mid_lng = road_geom[mid_idx]
        else:
            mid_lat = (slat + elat) / 2
            mid_lng = (slng + elng) / 2

        ax.annotate(f"{route_label}\n{dist_km:.1f} km\n{co2:.2f} kg CO₂",
                    xy=(mid_lng, mid_lat), fontsize=8, color=TEXT,
                    ha='center', va='center',
                    bbox=dict(boxstyle='round,pad=0.5', facecolor=SURFACE2,
                              edgecolor=ACCENT2, alpha=0.92))

        title = "Реален маршрут по улиците" if (road_geom and is_road) else "Право разстояние (без интернет)"
        ax.set_title(title, fontsize=10, pad=8)
        ax.set_xlabel("Longitude", fontsize=7)
        ax.set_ylabel("Latitude", fontsize=7)
        ax.grid(True, linestyle='--', alpha=0.25)
        ax.legend(facecolor=SURFACE2, edgecolor=SURFACE2, fontsize=8)
        fig.tight_layout()

        cv = FigureCanvasTkAgg(fig, master=self.map_preview_frame)
        cv.draw()
        cv.get_tk_widget().pack(fill='both', expand=True)

    def _map_send_to_calculator(self):
        """Copy map route into calculator fields and switch tab."""
        if not self._map_data:
            messagebox.showinfo("Няма маршрут",
                "Моля, първо избери маршрут от картата.")
            return
        d = self._map_data
        self.start_var.set(d.get('start_name', ''))
        self.end_var.set(d.get('end_name', ''))
        self.transport_var.set(self.map_transport_var.get())
        # Store pre-computed road route so calculator skips geocoding/routing
        self._prefilled_route = {
            'start_lat': d['start_lat'], 'start_lng': d['start_lng'],
            'end_lat':   d['end_lat'],   'end_lng':   d['end_lng'],
            'road_dist_km': d.get('road_dist_km'),
            'road_dur_min': d.get('road_dur_min'),
            'is_road_route': d.get('is_road_route', d.get('road_dist_km') is not None),
        }
        # Switch to calculator tab (index 1)
        self._show_page("calculator")
        messagebox.showinfo("Готово",
            "Маршрутът е попълнен в Калкулатора!\n"
            "Натисни 'Изчисли' за да изчислиш CO₂.")

    # ──────────────────────────────────────────────
    #  TAB: PROGRESS
    # ──────────────────────────────────────────────
    def _create_progress_tab(self):
        tab = tk.Frame(self._content, bg=BG)
        self._pages["progress"] = tab
        _, inner = self._scrollable(tab)

        hc = card(inner, accent_color=ACCENT2)
        hc.pack(fill='x', padx=18, pady=(16, 4))
        hb = tk.Frame(hc, bg=SURFACE)
        hb.pack(fill='x', padx=20, pady=14)
        lbl(hb, "Твоят Годишен Прогрес", font=FONT_HEAD, fg=WHITE, bg=SURFACE).pack(anchor='w')
        lbl(hb, "Проследявай въглеродния си отпечатък във времето",
            font=FONT_SUB, fg=TEXTDIM, bg=SURFACE).pack(anchor='w', pady=(2, 0))

        # Summary pills
        sum_row = tk.Frame(inner, bg=BG)
        sum_row.pack(fill='x', padx=18, pady=8)
        self.sum_total  = self._pill_card(sum_row, "🌍 Общо CO₂",       "—")
        self.sum_travel = self._pill_card(sum_row, "🚗 Транспорт",       "—")
        self.sum_elec   = self._pill_card(sum_row, "💡 Електричество",   "—")

        btn_row = tk.Frame(inner, bg=BG)
        btn_row.pack(fill='x', padx=18, pady=4)
        rb = tk.Button(btn_row, text="🔄 Опресни", command=self._refresh_all)
        sty_btn(rb)
        rb.pack(side='left', padx=4)
        eb = tk.Button(btn_row, text="📤 Експортирай CSV", command=self._export_data)
        sty_btn(eb)
        eb.pack(side='left', padx=4)

        self.progress_frame = tk.Frame(inner, bg=BG)
        self.progress_frame.pack(fill='both', expand=True, padx=18, pady=8)

        self._update_progress()

    def _pill_card(self, parent, title, value):
        c = tk.Frame(parent, bg=SURFACE, bd=0)
        c.pack(side='left', expand=True, fill='x', padx=6, pady=4)
        lbl(c, title, font=("Helvetica", 9), fg=TEXTDIM, bg=SURFACE).pack(anchor='w', padx=14, pady=(12, 0))
        val_lbl = lbl(c, value, font=("Georgia", 18, "bold"), fg=ACCENT, bg=SURFACE)
        val_lbl.pack(anchor='w', padx=14, pady=(2, 12))
        return val_lbl

    def _update_progress(self):
        for w in self.progress_frame.winfo_children():
            w.destroy()

        if not self.history_data:
            self.sum_total.config(text="—")
            self.sum_travel.config(text="—")
            self.sum_elec.config(text="—")
            self._empty_state(self.progress_frame,
                "📈", "Все още няма записи",
                "Добави своя първи запис чрез Калкулатора,\nи тук ще се появят красиви графики!")
            return

        one_year_ago = datetime.now() - timedelta(days=365)
        yearly = sorted([e for e in self.history_data if e['date'] >= one_year_ago],
                        key=lambda x: x['date'])
        if not yearly:
            self._empty_state(self.progress_frame,
                "📅", "Няма данни за последната година",
                "Добави нови записи чрез Калкулатора.")
            return

        dates  = [e['date'] for e in yearly]
        totals = [e['total_co2'] for e in yearly]
        travel = [e['travel_co2'] for e in yearly]
        elec   = [e['electricity_co2'] for e in yearly]

        self.sum_total.config(text=f"{sum(totals):.1f} kg")
        self.sum_travel.config(text=f"{sum(travel):.1f} kg")
        self.sum_elec.config(text=f"{sum(elec):.1f} kg")

        plt.rcParams['axes.facecolor'] = SURFACE
        plt.rcParams['figure.facecolor'] = BG
        plt.rcParams['axes.edgecolor'] = SURFACE2
        plt.rcParams['text.color'] = TEXT
        plt.rcParams['axes.labelcolor'] = TEXTDIM
        plt.rcParams['xtick.color'] = TEXTDIM
        plt.rcParams['ytick.color'] = TEXTDIM
        plt.rcParams['grid.color'] = SURFACE2

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 7), dpi=96)
        fig.patch.set_facecolor(BG)

        ax1.plot(dates, totals, color=ACCENT, linewidth=2.5, marker='o', markersize=5)
        ax1.fill_between(dates, totals, alpha=0.15, color=ACCENT)
        ax1.set_title("Месечен Въглероден Отпечатък", fontsize=12, pad=10)
        ax1.set_ylabel("kg CO₂")
        ax1.grid(True, linestyle='--', alpha=0.3)

        w = 0.35
        x = range(len(dates))
        ax2.bar(x,             travel, w, label='Транспорт',     color=ACCENT2)
        ax2.bar([i+w for i in x], elec, w, label='Електричество', color=WARN)
        ax2.set_xticks([i+w/2 for i in x])
        ax2.set_xticklabels([d.strftime('%b') for d in dates], rotation=45, fontsize=7)
        ax2.set_title("Разбивка по Категория", fontsize=12, pad=10)
        ax2.set_ylabel("kg CO₂")
        ax2.legend(facecolor=SURFACE, edgecolor=SURFACE2)
        ax2.grid(True, linestyle='--', alpha=0.4, axis='y')

        fig.tight_layout(pad=3)

        canvas = FigureCanvasTkAgg(fig, master=self.progress_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill='both', expand=True)

    # ──────────────────────────────────────────────
    #  TAB: IMPACT
    # ──────────────────────────────────────────────
    def _create_impact_tab(self):
        tab = tk.Frame(self._content, bg=BG)
        self._pages["impact"] = tab
        _, inner = self._scrollable(tab)

        hc = card(inner, accent_color=GREEN)
        hc.pack(fill='x', padx=18, pady=(16, 4))
        hb = tk.Frame(hc, bg=SURFACE)
        hb.pack(fill='x', padx=20, pady=14)
        lbl(hb, "Твоето Въздействие върху Средата",
            font=FONT_HEAD, fg=WHITE, bg=SURFACE).pack(anchor='w')
        lbl(hb, "Разбери какво означава твоят отпечатък в реалния свят",
            font=FONT_SUB, fg=TEXTDIM, bg=SURFACE).pack(anchor='w', pady=(2, 0))

        self.impact_vis_frame = tk.Frame(inner, bg=BG)
        self.impact_vis_frame.pack(fill='x', padx=18, pady=8)

        self.impact_text_card = card(inner)
        self.impact_text_card.pack(fill='x', padx=18, pady=8)
        self.impact_text = tk.Text(self.impact_text_card,
                                   wrap=tk.WORD, height=14, width=80,
                                   font=FONT_BODY, padx=16, pady=12,
                                   bg=SURFACE, fg=TEXT, bd=0,
                                   insertbackground=ACCENT,
                                   selectbackground=ACCENT2, selectforeground=BG)
        self.impact_text.pack(fill='x')

        self._update_impact()

    def _update_impact(self):
        self.impact_text.config(state='normal')
        self.impact_text.delete(1.0, tk.END)

        if not self.history_data:
            self.impact_text.insert(tk.END, "Все още няма данни.\nДобави записи чрез Калкулатора!")
            self.impact_text.config(state='disabled')
            # Show empty state in visualization frame too
            for w in self.impact_vis_frame.winfo_children():
                w.destroy()
            self._empty_state(self.impact_vis_frame,
                "🌿", "Все още няма данни за въздействие",
                "След като добавиш записи, тук ще видиш\nкак се сравняваш с еталони.")
            return

        total = sum(e['total_co2'] for e in self.history_data)
        trees   = total / 21.77
        cars    = total / 2000
        homes   = total / 28.6
        phones  = total / 0.008
        flights = total / 200

        self.impact_text.insert(tk.END,
            f"🌍  Общо произведен CO₂: {total:.2f} kg\n\n"
            f"Еквивалентно на:\n\n"
            f"🌳  {trees:.1f} дървета за 1 година поглъщане\n"
            f"🚗  {cars:.1f} коли, спрени за 1 година\n"
            f"🏠  {homes:.1f} дома, захранвани за 1 ден\n"
            f"📱  {phones:,.0f} зареждания на смартфон\n"
            f"✈️   {flights:.1f} кратки полета (500 km)\n\n")

        if total < 1000:
            self.impact_text.insert(tk.END,
                "🌟  Отличен! Отпечатъкът ти е под средния.\n")
        else:
            self.impact_text.insert(tk.END,
                "💡  Има потенциал за подобрение — виж таба Съвети!\n")

        self.impact_text.config(state='disabled')
        self._update_impact_vis(total)

    def _update_impact_vis(self, total):
        for w in self.impact_vis_frame.winfo_children():
            w.destroy()

        plt.rcParams['axes.facecolor'] = SURFACE
        plt.rcParams['figure.facecolor'] = BG
        plt.rcParams['text.color'] = TEXT
        plt.rcParams['axes.labelcolor'] = TEXTDIM
        plt.rcParams['xtick.color'] = TEXTDIM
        plt.rcParams['ytick.color'] = TEXTDIM
        plt.rcParams['grid.color'] = SURFACE2

        fig, ax = plt.subplots(figsize=(9, 3.5), dpi=96)
        fig.patch.set_facecolor(BG)

        cats   = ['Твоят отпечатък', 'Средно (BG)', 'Еко-минималист']
        vals   = [total, 1400, 600]
        colors = [ACCENT2, "#4b5563", TEAL]
        bars = ax.barh(cats, vals, color=colors, height=0.5)

        for bar in bars:
            w = bar.get_width()
            ax.text(w + 10, bar.get_y() + bar.get_height()/2,
                    f'{w:.0f} kg', va='center', color=TEXT, fontsize=10)

        ax.set_xlabel("kg CO₂")
        ax.set_title("Сравнение с Еталони", fontsize=12)
        ax.grid(True, linestyle='--', alpha=0.4, axis='x')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        fig.tight_layout()

        cv = FigureCanvasTkAgg(fig, master=self.impact_vis_frame)
        cv.draw()
        cv.get_tk_widget().pack(fill='x')

    # ──────────────────────────────────────────────
    #  TAB: HISTORY  📋  (detailed table of all entries)
    # ──────────────────────────────────────────────
    def _create_history_tab(self):
        tab = tk.Frame(self._content, bg=BG)
        self._pages["history"] = tab

        hdr = tk.Frame(tab, bg=SURFACE)
        hdr.pack(fill='x', padx=0, pady=0)
        tk.Frame(hdr, bg=ACCENT2, height=3).pack(fill='x')
        hb = tk.Frame(hdr, bg=SURFACE)
        hb.pack(fill='x', padx=20, pady=12)
        lbl(hb, "📋  Детайлна История на Записите", font=FONT_HEAD, fg=TEXT, bg=SURFACE).pack(side='left')

        # Search bar
        search_f = tk.Frame(hb, bg=SURFACE)
        search_f.pack(side='right')
        lbl(search_f, "🔍", font=FONT_BODY, bg=SURFACE, fg=TEXTDIM).pack(side='left')
        self.history_search_var = tk.StringVar()
        self.history_search_var.trace('w', lambda *a: self._refresh_history_table())
        se = entry_widget(search_f, self.history_search_var, width=20)
        se.pack(side='left', padx=4, ipady=3)

        # Treeview
        style = ttk.Style()
        style.configure("History.Treeview",
                         background=SURFACE2, foreground=TEXT,
                         fieldbackground=SURFACE2, rowheight=32,
                         font=("Helvetica", 10))
        style.configure("History.Treeview.Heading",
                         background=SURFACE3, foreground=ACCENT,
                         font=("Helvetica", 10, "bold"), relief="flat")
        style.map("History.Treeview",
                  background=[('selected', ACCENT2)],
                  foreground=[('selected', BG)])

        cols = ("date", "transport", "travel_co2", "elec_co2", "total_co2", "from", "to")
        self.history_tree = ttk.Treeview(tab, columns=cols, show='headings',
                                          style="History.Treeview", height=20)
        headers = [("date","📅 Дата",110), ("transport","🚗 Транспорт",100),
                   ("travel_co2","🚗 CO₂ km",90), ("elec_co2","💡 CO₂ ток",90),
                   ("total_co2","🌍 Общо CO₂",100), ("from","📍 От",160), ("to","📍 До",160)]
        for col, head, w in headers:
            self.history_tree.heading(col, text=head)
            self.history_tree.column(col, width=w, anchor='center')

        vsb = ttk.Scrollbar(tab, orient="vertical", command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=vsb.set)
        self.history_tree.pack(side='left', fill='both', expand=True, padx=(12, 0), pady=8)
        vsb.pack(side='right', fill='y', pady=8, padx=(0, 8))

        self._refresh_history_table()

    def _refresh_history_table(self):
        if not hasattr(self, 'history_tree'):
            return
        self.history_tree.delete(*self.history_tree.get_children())
        query = self.history_search_var.get().lower() if hasattr(self, 'history_search_var') else ""
        mode_icons = {"car":"🚗","bus":"🚌","train":"🚆","bicycle":"🚲","walking":"🚶","":"—"}
        sorted_data = sorted(self.history_data, key=lambda x: x['date'], reverse=True)
        for e in sorted_data:
            row = (
                e['date'].strftime('%d.%m.%Y'),
                mode_icons.get(e['transport_mode'], e['transport_mode']),
                f"{e['travel_co2']:.2f} kg",
                f"{e['electricity_co2']:.2f} kg",
                f"{e['total_co2']:.2f} kg",
                e['start_location'][:30] or "—",
                e['end_location'][:30] or "—",
            )
            if query and not any(query in str(v).lower() for v in row):
                continue
            co2_val = e['total_co2']
            tag = "low" if co2_val < 10 else "mid" if co2_val < 50 else "high"
            self.history_tree.insert("", "end", values=row, tags=(tag,))
        self.history_tree.tag_configure("low",  background="#0a2a10", foreground=ACCENT3)
        self.history_tree.tag_configure("mid",  background="#2a2a00", foreground=WARN)
        self.history_tree.tag_configure("high", background="#2a0a0a", foreground=ERROR)

    # ──────────────────────────────────────────────
    #  TAB: COMPARE  ⚖️  (compare two time periods)
    # ──────────────────────────────────────────────
    def _create_compare_tab(self):
        tab = tk.Frame(self._content, bg=BG)
        self._pages["compare"] = tab
        _, inner = self._scrollable(tab)

        hc = card(inner, accent_color=TEAL)
        hc.pack(fill='x', padx=18, pady=(16, 4))
        hb = tk.Frame(hc, bg=SURFACE)
        hb.pack(fill='x', padx=20, pady=14)
        lbl(hb, "⚖️  Сравни Два Периода", font=FONT_HEAD, fg=TEXT, bg=SURFACE).pack(anchor='w')
        lbl(hb, "Избери два месеца или периода и виж разликата в CO₂",
            font=FONT_SUB, fg=TEXTDIM, bg=SURFACE).pack(anchor='w', pady=(2, 0))

        # Period selectors
        sel_row = tk.Frame(inner, bg=BG)
        sel_row.pack(fill='x', padx=18, pady=12)

        def period_card(parent, title, color, var_month, var_year):
            c = tk.Frame(parent, bg=SURFACE)
            tk.Frame(c, bg=color, height=3).pack(fill='x')
            b = tk.Frame(c, bg=SURFACE)
            b.pack(fill='x', padx=14, pady=12)
            lbl(b, title, font=("Helvetica", 11, "bold"), fg=color, bg=SURFACE).pack(anchor='w', pady=(0, 8))
            lbl(b, "Месец (1-12):", font=("Helvetica", 9), fg=TEXTDIM, bg=SURFACE).pack(anchor='w')
            entry_widget(b, var_month, width=8).pack(anchor='w', pady=(2, 6), ipady=3)
            lbl(b, "Година:", font=("Helvetica", 9), fg=TEXTDIM, bg=SURFACE).pack(anchor='w')
            entry_widget(b, var_year, width=8).pack(anchor='w', pady=(2, 0), ipady=3)
            return c

        self.cmp_m1 = tk.StringVar(value=str(datetime.now().month - 1 or 12))
        self.cmp_y1 = tk.StringVar(value=str(datetime.now().year))
        self.cmp_m2 = tk.StringVar(value=str(datetime.now().month))
        self.cmp_y2 = tk.StringVar(value=str(datetime.now().year))

        p1 = period_card(sel_row, "📅 Период 1", ACCENT2, self.cmp_m1, self.cmp_y1)
        p1.pack(side='left', expand=True, fill='x', padx=(0, 8))
        vs_lbl = tk.Frame(sel_row, bg=BG)
        vs_lbl.pack(side='left', padx=12)
        lbl(vs_lbl, "VS", font=("Helvetica", 20, "bold"), fg=WARN, bg=BG).pack(pady=20)
        p2 = period_card(sel_row, "📅 Период 2", TEAL, self.cmp_m2, self.cmp_y2)
        p2.pack(side='left', expand=True, fill='x', padx=(8, 0))

        cmp_btn = tk.Button(inner, text="  ⚖️  Сравни Периодите  ",
                            command=self._run_compare)
        sty_btn(cmp_btn, accent=True)
        cmp_btn.pack(pady=12)

        self.compare_result_frame = tk.Frame(inner, bg=BG)
        self.compare_result_frame.pack(fill='both', expand=True, padx=18, pady=8)

    def _run_compare(self):
        for w in self.compare_result_frame.winfo_children():
            w.destroy()
        try:
            m1, y1 = int(self.cmp_m1.get()), int(self.cmp_y1.get())
            m2, y2 = int(self.cmp_m2.get()), int(self.cmp_y2.get())
        except ValueError:
            lbl(self.compare_result_frame, "❌ Въведи валидни числа за месец и година",
                font=FONT_BODY, fg=ERROR, bg=BG).pack()
            return

        def period_data(m, y):
            return [e for e in self.history_data
                    if e['date'].month == m and e['date'].year == y]

        d1 = period_data(m1, y1)
        d2 = period_data(m2, y2)

        import calendar
        name1 = f"{calendar.month_name[m1]} {y1}"
        name2 = f"{calendar.month_name[m2]} {y2}"

        t1 = sum(e['total_co2'] for e in d1)
        t2 = sum(e['total_co2'] for e in d2)
        tr1 = sum(e['travel_co2'] for e in d1)
        tr2 = sum(e['travel_co2'] for e in d2)
        el1 = sum(e['electricity_co2'] for e in d1)
        el2 = sum(e['electricity_co2'] for e in d2)

        diff = t2 - t1
        diff_pct = ((t2 - t1) / t1 * 100) if t1 > 0 else 0
        diff_clr = GREEN if diff < 0 else ERROR
        diff_sym = "↓" if diff < 0 else "↑"

        # Summary cards
        sum_row = tk.Frame(self.compare_result_frame, bg=BG)
        sum_row.pack(fill='x', pady=8)

        for title, v1, v2, clr in [
            ("🌍 Общо CO₂", t1, t2, ACCENT2),
            ("🚗 Транспорт", tr1, tr2, GREEN),
            ("💡 Електричество", el1, el2, WARN),
        ]:
            cc = tk.Frame(sum_row, bg=SURFACE)
            cc.pack(side='left', expand=True, fill='x', padx=4)
            tk.Frame(cc, bg=clr, height=3).pack(fill='x')
            ib = tk.Frame(cc, bg=SURFACE)
            ib.pack(fill='x', padx=12, pady=10)
            lbl(ib, title, font=("Helvetica", 9), fg=TEXTDIM, bg=SURFACE).pack(anchor='w')
            lbl(ib, f"{v1:.1f} kg", font=("Helvetica", 14, "bold"), fg=ACCENT2, bg=SURFACE).pack(anchor='w')
            lbl(ib, f"→  {v2:.1f} kg", font=("Helvetica", 14, "bold"), fg=TEAL, bg=SURFACE).pack(anchor='w')
            d = v2 - v1
            dc = GREEN if d <= 0 else ERROR
            lbl(ib, f"{'↓' if d<=0 else '↑'} {abs(d):.1f} kg", font=("Helvetica", 10, "bold"),
                fg=dc, bg=SURFACE).pack(anchor='w', pady=(4, 0))

        # Verdict
        verdict_c = card(self.compare_result_frame, accent_color=diff_clr)
        verdict_c.pack(fill='x', pady=8)
        vb = tk.Frame(verdict_c, bg=SURFACE)
        vb.pack(fill='x', padx=16, pady=14)
        if diff < 0:
            msg = f"🎉 Браво! В {name2} си намалил CO₂ с {abs(diff):.1f} kg ({abs(diff_pct):.1f}%) спрямо {name1}!"
        elif diff > 0:
            msg = f"⚠️ В {name2} си увеличил CO₂ с {diff:.1f} kg ({diff_pct:.1f}%) спрямо {name1}."
        else:
            msg = f"➡️ Няма промяна между {name1} и {name2}."
        lbl(vb, msg, font=("Helvetica", 11, "bold"), fg=diff_clr, bg=SURFACE,
            wraplength=700, justify='left').pack(anchor='w')

        # Bar chart comparison
        if d1 or d2:
            plt.rcParams['axes.facecolor']   = SURFACE
            plt.rcParams['figure.facecolor'] = BG
            plt.rcParams['text.color']       = TEXT
            plt.rcParams['axes.labelcolor']  = TEXTDIM
            plt.rcParams['xtick.color']      = TEXTDIM
            plt.rcParams['ytick.color']      = TEXTDIM
            fig, ax = plt.subplots(figsize=(10, 3.5), dpi=96)
            fig.patch.set_facecolor(BG)
            cats = ['Общо CO₂', 'Транспорт', 'Електричество']
            vals1 = [t1, tr1, el1]
            vals2 = [t2, tr2, el2]
            x = range(len(cats))
            w = 0.35
            ax.bar(x, vals1, w, label=name1, color=ACCENT2, alpha=0.9)
            ax.bar([i+w for i in x], vals2, w, label=name2, color=TEAL, alpha=0.9)
            ax.set_xticks([i+w/2 for i in x])
            ax.set_xticklabels(cats)
            ax.set_ylabel("kg CO₂")
            ax.legend(facecolor=SURFACE2, edgecolor=DIM)
            ax.grid(True, linestyle='--', alpha=0.25, axis='y')
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            fig.tight_layout()
            cv = FigureCanvasTkAgg(fig, master=self.compare_result_frame)
            cv.draw()
            cv.get_tk_widget().pack(fill='x', padx=4, pady=8)

    # ──────────────────────────────────────────────
    #  TAB: ACHIEVEMENTS  🏆
    # ──────────────────────────────────────────────
    def _create_achievements_tab(self):
        tab = tk.Frame(self._content, bg=BG)
        self._pages["achievements"] = tab
        _, inner = self._scrollable(tab)

        hc = card(inner, accent_color=PURPLE)
        hc.pack(fill='x', padx=18, pady=(16, 4))
        hb = tk.Frame(hc, bg=SURFACE)
        hb.pack(fill='x', padx=20, pady=14)
        lbl(hb, "Твоите Постижения", font=FONT_HEAD, fg=WHITE, bg=SURFACE).pack(anchor='w')
        lbl(hb, "Спечели значки като намаляваш въглеродния си отпечатък",
            font=FONT_SUB, fg=TEXTDIM, bg=SURFACE).pack(anchor='w', pady=(2, 0))

        total_co2   = sum(e['total_co2']   for e in self.history_data)
        total_days  = len(set(e['date'].date() for e in self.history_data))
        total_entries = len(self.history_data)

        ACHIEVEMENTS = [
            ("🌱", "Първи стъпки",      "Добави първия си запис",         total_entries >= 1,       TEAL),
            ("🔥", "7-дневна серия",     "Записи 7 различни дни",          total_days >= 7,           WARN),
            ("🌍", "ЕкоСледа-осъзнат",        "Запиши над 100 kg CO₂ общо",     total_co2 >= 100,          ACCENT),
            ("🚲", "Зелен пътник",       "Използвай колело или ходи пеша", any(e['transport_mode'] in ('bicycle','walking') for e in self.history_data), GREEN),
            ("📊", "Анализатор",         "Добави 10 записа",               total_entries >= 10,       ACCENT3),
            ("🏆", "ЕкоСледа-шампион",        "30 дни активност",               total_days >= 30,          PURPLE),
            ("⚡", "Енергоспестител",    "Запиши електричество",           any(e['electricity_co2'] > 0 for e in self.history_data), WARN),
            ("🌳", "Гора от действия",   "100+ записа",                    total_entries >= 100,      GREEN),
            ("✈️",  "Без полети 30 дни", "30 записа без влак/самолет",      total_entries >= 30,       TEAL),
            ("💎", "Диамантен еко",      "365 дни активност",              total_days >= 365,         PINK),
        ]

        earned = sum(1 for *_, unlocked, _ in ACHIEVEMENTS if unlocked)

        # Progress bar
        prog_c = card(inner, accent_color=PURPLE)
        prog_c.pack(fill='x', padx=18, pady=8)
        pb = tk.Frame(prog_c, bg=SURFACE)
        pb.pack(fill='x', padx=16, pady=14)
        lbl(pb, f"Спечелени: {earned} / {len(ACHIEVEMENTS)}", font=("Helvetica", 12, "bold"),
            fg=WHITE, bg=SURFACE).pack(anchor='w', pady=(0, 8))
        # Progress bar bg
        bar_bg = tk.Frame(pb, bg=SURFACE3, height=12)
        bar_bg.pack(fill='x')
        pct = earned / len(ACHIEVEMENTS)
        bar_fill = tk.Frame(bar_bg, bg=PURPLE, height=12)
        bar_fill.place(relx=0, rely=0, relwidth=pct, relheight=1)
        lbl(pb, f"{pct*100:.0f}% завършено", font=("Helvetica", 8), fg=TEXTDIM, bg=SURFACE).pack(anchor='e', pady=(4, 0))

        # Achievements grid
        grid_f = tk.Frame(inner, bg=BG)
        grid_f.pack(fill='x', padx=18, pady=8)

        for i, (icon, name, desc, unlocked, clr) in enumerate(ACHIEVEMENTS):
            col = i % 2
            row_idx = i // 2
            if col == 0:
                row_frame = tk.Frame(grid_f, bg=BG)
                row_frame.pack(fill='x', pady=4)

            cell = tk.Frame(row_frame, bg=SURFACE if unlocked else SURFACE2, bd=0)
            cell.pack(side='left', expand=True, fill='x', padx=4)

            if unlocked:
                tk.Frame(cell, bg=clr, height=3).pack(fill='x')
            else:
                tk.Frame(cell, bg=DIM, height=3).pack(fill='x')

            inner_c = tk.Frame(cell, bg=SURFACE if unlocked else SURFACE2)
            inner_c.pack(fill='x', padx=14, pady=12)

            top_row = tk.Frame(inner_c, bg=inner_c.cget('bg'))
            top_row.pack(fill='x')

            icon_lbl = lbl(top_row, icon if unlocked else "🔒",
                           font=("Helvetica", 24),
                           bg=inner_c.cget('bg'),
                           fg=TEXT if unlocked else DIM)
            icon_lbl.pack(side='left', padx=(0, 10))

            txt_f = tk.Frame(top_row, bg=inner_c.cget('bg'))
            txt_f.pack(side='left', fill='x', expand=True)
            lbl(txt_f, name, font=("Helvetica", 10, "bold"),
                fg=clr if unlocked else DIM, bg=inner_c.cget('bg')).pack(anchor='w')
            lbl(txt_f, desc, font=("Helvetica", 8), fg=TEXTDIM if unlocked else DIM,
                bg=inner_c.cget('bg')).pack(anchor='w')

            status = "✅ Спечелено!" if unlocked else "🔒 Заключено"
            status_clr = clr if unlocked else DIM
            lbl(inner_c, status, font=("Helvetica", 8, "bold"), fg=status_clr,
                bg=inner_c.cget('bg')).pack(anchor='w', pady=(6, 0))

    # ──────────────────────────────────────────────
    #  TAB: GOALS  🎯
    # ──────────────────────────────────────────────
    def _create_goals_tab(self):
        tab = tk.Frame(self._content, bg=BG)
        self._pages["goals"] = tab
        _, inner = self._scrollable(tab)

        hc = card(inner, accent_color=GREEN)
        hc.pack(fill='x', padx=18, pady=(16, 4))
        hb = tk.Frame(hc, bg=SURFACE)
        hb.pack(fill='x', padx=20, pady=14)
        lbl(hb, "Моите CO₂ Цели", font=FONT_HEAD, fg=WHITE, bg=SURFACE).pack(anchor='w')
        lbl(hb, "Задай месечна цел и следи прогреса си",
            font=FONT_SUB, fg=TEXTDIM, bg=SURFACE).pack(anchor='w', pady=(2, 0))

        # Set goal
        set_c = card(inner, accent_color=TEAL)
        set_c.pack(fill='x', padx=18, pady=8)
        sb = tk.Frame(set_c, bg=SURFACE)
        sb.pack(fill='x', padx=16, pady=14)
        lbl(sb, "🎯  Задай Месечна Цел (kg CO₂)", font=("Helvetica", 12, "bold"),
            fg=WHITE, bg=SURFACE).pack(anchor='w', pady=(0, 10))

        goal_row = tk.Frame(sb, bg=SURFACE)
        goal_row.pack(fill='x')
        self.goal_var = tk.StringVar(value="100")
        entry_widget(goal_row, self.goal_var, width=12).pack(side='left', ipady=4)
        lbl(goal_row, " kg CO₂ на месец", font=FONT_BODY, fg=TEXTDIM, bg=SURFACE).pack(side='left', padx=8)
        save_goal_btn = tk.Button(goal_row, text="Запази целта", command=self._save_goal)
        sty_btn(save_goal_btn, success=True)
        save_goal_btn.pack(side='left', padx=8)

        # Current progress
        today = datetime.now()
        this_month = [e for e in self.history_data
                      if e['date'].month == today.month and e['date'].year == today.year]
        month_total = sum(e['total_co2'] for e in this_month)

        prog_c = card(inner, accent_color=GREEN)
        prog_c.pack(fill='x', padx=18, pady=8)
        pb_frame = tk.Frame(prog_c, bg=SURFACE)
        pb_frame.pack(fill='x', padx=16, pady=14)

        try:
            goal_val = float(self.goal_var.get())
        except Exception:
            goal_val = 100

        pct = min(month_total / goal_val, 1.0) if goal_val > 0 else 0
        bar_clr = GREEN if pct < 0.7 else WARN if pct < 1.0 else ERROR

        lbl(pb_frame, f"📅  {today.strftime('%B %Y')} — Напредък",
            font=("Helvetica", 12, "bold"), fg=WHITE, bg=SURFACE).pack(anchor='w', pady=(0, 10))

        nums_row = tk.Frame(pb_frame, bg=SURFACE)
        nums_row.pack(fill='x', pady=(0, 8))
        lbl(nums_row, f"{month_total:.1f} kg", font=FONT_LARGE, fg=bar_clr, bg=SURFACE).pack(side='left')
        lbl(nums_row, f" / {goal_val:.0f} kg цел", font=FONT_BODY, fg=TEXTDIM, bg=SURFACE).pack(side='left', pady=(8, 0))

        bar_bg = tk.Frame(pb_frame, bg=SURFACE3, height=20)
        bar_bg.pack(fill='x')
        fill_f = tk.Frame(bar_bg, bg=bar_clr, height=20)
        fill_f.place(relx=0, rely=0, relwidth=pct, relheight=1)

        remaining = goal_val - month_total
        if remaining > 0:
            status_txt = f"✅ Остават {remaining:.1f} kg до целта — продължавай!"
            status_clr = GREEN
        else:
            status_txt = f"⚠️ Надхвърлил си целта с {abs(remaining):.1f} kg!"
            status_clr = ERROR
        lbl(pb_frame, status_txt, font=("Helvetica", 10, "bold"), fg=status_clr, bg=SURFACE).pack(anchor='w', pady=(8, 0))

        # Preset goals
        preset_c = card(inner, accent_color=ACCENT2)
        preset_c.pack(fill='x', padx=18, pady=8)
        pr = tk.Frame(preset_c, bg=SURFACE)
        pr.pack(fill='x', padx=16, pady=14)
        lbl(pr, "💡  Препоръчани Цели", font=("Helvetica", 12, "bold"),
            fg=WHITE, bg=SURFACE).pack(anchor='w', pady=(0, 10))

        presets = [
            ("🌱 Начинаещ",     200, "Добра начална точка",     GREEN),
            ("🌍 Средно",       100, "Европейска средна норма",  ACCENT),
            ("⚡ ЕкоСледа-лидер",     50, "Под средното — отлично!", TEAL),
            ("💎 Нула-герой",    20, "Почти нулев отпечатък",   PURPLE),
        ]
        presets_row = tk.Frame(pr, bg=SURFACE)
        presets_row.pack(fill='x')
        for name, val, desc, clr in presets:
            pc = tk.Frame(presets_row, bg=SURFACE2)
            pc.pack(side='left', expand=True, fill='x', padx=4, pady=4)
            tk.Frame(pc, bg=clr, height=2).pack(fill='x')
            lbl(pc, name, font=("Helvetica", 9, "bold"), fg=clr, bg=SURFACE2).pack(anchor='w', padx=8, pady=(8, 2))
            lbl(pc, f"{val} kg/мес", font=("Helvetica", 13, "bold"), fg=WHITE, bg=SURFACE2).pack(anchor='w', padx=8)
            lbl(pc, desc, font=("Helvetica", 8), fg=TEXTDIM, bg=SURFACE2).pack(anchor='w', padx=8, pady=(2, 0))
            def make_setter(v):
                return lambda: self.goal_var.set(str(v))
            btn = tk.Button(pc, text="Избери", command=make_setter(val))
            sty_btn(btn)
            btn.pack(anchor='w', padx=8, pady=8)

    def _save_goal(self):
        try:
            val = float(self.goal_var.get())
            if val <= 0:
                raise ValueError
            messagebox.showinfo("🎯 Цел Запазена",
                f"Месечната ти цел е: {val:.0f} kg CO₂\n\nПродължавай да намаляваш отпечатъка си!")
        except ValueError:
            messagebox.showerror("Грешка", "Моля въведи валидна стойност (число > 0)")

    # ══════════════════════════════════════════════
    #  TAB: AI СЪВЕТНИК  🤖
    # ══════════════════════════════════════════════
    def _create_ai_tab(self):
        tab = tk.Frame(self._content, bg=BG)
        self._pages["ai"] = tab
        _, inner = self._scrollable(tab)

        # Header
        hc = card(inner, accent_color=PURPLE)
        hc.pack(fill='x', padx=18, pady=(16, 4))
        hb = tk.Frame(hc, bg=SURFACE)
        hb.pack(fill='x', padx=20, pady=14)
        lbl(hb, "🤖  AI Еко Съветник", font=FONT_HEAD, fg=WHITE, bg=SURFACE).pack(anchor='w')
        lbl(hb, "Питай Claude за персонализирани съвети за намаляване на CO₂",
            font=FONT_SUB, fg=TEXTDIM, bg=SURFACE).pack(anchor='w', pady=(2, 0))

        # API Key button
        key_row = tk.Frame(hb, bg=SURFACE)
        key_row.pack(anchor='w', pady=(8, 0))
        key_btn = tk.Button(key_row, text="🔑  Въведи Groq API Ключ (безплатен)",
                            command=self._ai_set_api_key)
        sty_btn(key_btn)
        key_btn.pack(side='left')
        self._ai_key_status = lbl(key_row, "", font=("Helvetica", 9), fg=GREEN, bg=SURFACE)
        self._ai_key_status.pack(side='left', padx=10)
        # Check if key is already set
        try:
            from config import GROQ_API_KEY
            if GROQ_API_KEY.strip():
                self._ai_key_status.config(text="✅ Groq API ключ е настроен", fg=GREEN)
            else:
                self._ai_key_status.config(text="⚠️ Липсва ключ — натисни бутона!", fg=WARN)
        except Exception:
            self._ai_key_status.config(text="⚠️ Липсва Groq API ключ", fg=WARN)

        # Stats summary for AI context
        total_co2   = sum(e['total_co2'] for e in self.history_data)
        avg_monthly = total_co2 / max(len(set(
            (e['date'].year, e['date'].month) for e in self.history_data
        )), 1) if self.history_data else 0
        transport_co2 = sum(e['travel_co2'] for e in self.history_data)
        elec_co2      = sum(e['electricity_co2'] for e in self.history_data)
        top_mode      = ""
        if self.history_data:
            modes = [e['transport_mode'] for e in self.history_data if e['transport_mode']]
            if modes:
                top_mode = max(set(modes), key=modes.count)

        # Context card
        ctx_c = card(inner, accent_color=SURFACE3)
        ctx_c.pack(fill='x', padx=18, pady=8)
        ctx_b = tk.Frame(ctx_c, bg=SURFACE)
        ctx_b.pack(fill='x', padx=16, pady=12)
        lbl(ctx_b, "📊  Твоят профил (изпраща се на AI):",
            font=("Helvetica", 10, "bold"), fg=TEXTDIM, bg=SURFACE).pack(anchor='w', pady=(0, 6))
        ctx_row = tk.Frame(ctx_b, bg=SURFACE)
        ctx_row.pack(fill='x')
        stats_info = [
            (f"{total_co2:.0f} kg", "Общо CO₂", ACCENT2),
            (f"{avg_monthly:.0f} kg", "На месец", TEAL),
            (top_mode or "—", "Транспорт", GREEN),
        ]
        for val, lab, clr in stats_info:
            sf = tk.Frame(ctx_row, bg=SURFACE2)
            sf.pack(side='left', expand=True, fill='x', padx=4, pady=2)
            lbl(sf, val, font=("Helvetica", 13, "bold"), fg=clr, bg=SURFACE2).pack(pady=(8, 2))
            lbl(sf, lab, font=("Helvetica", 8), fg=TEXTDIM, bg=SURFACE2).pack(pady=(0, 8))

        # Quick question buttons
        quick_c = card(inner, accent_color=PURPLE)
        quick_c.pack(fill='x', padx=18, pady=8)
        qb = tk.Frame(quick_c, bg=SURFACE)
        qb.pack(fill='x', padx=16, pady=12)
        lbl(qb, "⚡  Бързи въпроси:", font=("Helvetica", 10, "bold"),
            fg=WHITE, bg=SURFACE).pack(anchor='w', pady=(0, 8))
        quick_qs = [
            "Как да намаля транспортния CO₂?",
            "Дай ми 5 практични еко съвета",
            "Анализирай моите данни и препоръчай",
            "Как да достигна нулев отпечатък?",
            "Сравни ме с европейската средна норма",
        ]
        for i, q in enumerate(quick_qs):
            def make_cmd(question=q):
                return lambda: self._ai_ask(question)
            btn = tk.Button(qb, text=f"  {q}", command=make_cmd(),
                            anchor='w')
            sty_btn(btn)
            btn.pack(fill='x', pady=2, ipady=3)

        # Chat area
        chat_c = card(inner, accent_color=PURPLE)
        chat_c.pack(fill='x', padx=18, pady=8)
        chat_b = tk.Frame(chat_c, bg=SURFACE)
        chat_b.pack(fill='x', padx=16, pady=12)
        lbl(chat_b, "💬  Чат с AI Съветника",
            font=("Helvetica", 11, "bold"), fg=WHITE, bg=SURFACE).pack(anchor='w', pady=(0, 8))

        # Chat history display
        self._ai_chat_frame = tk.Frame(chat_b, bg=SURFACE2)
        self._ai_chat_frame.pack(fill='x', pady=(0, 8))
        self._ai_welcome_msg()

        # Input row
        inp_row = tk.Frame(chat_b, bg=SURFACE)
        inp_row.pack(fill='x')
        self._ai_input_var = tk.StringVar()
        ai_entry = entry_widget(inp_row, self._ai_input_var, width=60)
        ai_entry.pack(side='left', fill='x', expand=True, ipady=6)
        ai_entry.bind('<Return>', lambda _: self._ai_ask(self._ai_input_var.get()))
        ask_btn = tk.Button(inp_row, text="  Изпрати  →",
                            command=lambda: self._ai_ask(self._ai_input_var.get()))
        sty_btn(ask_btn, accent=True)
        ask_btn.pack(side='left', padx=(8, 0))

        clear_btn = tk.Button(inp_row, text="🗑",
                              command=self._ai_clear_chat)
        sty_btn(clear_btn)
        clear_btn.pack(side='left', padx=(4, 0))

    def _ai_set_api_key(self):
        """Диалог за въвеждане на Groq API ключ."""
        dialog = tk.Toplevel(self.root)
        dialog.title("🔑 Groq API Ключ (Безплатен)")
        dialog.geometry("520x340")
        dialog.configure(bg=BG)
        dialog.resizable(False, False)
        dialog.grab_set()

        tk.Frame(dialog, bg=PURPLE, height=4).pack(fill='x')
        body = tk.Frame(dialog, bg=BG)
        body.pack(fill='both', expand=True, padx=24, pady=20)

        lbl(body, "🔑  Groq API Ключ — НАПЪЛНО БЕЗПЛАТЕН",
            font=("Helvetica", 13, "bold"), fg=WHITE, bg=BG).pack(anchor='w')
        lbl(body,
            "1️⃣  Отиди на https://console.groq.com/\n"
            "2️⃣  Регистрирай се безплатно (с Google акаунт)\n"
            "3️⃣  Кликни 'API Keys' → 'Create API Key'\n"
            "4️⃣  Копирай ключа (започва с 'gsk_...') и го постави тук:",
            font=("Helvetica", 9), fg=TEXTDIM, bg=BG).pack(anchor='w', pady=(8, 10))

        # Current key display
        try:
            from config import GROQ_API_KEY as cur_key
        except Exception:
            cur_key = ""
        cur_key = getattr(self, '_groq_api_key', cur_key.strip())

        key_var = tk.StringVar(value=cur_key)
        key_entry = entry_widget(body, key_var, width=55)
        key_entry.pack(fill='x', ipady=6)

        status_lbl = lbl(body, "", font=("Helvetica", 9), fg=ERROR, bg=BG)
        status_lbl.pack(anchor='w', pady=(6, 0))

        btn_row = tk.Frame(body, bg=BG)
        btn_row.pack(fill='x', pady=(10, 0))

        def save_key():
            new_key = key_var.get().strip()
            if not new_key:
                status_lbl.config(text="❌ Въведи API ключ!", fg=ERROR)
                return
            if not new_key.startswith("gsk_"):
                status_lbl.config(text="⚠️ Groq ключът трябва да започва с 'gsk_...'", fg=WARN)
                return

            # Save in memory
            self._groq_api_key = new_key

            # Save to config.py
            try:
                cfg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.py")
                if not os.path.exists(cfg_path):
                    cfg_path = "config.py"
                with open(cfg_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                import re
                if 'GROQ_API_KEY' in content:
                    content = re.sub(
                        r'GROQ_API_KEY\s*=\s*["\'].*?["\']',
                        f'GROQ_API_KEY = "{new_key}"',
                        content
                    )
                else:
                    content += f'\nGROQ_API_KEY = "{new_key}"\n'
                with open(cfg_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                status_lbl.config(text="✅ Ключът е запазен успешно!", fg=GREEN)
            except Exception as e:
                status_lbl.config(text=f"✅ Запазен в паметта (файлова грешка: {e})", fg=WARN)

            # Update status in AI tab
            try:
                self._ai_key_status.config(text="✅ Groq API ключ е настроен", fg=GREEN)
            except Exception:
                pass

            dialog.after(1500, dialog.destroy)

        save_btn = tk.Button(btn_row, text="💾  Запази ключа", command=save_key)
        sty_btn(save_btn, accent=True)
        save_btn.pack(side='left')

        cancel_btn = tk.Button(btn_row, text="Отказ", command=dialog.destroy)
        sty_btn(cancel_btn)
        cancel_btn.pack(side='left', padx=(10, 0))

        link_lbl = tk.Label(body,
                            text="🌐  Отвори console.groq.com",
                            font=("Helvetica", 10, "underline"),
                            fg=ACCENT, bg=BG, cursor="hand2")
        link_lbl.pack(anchor='w', pady=(14, 0))
        link_lbl.bind("<Button-1>", lambda _: webbrowser.open("https://console.groq.com/"))

    def _ai_welcome_msg(self):
        msg = (f"Здравей, {self.user_name}! 🌿 Аз съм твоят AI ЕкоСледа-съветник.\n"
               "Мога да анализирам данните ти и да дам персонализирани съвети.\n"
               "Питай ме всичко за намаляване на CO₂!")
        self._ai_add_bubble("🤖 AI", msg, PURPLE, is_ai=True)

    def _ai_clear_chat(self):
        for w in self._ai_chat_frame.winfo_children():
            w.destroy()
        self._ai_welcome_msg()

    def _ai_add_bubble(self, sender, text, color, is_ai=False):
        bubble = tk.Frame(self._ai_chat_frame, bg=SURFACE3 if is_ai else SURFACE2)
        bubble.pack(fill='x', pady=3, padx=4)
        tk.Frame(bubble, bg=color, width=4).pack(side='left', fill='y')
        inner = tk.Frame(bubble, bg=bubble.cget('bg'))
        inner.pack(side='left', fill='both', expand=True, padx=10, pady=8)
        lbl(inner, sender, font=("Helvetica", 9, "bold"),
            fg=color, bg=inner.cget('bg')).pack(anchor='w')
        lbl(inner, text, font=("Helvetica", 10),
            fg=TEXT, bg=inner.cget('bg'),
            wraplength=680, justify='left').pack(anchor='w', pady=(3, 0))

    def _ai_ask(self, question: str):
        question = question.strip()
        if not question:
            return
        self._ai_input_var.set("")

        # Show user bubble
        self._ai_add_bubble(f"👤 {self.user_name}", question, ACCENT2, is_ai=False)

        # Show thinking bubble
        thinking = tk.Frame(self._ai_chat_frame, bg=SURFACE3)
        thinking.pack(fill='x', pady=3, padx=4)
        tk.Frame(thinking, bg=PURPLE, width=4).pack(side='left', fill='y')
        th_inner = tk.Frame(thinking, bg=SURFACE3)
        th_inner.pack(side='left', fill='x', padx=10, pady=8)
        th_lbl = lbl(th_inner, "🤖 AI  ⏳  Мисля...",
                     font=("Helvetica", 9), fg=TEXTDIM, bg=SURFACE3)
        th_lbl.pack(anchor='w')
        self.root.update()

        # Build context for Claude
        total_co2   = sum(e['total_co2'] for e in self.history_data)
        transport   = sum(e['travel_co2'] for e in self.history_data)
        elec        = sum(e['electricity_co2'] for e in self.history_data)
        months      = len(set((e['date'].year, e['date'].month)
                              for e in self.history_data)) or 1
        avg_month   = total_co2 / months
        modes = [e['transport_mode'] for e in self.history_data if e['transport_mode']]
        top_mode = max(set(modes), key=modes.count) if modes else "неизвестен"

        system_prompt = f"""Ти си AI ЕкоСледа-съветник в приложение ЕкоСледа.
Потребителят {self.user_name} има следните данни за CO₂:
- Общо CO₂: {total_co2:.1f} kg
- Транспорт CO₂: {transport:.1f} kg
- Електричество CO₂: {elec:.1f} kg
- Средно на месец: {avg_month:.1f} kg
- Най-използван транспорт: {top_mode}
- Брой записи: {len(self.history_data)}

Давай кратки, практични, персонализирани съвети на БЪЛГАРСКИ.
Бъди приятелски, конкретен и мотивиращ. Форматирай с емоджи."""

        def call_api():
            # Вземи Groq API ключа от config или от паметта
            try:
                from config import GROQ_API_KEY
                api_key = GROQ_API_KEY.strip()
            except Exception:
                api_key = ""
            if not api_key:
                api_key = getattr(self, '_groq_api_key', "").strip()

            # Ако ключът липсва, покажи инструкции
            if not api_key:
                answer = (
                    "⚠️ Липсва Groq API ключ!\n\n"
                    "Groq е БЕЗПЛАТЕН! Следвай стъпките:\n"
                    "1️⃣ Отиди на https://console.groq.com/\n"
                    "2️⃣ Регистрирай се безплатно (с Google или email)\n"
                    "3️⃣ Кликни 'API Keys' → 'Create API Key'\n"
                    "4️⃣ Копирай ключа (започва с 'gsk_...')\n"
                    "5️⃣ Натисни бутона '🔑 Въведи Groq API Ключ' по-горе"
                )
                def update_ui_no_key():
                    thinking.destroy()
                    self._ai_add_bubble("🤖 AI Съветник", answer, PURPLE, is_ai=True)
                self.root.after(0, update_ui_no_key)
                return

            try:
                resp = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {api_key}",
                    },
                    json={
                        "model": "llama-3.1-8b-instant",
                        "max_tokens": 600,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user",   "content": question},
                        ],
                    },
                    timeout=30,
                )
                data = resp.json()
                if "choices" in data and data["choices"]:
                    answer = data["choices"][0]["message"]["content"]
                elif "error" in data:
                    err_msg = data["error"].get("message", str(data["error"]))
                    if "auth" in err_msg.lower() or "api_key" in err_msg.lower() or "invalid" in err_msg.lower():
                        answer = (
                            "❌ Невалиден Groq API ключ!\n\n"
                            "Провери дали ключът е правилен (трябва да започва с 'gsk_...').\n"
                            "Отиди на https://console.groq.com/ за нов ключ.\n"
                            "После натисни '🔑 Въведи Groq API Ключ' и въведи новия."
                        )
                    else:
                        answer = f"⚠️ Грешка от Groq: {err_msg}"
                else:
                    answer = "⚠️ Не можах да получа отговор. Провери интернет връзката."
            except requests.exceptions.ConnectionError:
                answer = (
                    "⚠️ Няма интернет връзка!\n\n"
                    "Провери дали:\n"
                    "• Интернет е свързан\n"
                    "• Firewall/антивирус не блокира заявките\n"
                    "• Опитай да отвориш https://console.groq.com в браузъра"
                )
            except requests.exceptions.Timeout:
                answer = "⚠️ Заявката отне твърде дълго. Опитай пак."
            except Exception as e:
                answer = (
                    f"⚠️ Неочаквана грешка: {e}\n\n"
                    "💡 Съвет: Намали транспортния CO₂ като използваш колело или ходиш пеша!"
                )

            def update_ui():
                thinking.destroy()
                self._ai_add_bubble("🤖 AI Съветник", answer, PURPLE, is_ai=True)
                self._ai_chat_frame.update_idletasks()

            self.root.after(0, update_ui)

        threading.Thread(target=call_api, daemon=True).start()

    # ══════════════════════════════════════════════
    #  TAB: ЛИДЕРБОРД  🏅
    # ══════════════════════════════════════════════
    def _create_leaderboard_tab(self):
        tab = tk.Frame(self._content, bg=BG)
        self._pages["leaderboard"] = tab
        _, inner = self._scrollable(tab)

        hc = card(inner, accent_color=WARN)
        hc.pack(fill='x', padx=18, pady=(16, 4))
        hb = tk.Frame(hc, bg=SURFACE)
        hb.pack(fill='x', padx=20, pady=14)
        lbl(hb, "🏅  Глобален Лидерборд", font=FONT_HEAD, fg=WHITE, bg=SURFACE).pack(anchor='w')
        lbl(hb, "Кой е най-зеленият потребител? Сравни се с всички!",
            font=FONT_SUB, fg=TEXTDIM, bg=SURFACE).pack(anchor='w', pady=(2, 0))

        # Controls
        ctrl = tk.Frame(inner, bg=BG)
        ctrl.pack(fill='x', padx=18, pady=8)
        lbl(ctrl, "Класация по:", font=("Helvetica", 10, "bold"),
            fg=TEXTDIM, bg=BG).pack(side='left', padx=(0, 8))
        self._lb_mode = tk.StringVar(value="avg")
        modes = [("Средно CO₂/запис", "avg"), ("Общо CO₂", "total"), ("Брой записи", "count")]
        for txt, val in modes:
            rb = tk.Radiobutton(ctrl, text=txt, variable=self._lb_mode, value=val,
                                bg=BG, fg=TEXT, selectcolor=SURFACE2,
                                activebackground=BG, activeforeground=ACCENT,
                                font=("Helvetica", 9), cursor="hand2",
                                command=self._refresh_leaderboard)
            rb.pack(side='left', padx=6)

        refresh_btn = tk.Button(ctrl, text="🔄 Обнови",
                                command=self._refresh_leaderboard)
        sty_btn(refresh_btn)
        refresh_btn.pack(side='right')

        self._lb_frame = tk.Frame(inner, bg=BG)
        self._lb_frame.pack(fill='x', padx=18, pady=4)

        # My position card
        my_c = card(inner, accent_color=ACCENT2)
        my_c.pack(fill='x', padx=18, pady=8)
        self._lb_my_frame = tk.Frame(my_c, bg=SURFACE)
        self._lb_my_frame.pack(fill='x', padx=16, pady=12)

        self._refresh_leaderboard()

    def _refresh_leaderboard(self):
        from database import load_leaderboard_data
        for w in self._lb_frame.winfo_children():
            w.destroy()
        for w in self._lb_my_frame.winfo_children():
            w.destroy()

        loading = lbl(self._lb_frame, "⏳  Зареждане на класацията...",
                      font=FONT_BODY, fg=TEXTDIM, bg=BG)
        loading.pack(pady=20)
        self.root.update()

        mode = self._lb_mode.get()
        data = load_leaderboard_data()
        loading.destroy()

        if not data:
            lbl(self._lb_frame, "🌱  Все още няма данни в класацията.",
                font=FONT_BODY, fg=TEXTDIM, bg=BG).pack(pady=20)
            return

        # Sort by mode
        if mode == "avg":
            key_fn = lambda x: x['avg_co2']
            label_fn = lambda x: f"{x['avg_co2']:.1f} kg/запис"
            title = "Средно CO₂ на запис (по-малко = по-добре)"
        elif mode == "total":
            key_fn = lambda x: x['total_co2']
            label_fn = lambda x: f"{x['total_co2']:.0f} kg общо"
            title = "Общо CO₂ (по-малко = по-добре)"
        else:
            key_fn = lambda x: -x['count']
            label_fn = lambda x: f"{x['count']} записа"
            title = "Брой записи (повече = по-активен)"

        sorted_data = sorted(data, key=key_fn)
        if mode == "count":
            sorted_data = sorted(data, key=key_fn)  # already negated

        lbl(self._lb_frame, f"📊  {title}",
            font=("Helvetica", 10, "bold"), fg=TEXTDIM, bg=BG).pack(anchor='w', pady=(0, 8))

        medals = ["🥇", "🥈", "🥉"]
        my_rank = None

        for i, user in enumerate(sorted_data[:20]):
            is_me = user['user_name'] == self.user_name
            if is_me:
                my_rank = i + 1

            row = tk.Frame(self._lb_frame,
                           bg=SURFACE3 if is_me else SURFACE2, bd=0)
            row.pack(fill='x', pady=2)

            # Rank medal or number
            medal = medals[i] if i < 3 else f"#{i+1}"
            rank_lbl = lbl(row, f"  {medal}  ", font=("Helvetica", 12, "bold"),
                           fg=WARN if i < 3 else TEXTDIM,
                           bg=row.cget('bg'))
            rank_lbl.pack(side='left', padx=4, pady=10)

            # Name
            name_clr = GREEN if is_me else TEXT
            name_font = ("Helvetica", 11, "bold") if is_me else ("Helvetica", 10)
            name_lbl = lbl(row, user['user_name'] + (" ← Ти" if is_me else ""),
                           font=name_font, fg=name_clr, bg=row.cget('bg'))
            name_lbl.pack(side='left', fill='x', expand=True, padx=8)

            # Bar
            bar_f = tk.Frame(row, bg=row.cget('bg'))
            bar_f.pack(side='left', fill='x', expand=True, padx=8)

            # Value label
            val_lbl = lbl(row, label_fn(user),
                          font=("Helvetica", 10, "bold"),
                          fg=ACCENT if is_me else TEXTDIM,
                          bg=row.cget('bg'))
            val_lbl.pack(side='right', padx=12)

        # My position summary
        if my_rank:
            lbl(self._lb_my_frame,
                f"🏆  Твоята позиция: #{my_rank} от {len(sorted_data)} потребители",
                font=("Helvetica", 12, "bold"), fg=ACCENT, bg=SURFACE).pack(anchor='w')
            pct = (len(sorted_data) - my_rank) / max(len(sorted_data) - 1, 1) * 100
            lbl(self._lb_my_frame,
                f"По-добър от {pct:.0f}% от потребителите! {'🌟' if pct > 50 else '💪'}",
                font=FONT_BODY, fg=GREEN if pct > 50 else WARN, bg=SURFACE).pack(anchor='w', pady=(4, 0))
        else:
            lbl(self._lb_my_frame,
                "Добави записи, за да се появиш в класацията!",
                font=FONT_BODY, fg=TEXTDIM, bg=SURFACE).pack(anchor='w')

    # ══════════════════════════════════════════════
    #  TAB: ДНЕВНИК НА НАВИЦИТЕ  📅
    # ══════════════════════════════════════════════
    def _create_habits_tab(self):
        tab = tk.Frame(self._content, bg=BG)
        self._pages["habits"] = tab
        _, inner = self._scrollable(tab)

        hc = card(inner, accent_color=TEAL)
        hc.pack(fill='x', padx=18, pady=(16, 4))
        hb = tk.Frame(hc, bg=SURFACE)
        hb.pack(fill='x', padx=20, pady=14)
        lbl(hb, "📅  Дневник на Еко Навиците", font=FONT_HEAD, fg=WHITE, bg=SURFACE).pack(anchor='w')
        lbl(hb, "Следи ежедневните си навици и изгради зелен начин на живот",
            font=FONT_SUB, fg=TEXTDIM, bg=SURFACE).pack(anchor='w', pady=(2, 0))

        # Today's habits
        today_c = card(inner, accent_color=GREEN)
        today_c.pack(fill='x', padx=18, pady=8)
        tc = tk.Frame(today_c, bg=SURFACE)
        tc.pack(fill='x', padx=16, pady=14)
        lbl(tc, f"✅  Навици за днес — {datetime.now().strftime('%d.%m.%Y')}",
            font=("Helvetica", 12, "bold"), fg=WHITE, bg=SURFACE).pack(anchor='w', pady=(0, 10))

        HABITS = [
            ("🚶", "Ходих пеша или с колело",       "transport"),
            ("🥗", "Изядох безмесно ястие",          "food"),
            ("♻️", "Рециклирах отпадъци",            "recycle"),
            ("💡", "Изключих ненужните светлини",    "energy"),
            ("🚿", "Взех кратък душ (< 5 мин)",      "water"),
            ("🛍️", "Избегнах еднократна пластмаса",  "plastic"),
            ("🌱", "Купих местни продукти",          "local"),
            ("🔌", "Изключих уреди от контакта",     "standby"),
        ]

        self._habit_vars = {}
        habits_grid = tk.Frame(tc, bg=SURFACE)
        habits_grid.pack(fill='x')

        for i, (icon, text, key) in enumerate(HABITS):
            col = i % 2
            if col == 0:
                row_f = tk.Frame(habits_grid, bg=SURFACE)
                row_f.pack(fill='x', pady=2)

            var = tk.BooleanVar(value=False)
            self._habit_vars[key] = var

            cb_f = tk.Frame(row_f, bg=SURFACE2)
            cb_f.pack(side='left', expand=True, fill='x', padx=4, pady=2)

            cb = tk.Checkbutton(cb_f, text=f"  {icon}  {text}",
                                variable=var, font=("Helvetica", 10),
                                bg=SURFACE2, fg=TEXT, selectcolor=SURFACE3,
                                activebackground=SURFACE2, activeforeground=ACCENT,
                                cursor="hand2",
                                command=lambda: self._update_habit_score())
            cb.pack(anchor='w', padx=8, pady=6)

        # Score display
        self._habit_score_lbl = lbl(tc, "Резултат: 0 / 8",
                                    font=("Helvetica", 13, "bold"), fg=ACCENT, bg=SURFACE)
        self._habit_score_lbl.pack(anchor='w', pady=(14, 4))

        self._habit_bar_frame = tk.Frame(tc, bg=SURFACE3, height=16)
        self._habit_bar_frame.pack(fill='x', pady=(0, 8))
        self._habit_bar_fill = tk.Frame(self._habit_bar_frame, bg=GREEN, height=16)
        self._habit_bar_fill.place(relx=0, rely=0, relwidth=0, relheight=1)

        self._habit_msg = lbl(tc, "Избери навиците, изпълнени днес!",
                              font=FONT_BODY, fg=TEXTDIM, bg=SURFACE)
        self._habit_msg.pack(anchor='w')

        # Weekly streak card
        streak_c = card(inner, accent_color=TEAL)
        streak_c.pack(fill='x', padx=18, pady=8)
        sc = tk.Frame(streak_c, bg=SURFACE)
        sc.pack(fill='x', padx=16, pady=14)
        lbl(sc, "🔥  Статистика за тази седмица",
            font=("Helvetica", 12, "bold"), fg=WHITE, bg=SURFACE).pack(anchor='w', pady=(0, 10))

        week_row = tk.Frame(sc, bg=SURFACE)
        week_row.pack(fill='x')
        days_bg = [SURFACE2] * 7
        today_idx = datetime.now().weekday()
        days_bg[today_idx] = SURFACE3

        days_names = ["Пон", "Вт", "Ср", "Чет", "Пет", "Съб", "Нед"]
        entries_by_day = {}
        for e in self.history_data:
            if (datetime.now() - e['date']).days < 7:
                wd = e['date'].weekday()
                entries_by_day[wd] = entries_by_day.get(wd, 0) + 1

        for d_idx, (d_name, d_bg) in enumerate(zip(days_names, days_bg)):
            d_f = tk.Frame(week_row, bg=d_bg)
            d_f.pack(side='left', expand=True, fill='x', padx=3, pady=2)
            has_entry = d_idx in entries_by_day
            clr = GREEN if has_entry else (WARN if d_idx == today_idx else DIM)
            dot = "✅" if has_entry else ("📍" if d_idx == today_idx else "○")
            lbl(d_f, dot, font=("Helvetica", 14), fg=clr, bg=d_bg).pack(pady=(8, 2))
            lbl(d_f, d_name, font=("Helvetica", 8), fg=TEXTDIM, bg=d_bg).pack(pady=(0, 8))

        # CO₂ saved estimate
        saved_c = card(inner, accent_color=GREEN)
        saved_c.pack(fill='x', padx=18, pady=8)
        sav_b = tk.Frame(saved_c, bg=SURFACE)
        sav_b.pack(fill='x', padx=16, pady=14)
        lbl(sav_b, "🌍  Прогнозно спестяване от навиците",
            font=("Helvetica", 12, "bold"), fg=WHITE, bg=SURFACE).pack(anchor='w', pady=(0, 10))

        habit_savings = [
            ("🚶 Ходене/колело вместо кола", "~2.4 kg CO₂ спестени / ден"),
            ("🥗 Безмесен ден",               "~1.5 kg CO₂ спестени"),
            ("♻️ Рециклиране",                "~0.5 kg CO₂ спестени"),
            ("💡 Пестене на ток",              "~0.3 kg CO₂ спестени"),
            ("🚿 Кратък душ",                  "~0.2 kg CO₂ спестени"),
        ]
        for habit, saving in habit_savings:
            r = tk.Frame(sav_b, bg=SURFACE2)
            r.pack(fill='x', pady=2)
            lbl(r, f"  {habit}", font=("Helvetica", 9), fg=TEXT, bg=SURFACE2).pack(side='left', padx=8, pady=6)
            lbl(r, saving, font=("Helvetica", 9, "bold"), fg=GREEN, bg=SURFACE2).pack(side='right', padx=8)

    def _update_habit_score(self):
        score = sum(1 for v in self._habit_vars.values() if v.get())
        total = len(self._habit_vars)
        pct = score / total

        clr = GREEN if pct >= 0.75 else WARN if pct >= 0.5 else ACCENT
        self._habit_score_lbl.config(text=f"Резултат: {score} / {total}", fg=clr)
        self._habit_bar_fill.place(relwidth=pct)

        msgs = {
            0: ("Избери поне един навик!", TEXTDIM),
            1: ("Добро начало! 🌱", TEXTDIM),
            2: ("Продължавай! 💪", ACCENT),
            3: ("Добре! Повече е по-добре 🌿", ACCENT),
            4: ("Отлично! Половината навици! ✨", TEAL),
            5: ("Страхотно! Почти там! 🌟", GREEN),
            6: ("Отличен ден! 🏆", GREEN),
            7: ("Невероятно! Почти перфектен! 🔥", GREEN),
            8: ("ПЕРФЕКТЕН ЕКО ДЕН! 🌍💚", GREEN),
        }
        msg, msg_clr = msgs.get(score, ("", TEXTDIM))
        self._habit_msg.config(text=msg, fg=msg_clr)

    # ══════════════════════════════════════════════
    #  TAB: ДЕТАЙЛНА СТАТИСТИКА  📊
    # ══════════════════════════════════════════════
    def _create_statistics_tab(self):
        tab = tk.Frame(self._content, bg=BG)
        self._pages["statistics"] = tab
        _, inner = self._scrollable(tab)

        hc = card(inner, accent_color=ACCENT2)
        hc.pack(fill='x', padx=18, pady=(16, 4))
        hb = tk.Frame(hc, bg=SURFACE)
        hb.pack(fill='x', padx=20, pady=14)
        lbl(hb, "📊  Детайлна Статистика", font=FONT_HEAD, fg=WHITE, bg=SURFACE).pack(anchor='w')
        lbl(hb, "Задълбочен анализ на твоя въглероден отпечатък",
            font=FONT_SUB, fg=TEXTDIM, bg=SURFACE).pack(anchor='w', pady=(2, 0))

        if not self.history_data:
            self._empty_state(inner, "📊", "Все още няма данни",
                              "Добави записи за да видиш детайлна статистика.")
            return

        data = self.history_data
        total   = sum(e['total_co2'] for e in data)
        transp  = sum(e['travel_co2'] for e in data)
        elec    = sum(e['electricity_co2'] for e in data)
        n       = len(data)
        avg     = total / n
        mx      = max(e['total_co2'] for e in data)
        mn      = min(e['total_co2'] for e in data)

        # ── KPI карти ───────────────────────────────
        kpi_row = tk.Frame(inner, bg=BG)
        kpi_row.pack(fill='x', padx=18, pady=8)
        kpis = [
            ("🌍", "Общо CO₂",    f"{total:.1f} kg",  ACCENT2),
            ("📈", "Средно",      f"{avg:.1f} kg",    TEAL),
            ("⬆️", "Максимум",    f"{mx:.1f} kg",     ERROR),
            ("⬇️", "Минимум",     f"{mn:.1f} kg",     GREEN),
            ("🚗", "Транспорт",   f"{transp:.0f} kg", WARN),
            ("💡", "Ток",         f"{elec:.0f} kg",   PURPLE),
        ]
        for icon, lab, val, clr in kpis:
            kf = tk.Frame(kpi_row, bg=SURFACE)
            kf.pack(side='left', expand=True, fill='x', padx=4, pady=2)
            tk.Frame(kf, bg=clr, height=3).pack(fill='x')
            lbl(kf, icon, font=("Helvetica", 20), bg=SURFACE).pack(pady=(10, 2))
            lbl(kf, val, font=("Helvetica", 13, "bold"), fg=clr, bg=SURFACE).pack()
            lbl(kf, lab, font=("Helvetica", 8), fg=TEXTDIM, bg=SURFACE).pack(pady=(2, 10))

        # ── Настройки на matplotlib ──────────────────
        plt.rcParams.update({
            'axes.facecolor':   SURFACE,
            'figure.facecolor': BG,
            'text.color':       TEXT,
            'axes.labelcolor':  TEXTDIM,
            'xtick.color':      TEXTDIM,
            'ytick.color':      TEXTDIM,
            'grid.color':       SURFACE2,
            'axes.spines.top':  False,
            'axes.spines.right':False,
        })

        # ── Графика 1: Тренд по месеци ───────────────
        from collections import defaultdict
        monthly_total = defaultdict(float)
        monthly_t     = defaultdict(float)
        monthly_e     = defaultdict(float)
        for e in data:
            k = e['date'].strftime('%m/%Y')
            monthly_total[k] += e['total_co2']
            monthly_t[k]     += e['travel_co2']
            monthly_e[k]     += e['electricity_co2']
        months_sorted = sorted(monthly_total.keys(),
                               key=lambda x: datetime.strptime(x, '%m/%Y'))

        fig1, ax1 = plt.subplots(figsize=(11, 3.2), dpi=96)
        fig1.patch.set_facecolor(BG)
        mt_vals = [monthly_t[m] for m in months_sorted]
        me_vals = [monthly_e[m] for m in months_sorted]
        x = range(len(months_sorted))
        ax1.bar(x, mt_vals, label="Транспорт", color=ACCENT2, alpha=0.9)
        ax1.bar(x, me_vals, bottom=mt_vals, label="Електричество", color=WARN, alpha=0.9)
        ax1.set_xticks(list(x))
        ax1.set_xticklabels(months_sorted, rotation=35, ha='right', fontsize=8)
        ax1.set_ylabel("kg CO₂")
        ax1.set_title("CO₂ по месеци — Транспорт vs Електричество", color=TEXT, pad=10)
        ax1.legend(facecolor=SURFACE2, edgecolor=DIM, labelcolor=TEXT)
        ax1.grid(True, linestyle='--', alpha=0.3, axis='y')
        fig1.tight_layout()
        cv1 = FigureCanvasTkAgg(fig1, master=inner)
        cv1.draw()
        cv1.get_tk_widget().pack(fill='x', padx=18, pady=4)

        # ── Графика 2: Разпределение по транспорт + тренд ──
        fig2, (ax2a, ax2b) = plt.subplots(1, 2, figsize=(11, 3.2), dpi=96)
        fig2.patch.set_facecolor(BG)

        # Pie по транспорт
        mode_co2 = defaultdict(float)
        mode_icons = {"car":"🚗 Кола", "bus":"🚌 Автобус", "train":"🚆 Влак",
                      "bicycle":"🚲 Колело", "walking":"🚶 Пеша", "":"🌍 Друго"}
        for e in data:
            label = mode_icons.get(e['transport_mode'], e['transport_mode'] or "Друго")
            mode_co2[label] += e['travel_co2']
        if mode_co2:
            pie_labels = list(mode_co2.keys())
            pie_vals   = list(mode_co2.values())
            pie_colors = [ACCENT2, TEAL, WARN, GREEN, PURPLE, PINK][:len(pie_labels)]
            ax2a.pie(pie_vals, labels=pie_labels, colors=pie_colors,
                     autopct='%1.0f%%', textprops={'color': TEXT, 'fontsize': 8},
                     startangle=140)
            ax2a.set_title("CO₂ по вид транспорт", color=TEXT, pad=10)

        # Line trend (7-day rolling average)
        sorted_entries = sorted(data, key=lambda x: x['date'])
        dates_dt = [e['date'] for e in sorted_entries]
        co2_vals = [e['total_co2'] for e in sorted_entries]
        ax2b.plot(dates_dt, co2_vals, color=DIM, linewidth=1, alpha=0.5)
        # Rolling avg
        window = min(7, len(co2_vals))
        rolling = [sum(co2_vals[max(0,i-window):i+1])/min(window,i+1)
                   for i in range(len(co2_vals))]
        ax2b.plot(dates_dt, rolling, color=ACCENT, linewidth=2.5, label="7-дн. средна")
        ax2b.fill_between(dates_dt, rolling, alpha=0.12, color=ACCENT)
        ax2b.set_ylabel("kg CO₂")
        ax2b.set_title("Тренд (7-дневна средна)", color=TEXT, pad=10)
        ax2b.legend(facecolor=SURFACE2, edgecolor=DIM, labelcolor=TEXT)
        ax2b.grid(True, linestyle='--', alpha=0.25)
        fig2.tight_layout()
        cv2 = FigureCanvasTkAgg(fig2, master=inner)
        cv2.draw()
        cv2.get_tk_widget().pack(fill='x', padx=18, pady=4)

        # ── Графика 3: Час на деня (кога записваш) + ден на седмицата ──
        fig3, (ax3a, ax3b) = plt.subplots(1, 2, figsize=(11, 2.8), dpi=96)
        fig3.patch.set_facecolor(BG)

        # CO₂ по ден от седмицата
        dow_co2 = defaultdict(float)
        dow_count = defaultdict(int)
        for e in data:
            dow = e['date'].weekday()
            dow_co2[dow]   += e['total_co2']
            dow_count[dow] += 1
        dow_labels = ["Пон", "Вт", "Ср", "Чет", "Пет", "Съб", "Нед"]
        dow_vals   = [dow_co2[i] / max(dow_count[i], 1) for i in range(7)]
        dow_clrs   = [GREEN if v == min(dow_vals) else (ERROR if v == max(dow_vals) else ACCENT2)
                      for v in dow_vals]
        ax3a.bar(dow_labels, dow_vals, color=dow_clrs, alpha=0.9)
        ax3a.set_ylabel("Средно kg CO₂")
        ax3a.set_title("Средно CO₂ по ден от седмицата", color=TEXT, pad=10)
        ax3a.grid(True, linestyle='--', alpha=0.25, axis='y')

        # Хистограма на разпределението
        ax3b.hist(co2_vals, bins=min(15, len(co2_vals)),
                  color=TEAL, alpha=0.85, edgecolor=BG)
        ax3b.axvline(avg, color=ACCENT, linewidth=2, linestyle='--', label=f"Средно: {avg:.1f}")
        ax3b.set_xlabel("kg CO₂")
        ax3b.set_ylabel("Брой записи")
        ax3b.set_title("Разпределение на записите", color=TEXT, pad=10)
        ax3b.legend(facecolor=SURFACE2, edgecolor=DIM, labelcolor=TEXT)
        fig3.tight_layout()
        cv3 = FigureCanvasTkAgg(fig3, master=inner)
        cv3.draw()
        cv3.get_tk_widget().pack(fill='x', padx=18, pady=4)

        # ── Insight карти ────────────────────────────
        insight_c = card(inner, accent_color=PURPLE)
        insight_c.pack(fill='x', padx=18, pady=8)
        ins_b = tk.Frame(insight_c, bg=SURFACE)
        ins_b.pack(fill='x', padx=16, pady=14)
        lbl(ins_b, "🧠  Умни Наблюдения",
            font=("Helvetica", 12, "bold"), fg=WHITE, bg=SURFACE).pack(anchor='w', pady=(0, 8))

        best_dow  = dow_labels[dow_vals.index(min(dow_vals))]
        worst_dow = dow_labels[dow_vals.index(max(dow_vals))]
        top_mode  = max(mode_co2, key=mode_co2.get) if mode_co2 else "—"
        trend_dir = "📈 нагоре" if len(rolling) > 1 and rolling[-1] > rolling[0] else "📉 надолу"

        insights = [
            (GREEN,   f"🌟  Най-зеленият ти ден е {best_dow} — средно само {min(dow_vals):.1f} kg CO₂"),
            (ERROR,   f"⚠️   Най-интензивният ти ден е {worst_dow} — средно {max(dow_vals):.1f} kg CO₂"),
            (TEAL,    f"🚗  Повечето CO₂ от транспорт идват от: {top_mode}"),
            (WARN,    f"📊  Тренд на последните записи: {trend_dir}"),
            (PURPLE,  f"⚡  Електричеството е {elec/max(total,1)*100:.0f}% от общия ти CO₂"),
        ]
        for clr, text in insights:
            ins_row = tk.Frame(ins_b, bg=SURFACE2)
            ins_row.pack(fill='x', pady=2)
            tk.Frame(ins_row, bg=clr, width=4).pack(side='left', fill='y')
            lbl(ins_row, text, font=("Helvetica", 10),
                fg=TEXT, bg=SURFACE2, wraplength=800, justify='left').pack(
                anchor='w', padx=12, pady=8)

    # ──────────────────────────────────────────────
    #  TAB: TIPS
    # ──────────────────────────────────────────────
    def _create_tips_tab(self):
        tab = tk.Frame(self._content, bg=BG)
        self._pages["tips"] = tab
        _, inner = self._scrollable(tab)

        hc = card(inner, accent_color=WARN)
        hc.pack(fill='x', padx=18, pady=(16, 4))
        hb = tk.Frame(hc, bg=SURFACE)
        hb.pack(fill='x', padx=20, pady=14)
        lbl(hb, "Съвети за Намаляване на Отпечатъка",
            font=FONT_HEAD, fg=WHITE, bg=SURFACE).pack(anchor='w')
        lbl(hb, "Персонализирани препоръки на базата на твоите данни",
            font=FONT_SUB, fg=TEXTDIM, bg=SURFACE).pack(anchor='w', pady=(2, 0))

        # Personal tips
        pc = card(inner, accent_color=ACCENT2)
        pc.pack(fill='x', padx=18, pady=8)
        pb = tk.Frame(pc, bg=SURFACE)
        pb.pack(fill='x', padx=16, pady=14)
        lbl(pb, "🌟  Персонализирани съвети за теб", font=("Helvetica", 12, "bold"),
            fg=WHITE, bg=SURFACE).pack(anchor='w', pady=(0, 8))
        self.personal_tips_text = tk.Text(pb, wrap=tk.WORD, height=5, width=80,
                                          font=FONT_BODY, padx=14, pady=10,
                                          bg=SURFACE2, fg=TEXT, bd=0,
                                          insertbackground=ACCENT)
        self.personal_tips_text.pack(fill='x')
        self.personal_tips_text.insert(tk.END,
            "💡 Извърши изчисление в Калкулатора, за да получиш персонализирани съвети!")
        self.personal_tips_text.config(state='disabled')

        tip_data = [
            ("🚗", "Транспорт", ACCENT2, [
                "Използвай обществен транспорт вместо кола",
                "Ходи пеша или карай колело за кратки разстояния",
                "Споделяй кола с колеги и приятели",
                "Ограничи полетите — 1 полет добавя стотици kg CO₂",
                "Обмисли електрически или хибриден автомобил",
            ]),
            ("💡", "Енергия", WARN, [
                "Смени крушките с LED — 75% по-малко ток",
                "Използвай естествена светлина",
                "Изключвай уредите от контакта при неизползване",
                "Обмисли соларни панели",
                "Намали отоплението/охлаждането с 1–2°C",
            ]),
            ("♻️", "Начин на живот", GREEN, [
                "Купувай по-малко, избирай устойчиви продукти",
                "Рециклирай и компостирай",
                "Вземай по-кратки душове",
                "Пери на студена вода и сушено на въздух",
                "Засаждай дървета",
            ]),
        ]

        for icon, title, clr, tips in tip_data:
            tc = card(inner, accent_color=clr)
            tc.pack(fill='x', padx=18, pady=8)
            tb = tk.Frame(tc, bg=SURFACE)
            tb.pack(fill='x', padx=16, pady=14)
            lbl(tb, f"{icon}  {title}", font=("Helvetica", 12, "bold"),
                fg=clr, bg=SURFACE).pack(anchor='w', pady=(0, 10))
            for tip in tips:
                r = tk.Frame(tb, bg=SURFACE2)
                r.pack(fill='x', pady=2)
                tk.Frame(r, bg=clr, width=3).pack(side='left', fill='y')
                lbl(r, f"  {tip}", font=FONT_BODY, fg=TEXT, bg=SURFACE2).pack(
                    side='left', padx=8, pady=8)

    # ──────────────────────────────────────────────
    #  TAB: COMMUNITY
    # ──────────────────────────────────────────────
    def _create_community_tab(self):
        tab = tk.Frame(self._content, bg=BG)
        self._pages["community"] = tab
        _, inner = self._scrollable(tab)

        hc = card(inner, accent_color=TEAL)
        hc.pack(fill='x', padx=18, pady=(16, 4))
        hb = tk.Frame(hc, bg=SURFACE)
        hb.pack(fill='x', padx=20, pady=14)
        lbl(hb, "Въздействие на Общността",
            font=FONT_HEAD, fg=WHITE, bg=SURFACE).pack(anchor='w')
        lbl(hb, "Виж как се сравняваш с другите и сподели съвети",
            font=FONT_SUB, fg=TEXTDIM, bg=SURFACE).pack(anchor='w', pady=(2, 0))

        # Comparison chart
        compare = card(inner, accent_color=TEAL)
        compare.pack(fill='x', padx=18, pady=8)
        lbl(compare, "📊  Как се сравняваш", font=("Helvetica", 12, "bold"),
            fg=WHITE, bg=SURFACE).pack(anchor='w', padx=16, pady=(14, 8))

        if not self.history_data:
            self._empty_state(compare,
                "👥", "Все още няма данни за сравнение",
                "Добави записи чрез Калкулатора,\nза да видиш как се сравняваш с другите.", compact=True)
        else:
            total = sum(e['total_co2'] for e in self.history_data) / max(len(self.history_data), 1)

            plt.rcParams['axes.facecolor'] = SURFACE
            plt.rcParams['figure.facecolor'] = SURFACE
            plt.rcParams['text.color'] = TEXT
            plt.rcParams['axes.labelcolor'] = TEXTDIM
            plt.rcParams['xtick.color'] = TEXTDIM
            plt.rcParams['ytick.color'] = TEXTDIM
            plt.rcParams['grid.color'] = SURFACE2

            fig, ax = plt.subplots(figsize=(8, 3), dpi=92)
            fig.patch.set_facecolor(SURFACE)
            cats   = ['Ти', 'Средно', 'ЕкоСледа-лидер']
            vals   = [total, 40, 20]
            clrs   = [ACCENT2, "#4b5563", TEAL]
            bars = ax.bar(cats, vals, color=clrs, width=0.45)
            for bar in bars:
                h = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2, h + 0.5,
                        f'{h:.1f} kg', ha='center', color=TEXT, fontsize=9)
            ax.set_ylabel("Средно kg CO₂ / запис")
            ax.grid(True, linestyle='--', alpha=0.35, axis='y')
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            fig.tight_layout()

            cv = FigureCanvasTkAgg(fig, master=compare)
            cv.draw()
            cv.get_tk_widget().pack(fill='x', padx=14, pady=(0, 14))

        # ── Публикувай съвет ─────────────────────────────
        share = card(inner, accent_color=ACCENT3)
        share.pack(fill='x', padx=18, pady=8)
        sh_b = tk.Frame(share, bg=SURFACE)
        sh_b.pack(fill='x', padx=16, pady=14)

        lbl(sh_b, "💬  Сподели твоя еко-съвет",
            font=("Helvetica", 12, "bold"), fg=WHITE, bg=SURFACE).pack(anchor='w', pady=(0, 8))
        lbl(sh_b, "Твоят съвет ще се вижда от всички потребители в реално време!",
            font=("Helvetica", 9), fg=TEXTDIM, bg=SURFACE).pack(anchor='w', pady=(0, 8))

        self._tip_entry = tk.Text(sh_b, wrap=tk.WORD, height=4, width=80,
                                   font=FONT_BODY, padx=12, pady=8,
                                   bg=SURFACE2, fg=TEXT, bd=0,
                                   insertbackground=ACCENT,
                                   highlightthickness=1,
                                   highlightbackground=DIM,
                                   highlightcolor=ACCENT2)
        self._tip_entry.pack(fill='x')
        placeholder = "Напиши своя еко-съвет тук..."
        self._tip_entry.insert(tk.END, placeholder)
        self._tip_entry.config(fg=TEXTDIM)

        def on_focus_in(e):
            if self._tip_entry.get("1.0", tk.END).strip() == placeholder:
                self._tip_entry.delete("1.0", tk.END)
                self._tip_entry.config(fg=TEXT)
        def on_focus_out(e):
            if not self._tip_entry.get("1.0", tk.END).strip():
                self._tip_entry.insert(tk.END, placeholder)
                self._tip_entry.config(fg=TEXTDIM)
        self._tip_entry.bind("<FocusIn>",  on_focus_in)
        self._tip_entry.bind("<FocusOut>", on_focus_out)

        self._tip_status = lbl(sh_b, "", font=("Helvetica", 9), fg=TEAL, bg=SURFACE)
        self._tip_status.pack(anchor='w', pady=(6, 0))

        btn_row = tk.Frame(sh_b, bg=SURFACE)
        btn_row.pack(fill='x', pady=(8, 0))
        char_lbl = lbl(btn_row, "0 / 280 символа", font=("Helvetica", 8),
                        fg=TEXTDIM, bg=SURFACE)
        char_lbl.pack(side='left')

        def on_key(_=None):
            txt = self._tip_entry.get("1.0", tk.END).strip()
            if txt == placeholder:
                char_lbl.config(text="0 / 280 символа", fg=TEXTDIM)
            else:
                n = len(txt)
                clr = GREEN if n <= 200 else WARN if n <= 280 else ERROR
                char_lbl.config(text=f"{n} / 280 символа", fg=clr)
        self._tip_entry.bind("<KeyRelease>", on_key)

        share_btn = tk.Button(btn_row, text="  🌿  Публикувай съвета  →",
                              command=lambda: self._post_tip())
        sty_btn(share_btn, accent=True)
        share_btn.pack(side='right')

        # ── Съвети от общността ──────────────────────────
        tips_c = card(inner, accent_color=SURFACE3)
        tips_c.pack(fill='x', padx=18, pady=8)
        tc_hdr = tk.Frame(tips_c, bg=SURFACE)
        tc_hdr.pack(fill='x', padx=16, pady=(14, 8))
        lbl(tc_hdr, "🌍  Съвети от общността",
            font=("Helvetica", 12, "bold"), fg=WHITE, bg=SURFACE).pack(side='left')
        refresh_btn = tk.Button(tc_hdr, text="🔄 Обнови",
                                command=self._refresh_community_tips)
        sty_btn(refresh_btn)
        refresh_btn.pack(side='right')

        self._tips_list_frame = tk.Frame(tips_c, bg=SURFACE)
        self._tips_list_frame.pack(fill='x', padx=16, pady=(0, 14))

        # Зареди при старт
        self._refresh_community_tips()

    def _post_tip(self):
        from database import post_community_tip
        placeholder = "Напиши своя еко-съвет тук..."
        txt = self._tip_entry.get("1.0", tk.END).strip()
        if not txt or txt == placeholder:
            self._tip_status.config(text="❌  Моля, напиши съвет преди да публикуваш.", fg=ERROR)
            return
        if len(txt) > 280:
            self._tip_status.config(text="❌  Съветът е твърде дълъг (макс. 280 символа).", fg=ERROR)
            return

        self._tip_status.config(text="⏳  Публикуване...", fg=TEAL)
        self.root.update()

        ok, err = post_community_tip(self.user_name, txt)
        if ok:
            self._tip_entry.delete("1.0", tk.END)
            self._tip_entry.insert(tk.END, placeholder)
            self._tip_entry.config(fg=TEXTDIM)
            self._tip_status.config(text="✅  Публикувано успешно! 🌿", fg=GREEN)
            self._refresh_community_tips()
        else:
            self._tip_status.config(text=f"❌  Грешка: {err}", fg=ERROR)

    def _refresh_community_tips(self):
        from database import load_community_tips, delete_community_tip

        for w in self._tips_list_frame.winfo_children():
            w.destroy()

        lbl(self._tips_list_frame, "⏳  Зареждане...",
            font=("Helvetica", 10), fg=TEXTDIM, bg=SURFACE).pack(pady=10)
        self.root.update()

        tips = load_community_tips(limit=30)

        for w in self._tips_list_frame.winfo_children():
            w.destroy()

        if not tips:
            lbl(self._tips_list_frame,
                "🌱  Все още няма съвети — бъди първият!",
                font=("Helvetica", 10), fg=TEXTDIM, bg=SURFACE).pack(pady=16)
            return

        for tip in tips:
            row = tk.Frame(self._tips_list_frame, bg=SURFACE2)
            row.pack(fill='x', pady=3)

            # Лява цветна лента — зелена за моите, сива за другите
            is_mine = tip.get('user_name', '') == self.user_name
            side_clr = ACCENT2 if is_mine else SURFACE3
            tk.Frame(row, bg=side_clr, width=4).pack(side='left', fill='y')

            body = tk.Frame(row, bg=SURFACE2)
            body.pack(side='left', fill='both', expand=True, padx=10, pady=8)

            # Горен ред: потребител + дата + (изтрий ако е мой)
            top = tk.Frame(body, bg=SURFACE2)
            top.pack(fill='x')

            name_lbl = lbl(top, f"🌿  {tip['user_name']}",
                           font=("Helvetica", 9, "bold"),
                           fg=ACCENT if is_mine else TEAL, bg=SURFACE2)
            name_lbl.pack(side='left')

            if is_mine:
                mine_badge = lbl(top, "  (твой)",
                                 font=("Helvetica", 8), fg=TEXTDIM, bg=SURFACE2)
                mine_badge.pack(side='left')

            date_str = tip.get('created_at', '')[:10]
            lbl(top, date_str, font=("Helvetica", 8),
                fg=TEXTDIM, bg=SURFACE2).pack(side='right')

            # Текст на съвета
            lbl(body, tip['tip'], font=("Helvetica", 10),
                fg=TEXT, bg=SURFACE2, wraplength=700, justify='left').pack(
                anchor='w', pady=(4, 0))

            # Бутон за изтриване (само за моите)
            if is_mine:
                tip_id = tip.get('id', '')
                def make_delete(tid, uname):
                    def do_delete():
                        if messagebox.askyesno("Изтриване",
                                               "Сигурен ли си, че искаш да изтриеш този съвет?"):
                            delete_community_tip(tid, uname)
                            self._refresh_community_tips()
                    return do_delete
                del_btn = tk.Button(body, text="🗑️  Изтрий",
                                    command=make_delete(tip_id, self.user_name))
                sty_btn(del_btn, danger=True)
                del_btn.pack(anchor='e', pady=(6, 0))

    # ──────────────────────────────────────────────
    #  TAB: PROFILE
    # ──────────────────────────────────────────────
    def _create_profile_tab(self):
        tab = tk.Frame(self._content, bg=BG)
        self._pages["profile"] = tab
        _, inner = self._scrollable(tab)

        hc = card(inner, accent_color=PURPLE)
        hc.pack(fill='x', padx=18, pady=(16, 4))
        hb = tk.Frame(hc, bg=SURFACE)
        hb.pack(fill='x', padx=20, pady=14)
        lbl(hb, "Твоят Профил", font=FONT_HEAD, fg=WHITE, bg=SURFACE).pack(anchor='w')
        lbl(hb, "Управлявай акаунта и личните си данни",
            font=FONT_SUB, fg=TEXTDIM, bg=SURFACE).pack(anchor='w', pady=(2, 0))

        profile = get_profile(self.user_id)
        if not profile:
            return

        username, name, created_at = profile

        # Info card
        info = card(inner, accent_color=PURPLE)
        info.pack(fill='x', padx=18, pady=8)
        ib = tk.Frame(info, bg=SURFACE)
        ib.pack(fill='both', expand=True, padx=16, pady=16)

        lbl(ib, "👤  Информация за акаунта",
            font=("Helvetica", 12, "bold"), fg=WHITE, bg=SURFACE).pack(anchor='w', pady=(0, 10))

        for lab, val, clr in [("Потребителско Име:", username, ACCENT),
                               ("Пълно Име:",         name,     WHITE),
                               ("Член от:",           created_at, TEAL),
                               ("Записани дати:",     str(len(self.history_data)), GREEN)]:
            r = tk.Frame(ib, bg=SURFACE2)
            r.pack(fill='x', pady=2)
            lbl(r, f"  {lab}", font=("Helvetica", 9, "bold"), fg=TEXTDIM, bg=SURFACE2,
                width=22, anchor='w').pack(side='left', pady=8)
            lbl(r, val, font=("Helvetica", 10, "bold"), fg=clr, bg=SURFACE2).pack(side='left')

        # Edit name
        edit = card(inner, accent_color=TEAL)
        edit.pack(fill='x', padx=18, pady=8)
        eb = tk.Frame(edit, bg=SURFACE)
        eb.pack(fill='both', expand=True, padx=16, pady=16)
        lbl(eb, "✏️  Промени Името", font=("Helvetica", 12, "bold"), fg=WHITE, bg=SURFACE).pack(anchor='w', pady=(0, 8))
        self.new_name_var = tk.StringVar(value=name)
        entry_widget(eb, self.new_name_var, width=36).pack(anchor='w', pady=(0, 8), ipady=4)
        sn_btn = tk.Button(eb, text="💾  Запази Иметo", command=self._save_name)
        sty_btn(sn_btn, accent=True)
        sn_btn.pack(anchor='w')

        # Change password
        pw_c = card(inner, accent_color=ERROR)
        pw_c.pack(fill='x', padx=18, pady=8)
        pb = tk.Frame(pw_c, bg=SURFACE)
        pb.pack(fill='both', expand=True, padx=16, pady=16)
        lbl(pb, "🔒  Промени Паролата", font=("Helvetica", 12, "bold"), fg=WHITE, bg=SURFACE).pack(anchor='w', pady=(0, 8))
        self.new_pw_var  = tk.StringVar()
        self.new_pw2_var = tk.StringVar()
        lbl(pb, "Нова парола:", font=("Helvetica", 9), fg=TEXTDIM, bg=SURFACE).pack(anchor='w')
        entry_widget(pb, self.new_pw_var,  width=30, show="●").pack(anchor='w', pady=(2, 6), ipady=4)
        lbl(pb, "Потвърди:", font=("Helvetica", 9), fg=TEXTDIM, bg=SURFACE).pack(anchor='w')
        entry_widget(pb, self.new_pw2_var, width=30, show="●").pack(anchor='w', pady=(2, 8), ipady=4)
        self.pw_err = lbl(pb, "", font=("Helvetica", 9), fg=ERROR, bg=SURFACE)
        self.pw_err.pack(anchor='w')
        cp_btn = tk.Button(pb, text="🔑  Смени Паролата", command=self._save_password)
        sty_btn(cp_btn, danger=True)
        cp_btn.pack(anchor='w', pady=6)

        # ── PDF Отчет ──────────────────────────────
        pdf_c = card(inner, accent_color=GREEN)
        pdf_c.pack(fill='x', padx=18, pady=8)
        pdf_b = tk.Frame(pdf_c, bg=SURFACE)
        pdf_b.pack(fill='x', padx=16, pady=16)
        lbl(pdf_b, "📄  Експорт на PDF Отчет",
            font=("Helvetica", 12, "bold"), fg=WHITE, bg=SURFACE).pack(anchor='w', pady=(0, 6))
        lbl(pdf_b,
            "Генерирай красив PDF отчет с всичките ти данни за CO₂,\n"
            "графики, статистики и прогрес за избран период.",
            font=("Helvetica", 9), fg=TEXTDIM, bg=SURFACE).pack(anchor='w', pady=(0, 10))

        period_row = tk.Frame(pdf_b, bg=SURFACE)
        period_row.pack(anchor='w', pady=(0, 8))
        lbl(period_row, "Период:", font=("Helvetica", 9, "bold"),
            fg=TEXTDIM, bg=SURFACE).pack(side='left', padx=(0, 8))
        self._pdf_period = tk.StringVar(value="month")
        for txt, val in [("Последен месец", "month"),
                         ("Последни 3 месеца", "3months"),
                         ("Цялата история", "all")]:
            rb = tk.Radiobutton(period_row, text=txt, variable=self._pdf_period, value=val,
                                bg=SURFACE, fg=TEXT, selectcolor=SURFACE2,
                                activebackground=SURFACE, activeforeground=ACCENT,
                                font=("Helvetica", 9), cursor="hand2")
            rb.pack(side='left', padx=6)

        self._pdf_status = lbl(pdf_b, "", font=("Helvetica", 9), fg=TEAL, bg=SURFACE)
        self._pdf_status.pack(anchor='w', pady=(0, 6))

        pdf_btn_row = tk.Frame(pdf_b, bg=SURFACE)
        pdf_btn_row.pack(anchor='w')
        pdf_btn = tk.Button(pdf_btn_row, text="  📄  Генерирай PDF  ",
                            command=self._export_pdf)
        sty_btn(pdf_btn, success=True)
        pdf_btn.pack(side='left')

        csv_btn = tk.Button(pdf_btn_row, text="  📊  Експорт CSV  ",
                            command=self._export_csv)
        sty_btn(csv_btn)
        csv_btn.pack(side='left', padx=(10, 0))

        # ── Напомняния ─────────────────────────────
        rem_c = card(inner, accent_color=TEAL)
        rem_c.pack(fill='x', padx=18, pady=8)
        rem_b = tk.Frame(rem_c, bg=SURFACE)
        rem_b.pack(fill='x', padx=16, pady=16)
        lbl(rem_b, "🔔  Дневни Напомняния",
            font=("Helvetica", 12, "bold"), fg=WHITE, bg=SURFACE).pack(anchor='w', pady=(0, 6))
        lbl(rem_b,
            "Включи напомняне да записваш CO₂ всеки ден.\n"
            "Ще се покаже известие докато програмата е отворена.",
            font=("Helvetica", 9), fg=TEXTDIM, bg=SURFACE).pack(anchor='w', pady=(0, 10))

        rem_row = tk.Frame(rem_b, bg=SURFACE)
        rem_row.pack(fill='x')
        self._reminder_enabled = tk.BooleanVar(value=False)
        rem_cb = tk.Checkbutton(rem_row,
                                text="  🔔  Включи ежедневно напомняне",
                                variable=self._reminder_enabled,
                                bg=SURFACE, fg=TEXT, selectcolor=SURFACE2,
                                activebackground=SURFACE, activeforeground=ACCENT,
                                font=("Helvetica", 10), cursor="hand2",
                                command=self._toggle_reminder)
        rem_cb.pack(side='left')

        lbl(rem_b, "Час на напомняне:", font=("Helvetica", 9, "bold"),
            fg=TEXTDIM, bg=SURFACE).pack(anchor='w', pady=(10, 4))
        time_row = tk.Frame(rem_b, bg=SURFACE)
        time_row.pack(anchor='w')
        self._reminder_hour = tk.StringVar(value="20")
        self._reminder_min  = tk.StringVar(value="00")
        lbl(time_row, "Час:", font=("Helvetica", 9), fg=TEXTDIM, bg=SURFACE).pack(side='left')
        entry_widget(time_row, self._reminder_hour, width=4).pack(side='left', padx=4, ipady=3)
        lbl(time_row, ":", font=("Helvetica", 12, "bold"), fg=ACCENT, bg=SURFACE).pack(side='left')
        entry_widget(time_row, self._reminder_min, width=4).pack(side='left', padx=4, ipady=3)
        lbl(time_row, "(чч:мм)", font=("Helvetica", 8), fg=TEXTDIM, bg=SURFACE).pack(side='left', padx=6)

        self._reminder_status = lbl(rem_b, "Напомнянето е изключено.",
                                    font=("Helvetica", 9), fg=TEXTDIM, bg=SURFACE)
        self._reminder_status.pack(anchor='w', pady=(8, 0))

        # ── Статистика на акаунта ──────────────────
        stats_c = card(inner, accent_color=ACCENT2)
        stats_c.pack(fill='x', padx=18, pady=8)
        st_b = tk.Frame(stats_c, bg=SURFACE)
        st_b.pack(fill='x', padx=16, pady=16)
        lbl(st_b, "📊  Статистика на акаунта",
            font=("Helvetica", 12, "bold"), fg=WHITE, bg=SURFACE).pack(anchor='w', pady=(0, 10))

        total_co2   = sum(e['total_co2'] for e in self.history_data)
        transport   = sum(e['travel_co2'] for e in self.history_data)
        elec        = sum(e['electricity_co2'] for e in self.history_data)
        n           = len(self.history_data)
        months_set  = set((e['date'].year, e['date'].month) for e in self.history_data)
        avg_month   = total_co2 / max(len(months_set), 1)
        best_day    = min(self.history_data, key=lambda x: x['total_co2'])['date'].strftime('%d.%m.%Y') if self.history_data else "—"
        streak = 0
        if self.history_data:
            dates = sorted(set(e['date'].date() for e in self.history_data), reverse=True)
            today = datetime.now().date()
            for i, d in enumerate(dates):
                if (today - d).days == i:
                    streak += 1
                else:
                    break

        stat_items = [
            ("🌍", "Общо CO₂",         f"{total_co2:.1f} kg",   ACCENT2),
            ("🚗", "Транспорт CO₂",    f"{transport:.1f} kg",   GREEN),
            ("💡", "Електричество CO₂",f"{elec:.1f} kg",        WARN),
            ("📝", "Брой записи",       str(n),                  TEAL),
            ("📅", "Средно/месец",      f"{avg_month:.1f} kg",   PURPLE),
            ("🔥", "Поредни дни",       f"{streak} дни",         ERROR if streak == 0 else GREEN),
            ("🌟", "Най-добър ден",     best_day,                ACCENT3),
        ]
        stats_grid = tk.Frame(st_b, bg=SURFACE)
        stats_grid.pack(fill='x')
        for i, (icon, lab, val, clr) in enumerate(stat_items):
            if i % 3 == 0:
                row_f = tk.Frame(stats_grid, bg=SURFACE)
                row_f.pack(fill='x', pady=3)
            sf = tk.Frame(row_f, bg=SURFACE2)
            sf.pack(side='left', expand=True, fill='x', padx=3)
            lbl(sf, icon, font=("Helvetica", 18), bg=SURFACE2).pack(pady=(10, 2))
            lbl(sf, val, font=("Helvetica", 12, "bold"), fg=clr, bg=SURFACE2).pack()
            lbl(sf, lab, font=("Helvetica", 8), fg=TEXTDIM, bg=SURFACE2).pack(pady=(2, 10))

    def _export_pdf(self):
        """Генерира PDF отчет с matplotlib графики."""
        if not self.history_data:
            messagebox.showwarning("Няма данни", "Добави поне един запис преди да генерираш PDF.")
            return

        period = self._pdf_period.get()
        now    = datetime.now()
        if period == "month":
            cutoff = now - timedelta(days=30)
            period_name = "Последен месец"
        elif period == "3months":
            cutoff = now - timedelta(days=90)
            period_name = "Последни 3 месеца"
        else:
            cutoff = datetime(2000, 1, 1)
            period_name = "Цялата история"

        data = [e for e in self.history_data if e['date'] >= cutoff]
        if not data:
            messagebox.showwarning("Няма данни", f"Няма записи за периода: {period_name}")
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF файл", "*.pdf")],
            initialfile=f"ЕкоСледа_Отчет_{now.strftime('%Y%m%d')}.pdf",
            title="Запази PDF отчет"
        )
        if not path:
            return

        self._pdf_status.config(text="⏳  Генериране на PDF...", fg=TEAL)
        self.root.update()

        try:
            self._generate_pdf(path, data, period_name)
            self._pdf_status.config(text=f"✅  PDF запазен успешно!", fg=GREEN)
            if messagebox.askyesno("Готово!", "PDF отчетът е генериран! Искаш ли да го отвориш?"):
                import subprocess, sys
                if sys.platform == "win32":
                    os.startfile(path)
                else:
                    subprocess.call(["xdg-open", path])
        except Exception as e:
            self._pdf_status.config(text=f"❌  Грешка: {e}", fg=ERROR)

    def _generate_pdf(self, path: str, data: list, period_name: str):
        """Вътрешен метод — генерира реалния PDF файл."""
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as mpl_plt
        import io

        total   = sum(e['total_co2'] for e in data)
        transp  = sum(e['travel_co2'] for e in data)
        elec    = sum(e['electricity_co2'] for e in data)
        avg     = total / max(len(data), 1)

        # Build chart image in-memory
        fig, axes = mpl_plt.subplots(1, 2, figsize=(10, 3.5))
        fig.patch.set_facecolor('#0a1a0a')
        for ax in axes:
            ax.set_facecolor('#0f2310')
            ax.tick_params(colors='#e8ffe8')
            ax.spines['bottom'].set_color('#2d4a2d')
            ax.spines['left'].set_color('#2d4a2d')
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)

        # Bar by month
        from collections import defaultdict
        monthly = defaultdict(float)
        for e in data:
            key = e['date'].strftime('%m/%Y')
            monthly[key] += e['total_co2']
        keys = sorted(monthly.keys(), key=lambda x: datetime.strptime(x, '%m/%Y'))
        vals = [monthly[k] for k in keys]
        axes[0].bar(keys, vals, color='#22c55e', alpha=0.9)
        axes[0].set_title('CO₂ по месеци (kg)', color='#e8ffe8', fontsize=10)
        axes[0].set_ylabel('kg CO₂', color='#6b9b6b')
        mpl_plt.setp(axes[0].xaxis.get_majorticklabels(), rotation=45, ha='right', fontsize=8)

        # Pie transport vs electricity
        if transp + elec > 0:
            axes[1].pie([transp, elec],
                        labels=['Транспорт', 'Електричество'],
                        colors=['#22c55e', '#fbbf24'],
                        autopct='%1.0f%%', textprops={'color': '#e8ffe8'})
            axes[1].set_title('Разпределение на CO₂', color='#e8ffe8', fontsize=10)

        fig.tight_layout(pad=2.0)
        img_buf = io.BytesIO()
        fig.savefig(img_buf, format='PNG', dpi=120, facecolor=fig.get_facecolor())
        img_buf.seek(0)
        mpl_plt.close(fig)

        # Write PDF
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib import colors as rc
            from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                            Table, TableStyle, Image as RLImage, HRFlowable)
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import cm

            doc    = SimpleDocTemplate(path, pagesize=A4,
                                       leftMargin=2*cm, rightMargin=2*cm,
                                       topMargin=2*cm, bottomMargin=2*cm)
            styles = getSampleStyleSheet()
            green  = rc.HexColor('#22c55e')
            dark   = rc.HexColor('#050d05')
            gray   = rc.HexColor('#6b9b6b')

            title_style  = ParagraphStyle('T', parent=styles['Title'],
                                          textColor=green, fontSize=22, spaceAfter=4)
            sub_style    = ParagraphStyle('S', parent=styles['Normal'],
                                          textColor=gray, fontSize=10, spaceAfter=12)
            heading_style= ParagraphStyle('H', parent=styles['Heading2'],
                                          textColor=green, fontSize=13, spaceBefore=16, spaceAfter=6)
            body_style   = ParagraphStyle('B', parent=styles['Normal'],
                                          textColor=rc.HexColor('#e8ffe8'), fontSize=10, spaceAfter=4)

            story = [
                Paragraph("🌿  ЕкоСледа — CO₂ Отчет", title_style),
                Paragraph(f"Потребител: <b>{self.user_name}</b>  •  Период: {period_name}  •  Дата: {datetime.now().strftime('%d.%m.%Y')}", sub_style),
                HRFlowable(width="100%", thickness=1, color=green),
                Spacer(1, 0.4*cm),
                Paragraph("📊  Обобщение", heading_style),
            ]

            summary_data = [
                ["Показател", "Стойност"],
                ["Общо CO₂", f"{total:.1f} kg"],
                ["Транспорт CO₂", f"{transp:.1f} kg"],
                ["Електричество CO₂", f"{elec:.1f} kg"],
                ["Средно на запис", f"{avg:.1f} kg"],
                ["Брой записи", str(len(data))],
            ]
            t = Table(summary_data, colWidths=[8*cm, 8*cm])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), green),
                ('TEXTCOLOR',  (0,0), (-1,0), dark),
                ('FONTNAME',   (0,0), (-1,0), 'Helvetica-Bold'),
                ('FONTSIZE',   (0,0), (-1,-1), 10),
                ('ROWBACKGROUNDS', (0,1), (-1,-1), [rc.HexColor('#0a1a0a'), rc.HexColor('#0f2310')]),
                ('TEXTCOLOR',  (0,1), (-1,-1), rc.HexColor('#e8ffe8')),
                ('GRID',       (0,0), (-1,-1), 0.5, rc.HexColor('#2d4a2d')),
                ('PADDING',    (0,0), (-1,-1), 8),
            ]))
            story += [t, Spacer(1, 0.5*cm),
                      Paragraph("📈  Графики", heading_style),
                      RLImage(img_buf, width=16*cm, height=5.6*cm),
                      Spacer(1, 0.5*cm),
                      Paragraph("📋  Последни 10 записа", heading_style)]

            recent = sorted(data, key=lambda x: x['date'], reverse=True)[:10]
            rec_data = [["Дата", "Транспорт", "CO₂ транспорт", "CO₂ ток", "Общо CO₂"]]
            for e in recent:
                rec_data.append([
                    e['date'].strftime('%d.%m.%Y'),
                    e['transport_mode'] or "—",
                    f"{e['travel_co2']:.2f} kg",
                    f"{e['electricity_co2']:.2f} kg",
                    f"{e['total_co2']:.2f} kg",
                ])
            t2 = Table(rec_data, colWidths=[3.2*cm, 3.5*cm, 3.2*cm, 3.2*cm, 3.2*cm])
            t2.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), green),
                ('TEXTCOLOR',  (0,0), (-1,0), dark),
                ('FONTNAME',   (0,0), (-1,0), 'Helvetica-Bold'),
                ('FONTSIZE',   (0,0), (-1,-1), 9),
                ('ROWBACKGROUNDS', (0,1), (-1,-1), [rc.HexColor('#0a1a0a'), rc.HexColor('#0f2310')]),
                ('TEXTCOLOR',  (0,1), (-1,-1), rc.HexColor('#e8ffe8')),
                ('GRID',       (0,0), (-1,-1), 0.5, rc.HexColor('#2d4a2d')),
                ('PADDING',    (0,0), (-1,-1), 6),
                ('ALIGN',      (2,1), (-1,-1), 'CENTER'),
            ]))
            story.append(t2)

            story += [
                Spacer(1, 0.8*cm),
                HRFlowable(width="100%", thickness=1, color=green),
                Paragraph("❤️  Генерирано от ЕкоСледа  •  Направено за планетата 🌍",
                          ParagraphStyle('F', parent=styles['Normal'],
                                         textColor=gray, fontSize=8, alignment=1)),
            ]

            doc.build(story)

        except ImportError:
            # Fallback: plain text PDF-like file
            with open(path.replace('.pdf', '.txt'), 'w', encoding='utf-8') as f:
                f.write(f"ЕкоСледа — CO₂ Отчет\n")
                f.write(f"Потребител: {self.user_name}\n")
                f.write(f"Период: {period_name}\n")
                f.write(f"Дата: {datetime.now().strftime('%d.%m.%Y')}\n\n")
                f.write(f"Общо CO₂: {total:.1f} kg\n")
                f.write(f"Транспорт: {transp:.1f} kg\n")
                f.write(f"Електричество: {elec:.1f} kg\n")
                f.write(f"Средно: {avg:.1f} kg/запис\n")
            raise Exception("reportlab не е инсталиран. Запазен като .txt файл.")

    def _export_csv(self):
        """Експортира всички данни като CSV."""
        if not self.history_data:
            messagebox.showwarning("Няма данни", "Няма записи за експорт.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV файл", "*.csv")],
            initialfile=f"ЕкоСледа_{datetime.now().strftime('%Y%m%d')}.csv",
        )
        if not path:
            return
        try:
            import csv
            with open(path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow(["Дата", "Транспорт", "CO₂ Транспорт (kg)",
                                  "CO₂ Електричество (kg)", "Общо CO₂ (kg)",
                                  "От", "До"])
                for e in sorted(self.history_data, key=lambda x: x['date'], reverse=True):
                    writer.writerow([
                        e['date'].strftime('%d.%m.%Y'),
                        e['transport_mode'],
                        f"{e['travel_co2']:.2f}",
                        f"{e['electricity_co2']:.2f}",
                        f"{e['total_co2']:.2f}",
                        e['start_location'],
                        e['end_location'],
                    ])
            messagebox.showinfo("Успех", f"CSV файлът е запазен!\n{path}")
        except Exception as e:
            messagebox.showerror("Грешка", str(e))

    def _toggle_reminder(self):
        """Включва/изключва ежедневното напомняне."""
        if self._reminder_enabled.get():
            try:
                hour = int(self._reminder_hour.get())
                minute = int(self._reminder_min.get())
                assert 0 <= hour <= 23 and 0 <= minute <= 59
            except Exception:
                messagebox.showerror("Грешна стойност", "Въведи валиден час (0-23) и минути (0-59).")
                self._reminder_enabled.set(False)
                return
            self._reminder_status.config(
                text=f"🔔  Напомнянето е включено в {hour:02d}:{minute:02d} всеки ден.", fg=GREEN)
            self._schedule_reminder(hour, minute)
        else:
            self._reminder_status.config(text="Напомнянето е изключено.", fg=TEXTDIM)

    def _schedule_reminder(self, hour: int, minute: int):
        """Проверява часа на всеки 60 секунди и показва известие."""
        def check():
            if not self._reminder_enabled.get():
                return
            now = datetime.now()
            if now.hour == hour and now.minute == minute:
                self.root.after(0, lambda: self._show_toast(
                    f"🔔  Не забравяй да запишеш CO₂ за днес! ({now.strftime('%d.%m.%Y')})",
                    color=TEAL, duration=8000
                ))
            # Проверявай пак след 58 секунди
            threading.Timer(58, check).start()
        threading.Timer(5, check).start()

    def _save_name(self):
        new_name = self.new_name_var.get().strip()
        if not new_name:
            return
        update_name(self.user_id, new_name)
        self.user_name = new_name
        self.root.title(f"🌿 ЕкоСледа — {new_name}")
        messagebox.showinfo("Успех", f"Името е обновено на: {new_name}")

    def _save_password(self):
        pw  = self.new_pw_var.get()
        pw2 = self.new_pw2_var.get()
        if pw != pw2:
            self.pw_err.config(text="Паролите не съвпадат.")
            return
        if len(pw) < 4:
            self.pw_err.config(text="Минимум 4 символа.")
            return
        update_password(self.user_id, pw)
        self.pw_err.config(text="")
        self.new_pw_var.set("")
        self.new_pw2_var.set("")
        messagebox.showinfo("Успех", "Паролата е сменена успешно!")

    # ══════════════════════════════════════════════
    #  TAB: CO₂ БЮДЖЕТ  💰  (НОВО)
    # ══════════════════════════════════════════════
    def _create_budget_tab(self):
        tab = tk.Frame(self._content, bg=BG)
        self._pages["budget"] = tab
        _, inner = self._scrollable(tab)

        # Header
        hc = card(inner, accent_color=WARN)
        hc.pack(fill='x', padx=18, pady=(16, 4))
        hb = tk.Frame(hc, bg=SURFACE)
        hb.pack(fill='x', padx=20, pady=14)
        lbl(hb, "💰  CO₂ Бюджет", font=FONT_HEAD, fg=WHITE, bg=SURFACE).pack(anchor='w')
        lbl(hb, "Задай месечен CO₂ бюджет и следи разхода си в реално време",
            font=FONT_SUB, fg=TEXTDIM, bg=SURFACE).pack(anchor='w', pady=(2, 0))

        # ── Бюджет настройки ─────────────────────────
        set_c = card(inner, accent_color=WARN)
        set_c.pack(fill='x', padx=18, pady=8)
        sb = tk.Frame(set_c, bg=SURFACE)
        sb.pack(fill='x', padx=20, pady=16)

        lbl(sb, "⚙️  Настрой месечния бюджет",
            font=("Helvetica", 12, "bold"), fg=WHITE, bg=SURFACE).pack(anchor='w', pady=(0, 12))

        # Preset buttons
        lbl(sb, "Бързи пресети:", font=("Helvetica", 9, "bold"),
            fg=TEXTDIM, bg=SURFACE).pack(anchor='w', pady=(0, 6))
        presets_row = tk.Frame(sb, bg=SURFACE)
        presets_row.pack(anchor='w', pady=(0, 10))
        presets = [
            ("🌍 Световна норма", 417),
            ("🇪🇺 ЕС норма",      250),
            ("🌱 Еко цел",        100),
            ("⭐ Неутрален",        50),
        ]
        self._budget_var = tk.StringVar(value="250")
        for label, val in presets:
            btn = tk.Button(presets_row, text=label,
                            command=lambda v=val: (self._budget_var.set(str(v)),
                                                   self._update_budget_display()))
            sty_btn(btn)
            btn.pack(side='left', padx=(0, 8))

        # Custom input
        inp_row = tk.Frame(sb, bg=SURFACE)
        inp_row.pack(anchor='w', pady=(0, 12))
        lbl(inp_row, "Или въведи ръчно:", font=("Helvetica", 9, "bold"),
            fg=TEXTDIM, bg=SURFACE).pack(side='left', padx=(0, 10))
        budget_entry = entry_widget(inp_row, self._budget_var, width=8)
        budget_entry.pack(side='left', ipady=5)
        lbl(inp_row, "kg CO₂ / месец", font=FONT_BODY,
            fg=TEXT, bg=SURFACE).pack(side='left', padx=8)
        apply_btn = tk.Button(inp_row, text="✔  Приложи",
                              command=self._update_budget_display)
        sty_btn(apply_btn, accent=True)
        apply_btn.pack(side='left', padx=(10, 0))

        # ── Прогрес за текущия месец ─────────────────
        prog_c = card(inner, accent_color=WARN)
        prog_c.pack(fill='x', padx=18, pady=8)
        self._budget_prog_frame = tk.Frame(prog_c, bg=SURFACE)
        self._budget_prog_frame.pack(fill='x', padx=20, pady=16)
        self._build_budget_display()

        # ── История по месеци ─────────────────────────
        hist_c = card(inner, accent_color=SURFACE3)
        hist_c.pack(fill='x', padx=18, pady=8)
        hh = tk.Frame(hist_c, bg=SURFACE)
        hh.pack(fill='x', padx=16, pady=14)
        lbl(hh, "📅  Бюджет по минали месеци",
            font=("Helvetica", 12, "bold"), fg=WHITE, bg=SURFACE).pack(anchor='w', pady=(0, 10))

        if not self.history_data:
            lbl(hh, "Все още няма данни.", font=FONT_BODY, fg=TEXTDIM, bg=SURFACE).pack(anchor='w')
        else:
            from collections import defaultdict
            monthly = defaultdict(float)
            for e in self.history_data:
                k = (e['date'].year, e['date'].month)
                monthly[k] += e['total_co2']

            try:
                budget = float(self._budget_var.get() or 250)
            except ValueError:
                budget = 250

            sorted_months = sorted(monthly.keys(), reverse=True)[:12]
            for ym in sorted_months:
                y, m = ym
                used = monthly[ym]
                pct  = used / budget if budget > 0 else 0
                clr  = GREEN if pct <= 0.7 else WARN if pct <= 1.0 else ERROR
                status = "✅ В рамките" if pct <= 1.0 else f"❌ +{(pct-1)*100:.0f}% над"

                row = tk.Frame(hh, bg=SURFACE2)
                row.pack(fill='x', pady=3)

                lbl(row, f"  {calendar.month_abbr[m]} {y}",
                    font=("Helvetica", 10, "bold"), fg=TEXT, bg=SURFACE2,
                    width=10, anchor='w').pack(side='left', pady=8)

                # Mini bar
                bar_outer = tk.Frame(row, bg=SURFACE3, height=14)
                bar_outer.pack(side='left', fill='x', expand=True, padx=8, pady=10)
                bar_fill = tk.Frame(bar_outer, bg=clr, height=14)
                bar_fill.place(relx=0, rely=0, relwidth=min(pct, 1.0), relheight=1)

                lbl(row, f"{used:.0f} / {budget:.0f} kg  {status}",
                    font=("Helvetica", 9, "bold"), fg=clr,
                    bg=SURFACE2, width=28, anchor='e').pack(side='right', padx=10)

        # ── Съвети за бюджет ──────────────────────────
        tip_c = card(inner, accent_color=TEAL)
        tip_c.pack(fill='x', padx=18, pady=8)
        tip_b = tk.Frame(tip_c, bg=SURFACE)
        tip_b.pack(fill='x', padx=16, pady=14)
        lbl(tip_b, "💡  Как да останеш в бюджета?",
            font=("Helvetica", 11, "bold"), fg=WHITE, bg=SURFACE).pack(anchor='w', pady=(0, 8))
        for tip in [
            "🚶  Замени 2 пътувания с кола на ден с ходене — спести ~15 kg/месец",
            "🥗  Безмесна диета 3 дни в седмицата — спести ~25 kg/месец",
            "💡  LED крушки + интелигентен термостат — спести ~10 kg/месец",
            "🚂  Влакът вместо самолет за до 700 km — 90% по-малко CO₂",
            "♻️  Купуване на употребявано вместо ново — спести ~50 kg на покупка",
        ]:
            r = tk.Frame(tip_b, bg=SURFACE2)
            r.pack(fill='x', pady=2)
            lbl(r, f"  {tip}", font=("Helvetica", 10), fg=TEXT, bg=SURFACE2,
                wraplength=1100, justify='left').pack(anchor='w', padx=10, pady=7)

    def _build_budget_display(self):
        """Изгражда / обновява прогрес дисплея за текущия месец."""
        for w in self._budget_prog_frame.winfo_children():
            w.destroy()

        try:
            budget = float(self._budget_var.get() or 250)
        except ValueError:
            budget = 250

        now   = datetime.now()
        used  = sum(e['total_co2'] for e in self.history_data
                    if e['date'].year == now.year and e['date'].month == now.month)
        left  = budget - used
        pct   = min(used / budget, 1.0) if budget > 0 else 0
        clr   = GREEN if pct < 0.6 else WARN if pct < 0.9 else ERROR
        days_in_month = calendar.monthrange(now.year, now.month)[1]
        day_of_month  = now.day
        projected     = (used / day_of_month) * days_in_month if day_of_month > 0 else 0

        lbl(self._budget_prog_frame,
            f"📊  {calendar.month_name[now.month]} {now.year}  —  Текущо изразходване",
            font=("Helvetica", 12, "bold"), fg=WHITE, bg=SURFACE).pack(anchor='w', pady=(0, 12))

        # Big numbers row
        nums_row = tk.Frame(self._budget_prog_frame, bg=SURFACE)
        nums_row.pack(fill='x', pady=(0, 12))
        for val, lab, c in [
            (f"{used:.1f} kg",     "Изразходено",  clr),
            (f"{max(left,0):.1f} kg", "Остава",    GREEN if left > 0 else ERROR),
            (f"{budget:.0f} kg",   "Бюджет",        WARN),
            (f"{projected:.1f} kg","Прогноза",      WARN if projected > budget else TEAL),
        ]:
            nf = tk.Frame(nums_row, bg=SURFACE2)
            nf.pack(side='left', expand=True, fill='x', padx=4)
            lbl(nf, val, font=("Helvetica", 15, "bold"), fg=c, bg=SURFACE2).pack(pady=(10, 2))
            lbl(nf, lab, font=("Helvetica", 8), fg=TEXTDIM, bg=SURFACE2).pack(pady=(0, 10))

        # Big progress bar
        lbl(self._budget_prog_frame,
            f"Изразходено: {pct*100:.1f}%  (ден {day_of_month}/{days_in_month})",
            font=("Helvetica", 9, "bold"), fg=clr, bg=SURFACE).pack(anchor='w', pady=(0, 4))

        bar_outer = tk.Frame(self._budget_prog_frame, bg=SURFACE3, height=28)
        bar_outer.pack(fill='x', pady=(0, 8))
        bar_outer.pack_propagate(False)
        bar_fill = tk.Frame(bar_outer, bg=clr, height=28)
        bar_fill.place(relx=0, rely=0, relwidth=pct, relheight=1)
        # Day marker
        day_pct = day_of_month / days_in_month
        marker  = tk.Frame(bar_outer, bg=WHITE, width=2, height=28)
        marker.place(relx=day_pct, rely=0, relheight=1)

        if projected > budget:
            excess = projected - budget
            lbl(self._budget_prog_frame,
                f"⚠️  Прогнозата показва {excess:.0f} kg над бюджета! Намали разхода.",
                font=("Helvetica", 10, "bold"), fg=ERROR, bg=SURFACE).pack(anchor='w', pady=(4, 0))
        elif left > 0:
            daily_left = left / max(days_in_month - day_of_month, 1)
            lbl(self._budget_prog_frame,
                f"✅  Оставащо дневно: {daily_left:.1f} kg CO₂ (до края на месеца)",
                font=("Helvetica", 10, "bold"), fg=GREEN, bg=SURFACE).pack(anchor='w', pady=(4, 0))

    def _update_budget_display(self):
        self._build_budget_display()

    # ══════════════════════════════════════════════
    #  WEEKLY SUMMARY POPUP  (НОВО)
    # ══════════════════════════════════════════════
    def _show_weekly_summary(self):
        """Показва красив popup с резюме на изминалата седмица."""
        now    = datetime.now()
        week_ago = now - timedelta(days=7)
        week_data = [e for e in self.history_data if e['date'] >= week_ago]
        if not week_data:
            return

        total   = sum(e['total_co2'] for e in week_data)
        transp  = sum(e['travel_co2'] for e in week_data)
        elec    = sum(e['electricity_co2'] for e in week_data)
        n       = len(week_data)
        avg     = total / n if n > 0 else 0

        # Compare to previous week
        prev_week_ago = week_ago - timedelta(days=7)
        prev_data = [e for e in self.history_data
                     if prev_week_ago <= e['date'] < week_ago]
        prev_total = sum(e['total_co2'] for e in prev_data)
        diff = total - prev_total
        diff_str = (f"{'📈 +' if diff > 0 else '📉 '}{abs(diff):.1f} kg от миналата седмица"
                    if prev_data else "")

        win = tk.Toplevel(self.root)
        win.title("📊 Седмично резюме")
        win.configure(bg=BG)
        win.resizable(False, False)
        w, h = 520, 460
        sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
        win.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

        # Gradient top bar
        bar = tk.Frame(win, bg=BG, height=8)
        bar.pack(fill='x')
        bar.pack_propagate(False)
        for clr in [ACCENT2, ACCENT3, GREEN, TEAL, GREEN, ACCENT3, ACCENT2]:
            tk.Frame(bar, bg=clr, height=8).pack(side='left', fill='both', expand=True)

        body = tk.Frame(win, bg=BG)
        body.pack(fill='both', expand=True, padx=30, pady=20)

        lbl(body, "📊  Седмично Резюме", font=("Helvetica", 20, "bold"),
            fg=WHITE, bg=BG).pack(anchor='w')
        lbl(body, f"{(now - timedelta(days=7)).strftime('%d.%m')} — {now.strftime('%d.%m.%Y')}",
            font=FONT_BODY, fg=TEXTDIM, bg=BG).pack(anchor='w', pady=(2, 16))

        # Stats grid
        stats_row = tk.Frame(body, bg=BG)
        stats_row.pack(fill='x', pady=(0, 16))
        for val, lab, clr in [
            (f"{total:.1f} kg",  "Общо CO₂",   ACCENT2),
            (f"{avg:.1f} kg",    "Средно/ден",  TEAL),
            (str(n),             "Записа",       GREEN),
        ]:
            sf = tk.Frame(stats_row, bg=SURFACE2)
            sf.pack(side='left', expand=True, fill='x', padx=4)
            lbl(sf, val, font=("Helvetica", 16, "bold"), fg=clr, bg=SURFACE2).pack(pady=(12, 2))
            lbl(sf, lab, font=("Helvetica", 9), fg=TEXTDIM, bg=SURFACE2).pack(pady=(0, 12))

        if diff_str:
            diff_clr = ERROR if diff > 0 else GREEN
            lbl(body, diff_str, font=("Helvetica", 10, "bold"),
                fg=diff_clr, bg=BG).pack(anchor='w', pady=(0, 12))

        # Mini breakdown
        tk.Frame(body, bg=SURFACE3, height=1).pack(fill='x', pady=(0, 12))
        for lab, val, clr in [("🚗 Транспорт:", f"{transp:.1f} kg", GREEN),
                               ("💡 Електричество:", f"{elec:.1f} kg", WARN)]:
            r = tk.Frame(body, bg=BG)
            r.pack(fill='x', pady=2)
            lbl(r, lab, font=FONT_BODY, fg=TEXTDIM, bg=BG).pack(side='left')
            lbl(r, val, font=("Helvetica", 11, "bold"), fg=clr, bg=BG).pack(side='right')

        tk.Frame(body, bg=SURFACE3, height=1).pack(fill='x', pady=12)

        # Motivational message
        if avg < 5:
            msg, msg_clr = "🏆  Фантастична седмица! Ти си еко-шампион!", GREEN
        elif avg < 15:
            msg, msg_clr = "🌿  Добра седмица! Продължавай в същия дух.", TEAL
        else:
            msg, msg_clr = "💪  Можеш по-добре! Опитай безмесен ден или колело.", WARN
        lbl(body, msg, font=("Helvetica", 11, "bold"), fg=msg_clr, bg=BG).pack(anchor='w')

        tk.Frame(body, bg=BG).pack(expand=True)
        close_btn = tk.Button(body, text="  ✔  Затвори  ", command=win.destroy)
        sty_btn(close_btn, accent=True)
        close_btn.pack(pady=(0, 10))

    # ──────────────────────────────────────────────
    #  UTILITY METHODS
    # ──────────────────────────────────────────────
    def _refresh_all(self):
        self.history_data = load_entries(self.user_id)
        try:
            self._update_progress()
        except Exception:
            pass
        try:
            self._update_impact()
        except Exception:
            pass
        try:
            self._refresh_welcome_stats()
        except Exception:
            pass
        try:
            self._refresh_history_table()
        except Exception:
            pass

    def _show_toast(self, message, color=None, duration=2500):
        """Show a floating toast notification."""
        color = color or ACCENT2
        toast = tk.Toplevel(self.root)
        toast.overrideredirect(True)
        toast.configure(bg=SURFACE2)
        toast.attributes('-topmost', True)
        # Position bottom-right
        self.root.update_idletasks()
        rx = self.root.winfo_x() + self.root.winfo_width() - 360
        ry = self.root.winfo_y() + self.root.winfo_height() - 80
        toast.geometry(f"340x50+{rx}+{ry}")
        tk.Frame(toast, bg=color, width=5).pack(side='left', fill='y')
        tk.Label(toast, text=message, font=("Helvetica", 10, "bold"),
                 fg=TEXT, bg=SURFACE2, padx=16, pady=12).pack(side='left', fill='both', expand=True)
        toast.after(duration, toast.destroy)

    def _refresh_welcome_stats(self):
        """Refresh the stat pills on the welcome tab after new data is entered."""
        if not hasattr(self, '_welcome_stats_frame'):
            return
        for w in self._welcome_stats_frame.winfo_children():
            w.destroy()
        today     = datetime.now()
        last30    = [e for e in self.history_data if (today - e['date']).days <= 30]
        total_all = sum(e['total_co2'] for e in self.history_data)
        total_30  = sum(e['total_co2'] for e in last30)
        days_used = len(set(e['date'].date() for e in self.history_data))
        f = self._welcome_stats_frame
        self._stat_pill(f, "📊  Последни 30 дни", f"{total_30:.0f} kg CO₂", ACCENT)
        self._stat_pill(f, "🌍  Общо записано",    f"{total_all:.0f} kg CO₂", GREEN)
        self._stat_pill(f, "📅  Дни активност",    str(days_used),             TEAL)

    def _export_data(self):
        if not self.history_data:
            messagebox.showwarning("Без данни", "Няма данни за експортиране.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV файлове", "*.csv")],
            title="Запази CSV")
        if not path:
            return
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write("Дата,Транспорт(kg),Електричество(kg),Общо(kg),Начало,Край,Транспортно средство\n")
                for e in self.history_data:
                    f.write(f"{e['date'].strftime('%Y-%m-%d')},{e['travel_co2']:.2f},"
                            f"{e['electricity_co2']:.2f},{e['total_co2']:.2f},"
                            f"{e['start_location']},{e['end_location']},{e['transport_mode']}\n")
            messagebox.showinfo("Готово", f"Данните са запазени в:\n{path}")
        except Exception as ex:
            messagebox.showerror("Грешка", str(ex))

    def _show_about(self):
        w = tk.Toplevel(self.root)
        w.title("Относно ЕкоСледа")
        w.geometry("440x360")
        w.configure(bg=BG)
        # Gradient top bar
        bar = tk.Frame(w, bg=BG, height=5)
        bar.pack(fill='x')
        for clr in [ACCENT2, ACCENT3, GREEN, TEAL, GREEN, ACCENT3, ACCENT2]:
            tk.Frame(bar, bg=clr, height=5).pack(side='left', fill='both', expand=True)
        lbl(w, "🌿", font=("Helvetica", 52), bg=BG, fg=GREEN).pack(pady=(20, 4))
        lbl(w, "ЕкоСледа", font=("Helvetica", 20, "bold"), fg=ACCENT, bg=BG).pack()
        lbl(w, "Въглероден Тракер с онлайн база данни\n\n"
               "☁️ Supabase • Python • tkinter\n\n"
               "🏆 Постижения  •  🎯 Цели  •  📋 История\n"
               "⚖️ Сравни периоди  •  🔔 Известия\n\n"
               "❤️ направено с любов към планетата",
            font=FONT_BODY, fg=TEXTDIM, bg=BG, justify='center').pack(pady=10)
        btn = tk.Button(w, text="  Затвори  ", command=w.destroy)
        sty_btn(btn, accent=True)
        btn.pack(pady=8)

    def _fetch_eco_news(self):
        try:
            url = "https://www.bbc.com/news/science-environment-56837908"
            r = requests.get(url, timeout=8)
            soup = BeautifulSoup(r.text, 'html.parser')
            headlines = [h.text.strip() for h in soup.find_all('h3') if h.text.strip()][:6]

            w = tk.Toplevel(self.root)
            w.title("Еко Новини")
            w.geometry("620x420")
            w.configure(bg=BG)
            lbl(w, "🌎  Последни Новини за Средата",
                font=("Georgia", 15, "bold"), fg=ACCENT, bg=BG).pack(pady=12)
            t = tk.Text(w, wrap=tk.WORD, font=FONT_BODY, bg=SURFACE, fg=TEXT,
                        padx=16, pady=12, bd=0)
            t.pack(fill='both', expand=True, padx=16, pady=(0, 8))
            for i, h in enumerate(headlines, 1):
                t.insert(tk.END, f"{i}. {h}\n\n")
            t.config(state='disabled')
        except Exception as e:
            messagebox.showerror("Грешка", f"Не може да се зареди: {e}")

    def _logout(self):
        if messagebox.askyesno("Изход", "Сигурен ли си, че искаш да излезеш?"):
            self.root.destroy()
            start_app()

# ─────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────

def start_app():
    def on_login(uid, name):
        root = tk.Tk()
        CarbonFootprintApp(root, uid, name)
        root.mainloop()

    AuthWindow(on_login)

if __name__ == "__main__":
    init_db()
    start_app()