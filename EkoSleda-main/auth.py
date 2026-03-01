# ═══════════════════════════════════════════════
#  auth.py  —  Прозорец за вход и регистрация
# ═══════════════════════════════════════════════

import tkinter as tk
from tkinter import ttk

from theme import (BG, SURFACE, SURFACE2, SURFACE3,
                   ACCENT, ACCENT2, ACCENT3, GREEN, TEAL,
                   TEXT, TEXTDIM, ERROR, WHITE, WARN, PURPLE,
                   FONT_BODY, lbl, entry_widget, sty_btn, card)
from database import login_user, register_user


class AuthWindow:
    def __init__(self, on_success):
        self.on_success = on_success
        self.win = tk.Tk()
        self.win.title("ЕкоСледа")
        # По-голям прозорец — центриран на екрана
        w, h = 740, 820
        sw = self.win.winfo_screenwidth()
        sh = self.win.winfo_screenheight()
        x  = (sw - w) // 2
        y  = (sh - h) // 2
        self.win.geometry(f"{w}x{h}+{x}+{y}")
        self.win.resizable(False, False)
        self.win.configure(bg=BG)
        self._notebook = None
        self._build()
        self.win.mainloop()

    # ────────────────────────────────────────────
    def _build(self):
        # Градиентна лента
        bar = tk.Frame(self.win, bg=BG, height=8)
        bar.pack(fill='x')
        bar.pack_propagate(False)
        for clr in [ACCENT2, ACCENT3, GREEN, TEAL, GREEN, ACCENT3, ACCENT2]:
            tk.Frame(bar, bg=clr, height=8).pack(side='left', fill='both', expand=True)

        # ── Лява / дясна колона ──────────────────
        body = tk.Frame(self.win, bg=BG)
        body.pack(fill='both', expand=True)

        left  = tk.Frame(body, bg=SURFACE2, width=280)
        left.pack(side='left', fill='y')
        left.pack_propagate(False)
        right = tk.Frame(body, bg=BG)
        right.pack(side='left', fill='both', expand=True)

        self._build_left_panel(left)
        self._build_right_panel(right)

    # ── Лява декоративна колона ──────────────────
    def _build_left_panel(self, p):
        # Лого
        logo_outer = tk.Frame(p, bg=ACCENT2, width=100, height=100)
        logo_outer.pack(pady=(50, 20))
        logo_outer.pack_propagate(False)
        lbl(logo_outer, "🌿", font=("Helvetica", 52),
            bg=ACCENT2, fg=WHITE).pack(expand=True)

        lbl(p, "ЕкоСледа", font=("Helvetica", 28, "bold"),
            fg=WHITE, bg=SURFACE2).pack()
        lbl(p, "Pro v4.0", font=("Helvetica", 13),
            fg=ACCENT, bg=SURFACE2).pack(pady=(0, 6))
        lbl(p, "Въглероден тракер\nс облачна база данни",
            font=("Helvetica", 10), fg=TEXTDIM, bg=SURFACE2,
            justify='center').pack(pady=(0, 30))

        # Разделител
        tk.Frame(p, bg=SURFACE3, height=1, width=200).pack(pady=10)

        # Характеристики
        features = [
            ("🌿", "Следи CO₂"),
            ("🗺️",  "Интерактивна карта"),
            ("📊", "Графики и анализи"),
            ("🏆", "Постижения"),
            ("🎯", "Лични цели"),
            ("☁️",  "Облачна синхронизация"),
        ]
        feat_f = tk.Frame(p, bg=SURFACE2)
        feat_f.pack(fill='x', padx=20, pady=10)
        for icon, txt in features:
            row = tk.Frame(feat_f, bg=SURFACE2)
            row.pack(fill='x', pady=5)
            lbl(row, icon, font=("Helvetica", 14), bg=SURFACE2,
                width=3).pack(side='left')
            lbl(row, txt, font=("Helvetica", 10), fg=TEXTDIM,
                bg=SURFACE2).pack(side='left', padx=6)

        # Долна лента
        tk.Frame(p, bg=SURFACE3, height=1, width=200).pack(pady=(20, 10))
        lbl(p, "❤️ направено за планетата",
            font=("Helvetica", 8), fg=SURFACE3, bg=SURFACE2).pack()

    # ── Дясна страна с Notebook ──────────────────
    def _build_right_panel(self, p):
        # Notebook
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Auth.TNotebook', background=BG, borderwidth=0)
        style.configure('Auth.TNotebook.Tab',
                        background=SURFACE2, foreground=TEXTDIM,
                        font=("Helvetica", 11, "bold"), padding=[28, 12])
        style.map('Auth.TNotebook.Tab',
                  background=[('selected', ACCENT2)],
                  foreground=[('selected', WHITE)])

        self._nb = ttk.Notebook(p, style='Auth.TNotebook')
        self.login_frame = tk.Frame(self._nb, bg=BG, padx=48, pady=28)
        self.reg_frame   = tk.Frame(self._nb, bg=BG, padx=48, pady=28)
        self._nb.add(self.login_frame, text="  🔑  Вход  ")
        self._nb.add(self.reg_frame,   text="  ✨  Регистрация  ")
        self._nb.pack(fill='both', expand=True, padx=0, pady=0)

        self._build_login()
        self._build_register()

    # ── Поле ──────────────────────────────────────
    def _field(self, parent, label_text, var, show=None, tip=None):
        lbl(parent, label_text, font=("Helvetica", 10, "bold"),
            fg=TEXTDIM, bg=BG).pack(anchor='w', pady=(14, 3))
        e = entry_widget(parent, var, width=40, show=show)
        e.pack(fill='x', ipady=8)
        if tip:
            lbl(parent, tip, font=("Helvetica", 8), fg=SURFACE3, bg=BG).pack(anchor='w')
        return e

    # ── Вход ──────────────────────────────────────
    def _build_login(self):
        p = self.login_frame

        lbl(p, "Добре дошъл обратно! 👋",
            font=("Helvetica", 18, "bold"), fg=WHITE, bg=BG).pack(anchor='w')
        lbl(p, "Влез с твоите данни",
            font=("Helvetica", 10), fg=TEXTDIM, bg=BG).pack(anchor='w', pady=(2, 16))

        # Разделител
        tk.Frame(p, bg=SURFACE3, height=1).pack(fill='x', pady=(0, 10))

        self.l_user = tk.StringVar()
        self.l_pass = tk.StringVar()
        e1 = self._field(p, "👤  Потребителско Име", self.l_user)
        e2 = self._field(p, "🔒  Парола", self.l_pass, show="●")

        # Enter triggers login
        e1.bind('<Return>', lambda _: e2.focus_set())
        e2.bind('<Return>', lambda _: self._do_login())

        self.l_err     = lbl(p, "", font=("Helvetica", 9), fg=ERROR, bg=BG)
        self.l_loading = lbl(p, "", font=("Helvetica", 9), fg=TEAL,  bg=BG)
        self.l_err.pack(anchor='w', pady=(10, 0))
        self.l_loading.pack(anchor='w')

        btn = tk.Button(p, text="  ➜  Влез в профила",
                        command=self._do_login)
        sty_btn(btn, accent=True)
        btn.pack(fill='x', pady=16, ipady=6)

        # Линк към регистрация
        sep = tk.Frame(p, bg=SURFACE3, height=1)
        sep.pack(fill='x', pady=8)

        link_f = tk.Frame(p, bg=BG)
        link_f.pack(anchor='w')
        lbl(link_f, "Нямаш акаунт?  ",
            font=("Helvetica", 10), fg=TEXTDIM, bg=BG).pack(side='left')
        reg_link = tk.Label(link_f, text="✨  Регистрирай се тук →",
                            font=("Helvetica", 10, "bold"),
                            fg=ACCENT, bg=BG, cursor="hand2")
        reg_link.pack(side='left')
        reg_link.bind("<Button-1>", lambda _: self._nb.select(1))
        reg_link.bind("<Enter>",   lambda _: reg_link.config(fg=GREEN))
        reg_link.bind("<Leave>",   lambda _: reg_link.config(fg=ACCENT))

    def _do_login(self):
        self.l_err.config(text="")
        self.l_loading.config(text="⏳ Влизане...")
        self.win.update()
        uid, name, err = login_user(self.l_user.get(), self.l_pass.get())
        self.l_loading.config(text="")
        if err:
            self.l_err.config(text=f"❌  {err}")
        else:
            self.win.destroy()
            self.on_success(uid, name)

    # ── Регистрация ────────────────────────────────
    def _build_register(self):
        p = self.reg_frame

        lbl(p, "Създай безплатен акаунт 🚀",
            font=("Helvetica", 18, "bold"), fg=WHITE, bg=BG).pack(anchor='w')
        lbl(p, "Присъедини се и започни да следиш CO₂",
            font=("Helvetica", 10), fg=TEXTDIM, bg=BG).pack(anchor='w', pady=(2, 16))

        tk.Frame(p, bg=SURFACE3, height=1).pack(fill='x', pady=(0, 10))

        self.r_name  = tk.StringVar()
        self.r_user  = tk.StringVar()
        self.r_pass  = tk.StringVar()
        self.r_pass2 = tk.StringVar()

        e1 = self._field(p, "✨  Твоето Пълно Име",  self.r_name,
                         tip="Например: Иван Петров")
        e2 = self._field(p, "👤  Потребителско Име", self.r_user,
                         tip="Само латински букви и цифри")
        e3 = self._field(p, "🔒  Парола",            self.r_pass,  show="●",
                         tip="Поне 4 символа")
        e4 = self._field(p, "🔒  Потвърди Паролата", self.r_pass2, show="●")

        e1.bind('<Return>', lambda _: e2.focus_set())
        e2.bind('<Return>', lambda _: e3.focus_set())
        e3.bind('<Return>', lambda _: e4.focus_set())
        e4.bind('<Return>', lambda _: self._do_register())

        self.r_err     = lbl(p, "", font=("Helvetica", 9), fg=ERROR, bg=BG)
        self.r_loading = lbl(p, "", font=("Helvetica", 9), fg=TEAL,  bg=BG)
        self.r_err.pack(anchor='w', pady=(10, 0))
        self.r_loading.pack(anchor='w')

        btn = tk.Button(p, text="  ✅  Създай Акаунт",
                        command=self._do_register)
        sty_btn(btn, success=True)
        btn.pack(fill='x', pady=14, ipady=6)

        # Линк към вход
        sep = tk.Frame(p, bg=SURFACE3, height=1)
        sep.pack(fill='x', pady=8)

        link_f = tk.Frame(p, bg=BG)
        link_f.pack(anchor='w')
        lbl(link_f, "Вече имаш акаунт?  ",
            font=("Helvetica", 10), fg=TEXTDIM, bg=BG).pack(side='left')
        login_link = tk.Label(link_f, text="🔑  Влез тук →",
                              font=("Helvetica", 10, "bold"),
                              fg=ACCENT, bg=BG, cursor="hand2")
        login_link.pack(side='left')
        login_link.bind("<Button-1>", lambda _: self._nb.select(0))
        login_link.bind("<Enter>",   lambda _: login_link.config(fg=GREEN))
        login_link.bind("<Leave>",   lambda _: login_link.config(fg=ACCENT))

    def _do_register(self):
        name = self.r_name.get().strip()
        user = self.r_user.get().strip()
        pw   = self.r_pass.get()
        pw2  = self.r_pass2.get()
        if not name or not user or not pw:
            self.r_err.config(text="❌  Моля, попълнете всички полета.")
            return
        if pw != pw2:
            self.r_err.config(text="❌  Паролите не съвпадат.")
            return
        if len(pw) < 4:
            self.r_err.config(text="❌  Паролата трябва да е поне 4 символа.")
            return
        self.r_err.config(text="")
        self.r_loading.config(text="⏳ Регистрация...")
        self.win.update()
        uid, err = register_user(user, pw, name)
        self.r_loading.config(text="")
        if err:
            self.r_err.config(text=f"❌  {err}")
        else:
            self.win.destroy()
            self.on_success(uid, name)
