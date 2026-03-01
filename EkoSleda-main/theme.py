# ═══════════════════════════════════════════════
#  theme.py  —  Цветова палитра, шрифтове и UI хелпъри
# ═══════════════════════════════════════════════

import tkinter as tk

# ── Neon Green Cyberpunk Palette ──
BG       = "#050d05"      # near-black deep forest
SURFACE  = "#0a1a0a"      # card bg
SURFACE2 = "#0f2310"      # elevated card
SURFACE3 = "#152b16"      # hover/active
ACCENT   = "#4ade80"      # neon leaf green
ACCENT2  = "#22c55e"      # primary green
ACCENT3  = "#86efac"      # light mint
GREEN    = "#39ff14"      # pure neon green
TEAL     = "#2dd4bf"      # teal accent
DIM      = "#2d4a2d"
TEXT     = "#e8ffe8"
TEXTDIM  = "#6b9b6b"
ERROR    = "#ff4d4d"
WARN     = "#fbbf24"
WHITE    = "#ffffff"
PURPLE   = "#c084fc"
PINK     = "#f9a8d4"

# ── Fonts ──
FONT_TITLE = ("Helvetica", 22, "bold")
FONT_HEAD  = ("Helvetica", 14, "bold")
FONT_SUB   = ("Helvetica", 10)
FONT_BODY  = ("Helvetica", 11)
FONT_MONO  = ("Courier", 10)
FONT_LARGE = ("Helvetica", 28, "bold")


# ── Widget Helpers ──

def sty_btn(btn, accent=False, danger=False, success=False):
    """Прилага тъмна тема към tk.Button."""
    if danger:
        btn.configure(bg=ERROR, fg=WHITE, font=("Helvetica", 10, "bold"),
                      relief=tk.FLAT, cursor="hand2", padx=16, pady=8,
                      activebackground="#cc0000", activeforeground=WHITE)
    elif success:
        btn.configure(bg=GREEN, fg=BG, font=("Helvetica", 10, "bold"),
                      relief=tk.FLAT, cursor="hand2", padx=16, pady=8,
                      activebackground=TEAL, activeforeground=BG)
    elif accent:
        btn.configure(bg=ACCENT2, fg=WHITE, font=("Helvetica", 10, "bold"),
                      relief=tk.FLAT, cursor="hand2", padx=16, pady=8,
                      activebackground=ACCENT, activeforeground=WHITE)
    else:
        btn.configure(bg=SURFACE3, fg=TEXT, font=("Helvetica", 10),
                      relief=tk.FLAT, cursor="hand2", padx=16, pady=8,
                      activebackground=SURFACE2, activeforeground=ACCENT)


def lbl(parent, text, font=FONT_BODY, fg=TEXT, bg=None, **kw):
    return tk.Label(parent, text=text, font=font, fg=fg,
                    bg=bg or parent.cget("bg"), **kw)


def entry_widget(parent, var=None, width=30, show=None):
    return tk.Entry(parent, textvariable=var, width=width, show=show,
                    bg=SURFACE3, fg=TEXT, insertbackground=ACCENT,
                    relief=tk.FLAT, font=FONT_BODY,
                    highlightthickness=1, highlightbackground=DIM,
                    highlightcolor=ACCENT2)


def card(parent, accent_color=None, **kw):
    f = tk.Frame(parent, bg=SURFACE, bd=0, **kw)
    if accent_color:
        tk.Frame(f, bg=accent_color, height=2).pack(fill='x', side='top')
    return f


def glowing_card(parent, **kw):
    """Карта с цветна рамка."""
    outer = tk.Frame(parent, bg=ACCENT2, bd=0, **kw)
    inner = tk.Frame(outer, bg=SURFACE, bd=0)
    inner.pack(fill='both', expand=True, padx=1, pady=1)
    return outer, inner


def divider(parent, color=None):
    tk.Frame(parent, height=1, bg=color or SURFACE3).pack(fill='x', padx=20)


def badge(parent, text, color=ACCENT2, bg=None):
    """Малък оцветен badge/pill."""
    f = tk.Frame(parent, bg=color, bd=0)
    tk.Label(f, text=text, font=("Helvetica", 8, "bold"),
             fg=WHITE, bg=color, padx=8, pady=2).pack()
    return f


def gradient_bar(parent, colors=None, height=4):
    """Симулира градиентна лента с множество тънки frames."""
    colors = colors or [ACCENT2, ACCENT3, GREEN, TEAL, GREEN, ACCENT3, ACCENT2]
    bar = tk.Frame(parent, bg=BG, height=height)
    bar.pack(fill='x')
    bar.pack_propagate(False)
    for clr in colors:
        tk.Frame(bar, bg=clr, height=height).pack(
            side='left', fill='both', expand=True)
    return bar
