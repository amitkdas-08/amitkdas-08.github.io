"""Generate a unique SVG illustration for every publication and insert it into publications.html.

Usage: python tools/gen_thumbs.py <site_root>
Idempotent: existing .pub-thumb blocks are replaced. Every paper has its own drawing (see ART),
mixing scenes, UI mock-ups, result charts, diagrams and typographic pieces so no two look alike.
"""
import html, math, os, random, re, sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else "."
PUBS = os.path.join(ROOT, "publications.html")
OUT = os.path.join(ROOT, "img", "pubs")
os.makedirs(OUT, exist_ok=True)

W, H = 240, 150
SANS = "'Inter','Segoe UI',Helvetica,Arial,sans-serif"
MONO = "'IBM Plex Mono',Consolas,monospace"
BN = "'Nirmala UI','Kohinoor Bangla','Bangla Sangam MN','Noto Sans Bengali',Vrinda,sans-serif"
INK, MUTED, FAINT, LINE = "#334155", "#94A3B8", "#CBD5E1", "#E2E8F0"


# ------------------------------------------------------------------ primitives
def at(**kw):
    return " ".join(f'{k.rstrip("_").replace("_", "-")}="{v}"' for k, v in kw.items() if v is not None)


def f(v):
    return f"{v:.1f}".rstrip("0").rstrip(".") if isinstance(v, float) else str(v)


def R(x, y, w, h, fill, rx=0, **kw):
    return f'<rect x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h)}" rx="{f(rx)}" fill="{fill}" {at(**kw)}/>'


def C(cx, cy, r, fill, **kw):
    return f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{f(r)}" fill="{fill}" {at(**kw)}/>'


def E(cx, cy, rx, ry, fill, **kw):
    return f'<ellipse cx="{f(cx)}" cy="{f(cy)}" rx="{f(rx)}" ry="{f(ry)}" fill="{fill}" {at(**kw)}/>'


def L(x1, y1, x2, y2, stroke, sw=1, **kw):
    return f'<line x1="{f(x1)}" y1="{f(y1)}" x2="{f(x2)}" y2="{f(y2)}" stroke="{stroke}" stroke-width="{sw}" {at(**kw)}/>'


def P(d, fill="none", **kw):
    return f'<path d="{d}" fill="{fill}" {at(**kw)}/>'


def PL(pts, stroke, sw=1.5, fill="none", **kw):
    return f'<polyline points="{" ".join(f"{f(x)},{f(y)}" for x, y in pts)}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" stroke-linejoin="round" stroke-linecap="round" {at(**kw)}/>'


def PG(pts, fill, **kw):
    return f'<polygon points="{" ".join(f"{f(x)},{f(y)}" for x, y in pts)}" fill="{fill}" {at(**kw)}/>'


def T(x, y, s, size=9, fill=INK, w=400, anchor="start", fam=SANS, **kw):
    return (f'<text x="{f(x)}" y="{f(y)}" font-family="{fam}" font-size="{size}" font-weight="{w}" fill="{fill}" '
            f'text-anchor="{anchor}" {at(**kw)}>{html.escape(s)}</text>')


def G(body, **kw):
    return f"<g {at(**kw)}>{body}</g>"


def lin(id_, stops, x2=0, y2=1):
    s = "".join(f'<stop offset="{o}" stop-color="{c}"/>' for o, c in stops)
    return f'<defs><linearGradient id="{id_}" x1="0" y1="0" x2="{x2}" y2="{y2}">{s}</linearGradient></defs>'


def rad(id_, stops, cx=.5, cy=.5, r=.5):
    s = "".join(f'<stop offset="{o}" stop-color="{c}" {"stop-opacity=" + chr(34) + str(op) + chr(34) if op is not None else ""}/>' for o, c, op in stops)
    return f'<defs><radialGradient id="{id_}" cx="{cx}" cy="{cy}" r="{r}">{s}</radialGradient></defs>'


def bg(fill):
    return R(0, 0, W, H, fill)


def arrow(x1, y1, x2, y2, col=MUTED, sw=1.6, head=5):
    a = math.atan2(y2 - y1, x2 - x1)
    p1 = (x2 - head * math.cos(a - .45), y2 - head * math.sin(a - .45))
    p2 = (x2 - head * math.cos(a + .45), y2 - head * math.sin(a + .45))
    return L(x1, y1, x2 - head * .6 * math.cos(a), y2 - head * .6 * math.sin(a), col, sw) + PG([(x2, y2), p1, p2], col)


def dotgrid(col, step=12, r=.7, x0=6, y0=6):
    return "".join(C(x, y, r, col) for x in range(x0, W, step) for y in range(y0, H, step))


def rnd(seed):
    return random.Random(seed)


# ------------------------------------------------------------------ icons
def person(x, y, s, col, **kw):
    return G(C(x, y - 9 * s, 4.6 * s, col) + P(f"M{f(x-8*s)} {f(y+6*s)} q0 -11 {f(8*s)} -11 q{f(8*s)} 0 {f(8*s)} 11z", col), **kw)


def cloud(x, y, s, col, **kw):
    return G(C(x + 9 * s, y, 9 * s, col) + C(x + 22 * s, y - 7 * s, 12 * s, col) + C(x + 36 * s, y, 9 * s, col)
             + R(x + 9 * s, y - 2 * s, 27 * s, 11 * s, col), **kw)


def phone(x, y, w, h, frame=INK, screen="#FFFFFF"):
    return R(x, y, w, h, frame, 7) + R(x + 3, y + 8, w - 6, h - 16, screen, 2) + R(x + w / 2 - 6, y + 3, 12, 2, "#64748B", 1)


def browser(x, y, w, h, frame="#FFFFFF", bar="#F1F5F9", stroke=LINE):
    return (R(x, y, w, h, frame, 6, stroke=stroke) + R(x, y, w, 12, bar, 6) + R(x, y + 6, w, 6, bar)
            + C(x + 7, y + 6, 2, "#F87171") + C(x + 13, y + 6, 2, "#FBBF24") + C(x + 19, y + 6, 2, "#34D399"))


def car(x, y, s, col, win="#E0F2FE"):
    b = P(f"M{f(x)} {f(y+10*s)} v-6 q0 -3 3 -3 h{f(6*s)} l{f(6*s)} -7 h{f(16*s)} l{f(7*s)} 7 h{f(5*s)} q3 0 3 3 v6z", col)
    b += P(f"M{f(x+11*s)} {f(y+3*s)} l{f(4*s)} -5 h{f(7*s)} v5z M{f(x+24*s)} {f(y+3*s)} v-5 h{f(5*s)} l{f(5*s)} 5z", win)
    b += C(x + 10 * s, y + 10 * s, 4 * s, "#1F2937") + C(x + 32 * s, y + 10 * s, 4 * s, "#1F2937")
    b += C(x + 10 * s, y + 10 * s, 1.6 * s, "#CBD5E1") + C(x + 32 * s, y + 10 * s, 1.6 * s, "#CBD5E1")
    return b


def leaf(cx, cy, s, rot, col, vein="#FFFFFF"):
    d = f"M0 {f(-30*s)} C{f(22*s)} {f(-18*s)} {f(22*s)} {f(18*s)} 0 {f(30*s)} C{f(-22*s)} {f(18*s)} {f(-22*s)} {f(-18*s)} 0 {f(-30*s)}z"
    v = L(0, -28 * s, 0, 30 * s, vein, 1.2, opacity=".7")
    for k in range(-2, 3):
        v += P(f"M0 {f(k*9*s)} q{f(7*s)} {f(-4*s)} {f(13*s)} {f(-9*s)} M0 {f(k*9*s)} q{f(-7*s)} {f(-4*s)} {f(-13*s)} {f(-9*s)}", stroke=vein, stroke_width=.8, opacity=".55")
    return G(P(d, col) + v, transform=f"translate({f(cx)},{f(cy)}) rotate({rot})")


def server(x, y, w, h, col, led="#34D399", n=4):
    b = R(x, y, w, h, col, 2)
    for i in range(n):
        yy = y + 3 + i * (h - 6) / n
        b += R(x + 3, yy, w - 6, (h - 6) / n - 2, "#FFFFFF", 1, opacity=".14") + C(x + w - 6, yy + (h - 6) / n / 2 - 1, 1.3, led)
    return b


def tower(x, y, s, col):
    return (L(x, y, x - 8 * s, y + 26 * s, col, 1.6) + L(x, y, x + 8 * s, y + 26 * s, col, 1.6)
            + L(x - 4 * s, y + 13 * s, x + 4 * s, y + 13 * s, col, 1.2) + L(x - 6 * s, y + 20 * s, x + 6 * s, y + 20 * s, col, 1.2)
            + C(x, y, 2.4 * s, col))


def face(cx, cy, r, col, mood):
    mouth = {1: f"M{f(cx-r*.45)} {f(cy+r*.2)} q{f(r*.45)} {f(r*.45)} {f(r*.9)} 0",
             0: f"M{f(cx-r*.4)} {f(cy+r*.35)} h{f(r*.8)}",
             -1: f"M{f(cx-r*.45)} {f(cy+r*.5)} q{f(r*.45)} {f(-r*.45)} {f(r*.9)} 0"}[mood]
    return (C(cx, cy, r, col) + C(cx - r * .35, cy - r * .2, r * .11, INK) + C(cx + r * .35, cy - r * .2, r * .11, INK)
            + P(mouth, stroke=INK, stroke_width=max(1, r * .12), stroke_linecap="round"))


def bubble(x, y, w, h, col, tail="left", **kw):
    t = (f"M{f(x+8)} {f(y+h)} l-6 6 l2 -6z" if tail == "left" else f"M{f(x+w-8)} {f(y+h)} l6 6 l-2 -6z")
    return R(x, y, w, h, col, 7, **kw) + P(t, col)


def bars_text(x, y, widths, col, h=4, gap=7, rx=2):
    return "".join(R(x, y + i * gap, w, h, col, rx) for i, w in enumerate(widths))


def block(x, y, s, col):
    """Isometric cube."""
    top = PG([(x, y), (x + 10 * s, y - 6 * s), (x + 20 * s, y), (x + 10 * s, y + 6 * s)], col, opacity=".55")
    left = PG([(x, y), (x + 10 * s, y + 6 * s), (x + 10 * s, y + 18 * s), (x, y + 12 * s)], col, opacity=".85")
    right = PG([(x + 10 * s, y + 6 * s), (x + 20 * s, y), (x + 20 * s, y + 12 * s), (x + 10 * s, y + 18 * s)], col)
    return top + left + right


def gauge(cx, cy, r, val, cols=("#22C55E", "#FACC15", "#EF4444")):
    b = ""
    for i, c in enumerate(cols):
        a0, a1 = math.pi + i * math.pi / 3, math.pi + (i + 1) * math.pi / 3
        b += P(f"M{f(cx + r*math.cos(a0))} {f(cy + r*math.sin(a0))} A{r} {r} 0 0 1 {f(cx + r*math.cos(a1))} {f(cy + r*math.sin(a1))}",
               stroke=c, stroke_width=r * .28)
    a = math.pi + val * math.pi
    b += L(cx, cy, cx + r * .85 * math.cos(a), cy + r * .85 * math.sin(a), INK, 2, stroke_linecap="round") + C(cx, cy, 3, INK)
    return b


def braille(x, y, cells, col, s=1):
    b = ""
    for k, pat in enumerate(cells):
        for i, on in enumerate(pat):
            cx, cy = x + k * 11 * s + (i // 3) * 4.5 * s, y + (i % 3) * 4.5 * s
            b += C(cx, cy, 1.5 * s, col if on == "1" else "none", stroke=col, stroke_width=.6, opacity="1" if on == "1" else ".35")
    return b


def wave_bars(x, y, n, step, amp, col, seed, w=2.2, op=None):
    r = rnd(seed)
    b = ""
    for i in range(n):
        env = .35 + .65 * abs(math.sin(i / n * math.pi * 2.3))
        a = max(2, amp * env * r.uniform(.4, 1))
        b += R(x + i * step, y - a / 2, w, a, col, w / 2, opacity=op)
    return b


# ------------------------------------------------------------------ one drawing per paper
def data2vizwiz():
    c = "#7C3AED"
    b = bg("#F5F3FF") + browser(10, 10, 220, 130, stroke="#DDD6FE", bar="#EDE9FE")
    for i in range(7):
        b += R(18, 30 + i * 11, 64, 9, "#EDE9FE" if i == 0 else ("#FAF5FF" if i % 2 else "#FFFFFF"), 1)
        b += R(21, 33 + i * 11, 20, 3, c if i == 0 else FAINT, 1) + R(48, 33 + i * 11, 14, 3, FAINT, 1) + R(66, 33 + i * 11, 12, 3, FAINT, 1)
    # cards
    b += R(90, 28, 62, 42, "#FFFFFF", 4, stroke=LINE)
    for k, h in enumerate([16, 26, 20, 30]):
        b += R(98 + k * 12, 64 - h, 8, h, FAINT, 1)
    b += T(121, 36, "default", 6, MUTED, anchor="middle")
    b += R(158, 28, 64, 42, "#FFFFFF", 4, stroke=c, stroke_width=1.6)
    for y1, y2 in [(40, 58), (52, 36), (60, 62)]:
        col = c if abs(y1 - y2) > 8 else FAINT
        b += L(170, y1, 210, y2, col, 1.8) + C(170, y1, 2.4, col) + C(210, y2, 2.4, col)
    b += P("M214 30 l1.6 4 l4 1.6 l-4 1.6 l-1.6 4 l-1.6 -4 l-4 -1.6 l4 -1.6z", c)
    b += R(90, 76, 62, 36, "#FFFFFF", 4, stroke=LINE)
    for k in range(3):
        b += P(f"M96 {104-k*8} q12 -14 24 -2 q12 10 26 -6", stroke=c, stroke_width=1.2, opacity=f"{.35+k*.25:.2f}")
    b += R(158, 76, 64, 36, "#FFFFFF", 4, stroke=LINE)
    for k, (a, z) in enumerate([(18, 46), (24, 40), (14, 34)]):
        y = 86 + k * 9
        b += L(166 + a, y, 166 + z, y, FAINT, 1.5) + C(166 + a, y, 2.4, MUTED) + C(166 + z, y, 2.4, c)
    b += R(90, 118, 132, 14, "#FFFFFF", 7, stroke="#DDD6FE") + T(100, 128, "show the change by region…", 6.6, "#6B7280")
    b += P("M213 120 l1.4 3.5 l3.5 1.4 l-3.5 1.4 l-1.4 3.5 l-1.4 -3.5 l-3.5 -1.4 l3.5 -1.4z", c)
    return b, c, "Interface mock-up: a data table beside recommended charts that go beyond the default bar chart"


def graphwhisper():
    c = "#F59E0B"
    b = bg("#0F172A") + dotgrid("#1E293B", 10, .8)
    pts = [(18, 96), (38, 88), (58, 92), (78, 70), (98, 74), (118, 50), (138, 40)]
    b += L(14, 108, 146, 108, "#334155") + L(14, 30, 14, 108, "#334155")
    b += PL(pts, "#475569", 2) + "".join(C(x, y, 3.2, c) + C(x, y, 6, c, opacity=".18") for x, y in pts)
    b += bubble(154, 20, 76, 22, "#1E293B", "right") + T(160, 34, "What's the trend?", 7, "#E2E8F0")
    b += bubble(150, 52, 80, 34, c, "left") + T(156, 65, "Rising steadily,", 7, "#1F2937", 600) + T(156, 76, "peak at the end.", 7, "#1F2937", 600)
    b += R(156, 104, 10, 14, "#E2E8F0", 2) + P("M166 104 l8 -6 v26 l-8 -6z", "#E2E8F0")
    for k in range(3):
        b += P(f"M{180+k*6} {101-k*3} q{6+k*2} {10+k*3} 0 {20+k*6}", stroke=c, stroke_width=1.6, opacity=f"{1-k*.25:.2f}")
    b += braille(20, 122, ["110100", "100000", "111010", "101110"], "#64748B")
    return b, c, "Dark chart with a spoken question and answer, sound waves and braille, for blind and low-vision users"


def tochi_personal():
    c = "#059669"
    b = bg("#F0FDF4")
    traits = ["O", "C", "E", "A", "N"]
    r = rnd(11)
    b += T(16, 20, "message × personality", 7.5, "#047857", 600)
    for j, t in enumerate(traits):
        b += T(78 + j * 18, 34, t, 8, INK, 700, "middle")
    for i in range(5):
        b += R(16, 40 + i * 17, 50, 12, "#FFFFFF", 3, stroke="#BBF7D0") + R(20, 45 + i * 17, r.uniform(18, 40), 3, MUTED, 1)
        for j in range(5):
            b += R(70 + j * 18, 40 + i * 17, 16, 14, c, 2, opacity=f"{r.uniform(.12, 1):.2f}")
    b += R(170, 20, 60, 50, "#FFFFFF", 8, stroke="#BBF7D0") + T(200, 44, "2,040", 14, c, 800, "middle") + T(200, 58, "participants", 7, "#64748B", anchor="middle")
    b += R(170, 78, 60, 50, c, 8) + T(200, 102, "−99%", 14, "#FFFFFF", 800, "middle") + T(200, 116, "survey cost", 7, "#D1FAE5", anchor="middle")
    return b, c, "Heatmap of messages by Big Five traits with highlights: 2,040 participants and 99% lower survey cost"


def visnoob():
    c = "#0D9488"
    b = bg("#F0FDFA")
    # 3D pie (misleading)
    b += E(46, 70, 32, 14, "#B91C1C") + R(14, 62, 64, 8, "#B91C1C") + E(46, 62, 32, 14, "#F87171")
    b += P("M46 62 L46 48 A32 14 0 0 1 76 58 z", "#FCA5A5") + P("M46 62 L76 58 A32 14 0 0 1 30 74 z", "#FECACA")
    b += C(70, 34, 9, "#FEF3C7", stroke="#D97706") + T(70, 38, "?", 11, "#B45309", 800, "middle")
    b += T(46, 98, "misleading", 7.5, "#B91C1C", 600, "middle")
    # stepper
    for k, lab in enumerate(["spot", "learn", "fix"]):
        y = 34 + k * 30
        b += C(110, y, 9, c if k < 2 else "#FFFFFF", stroke=c, stroke_width=1.6)
        b += T(110, y + 3.5, str(k + 1), 9, "#FFFFFF" if k < 2 else c, 700, "middle") + T(123, y + 3, lab, 7.5, INK, 600)
        if k < 2:
            b += L(110, y + 9, 110, y + 21, c, 1.6)
    # clean bars
    b += R(150, 24, 80, 96, "#FFFFFF", 6, stroke="#99F6E4")
    for k, h in enumerate([58, 34, 20, 10]):
        b += R(160 + k * 17, 106 - h, 12, h, c, 2, opacity=f"{1-k*.18:.2f}")
    b += L(156, 106, 224, 106, MUTED)
    b += C(222, 28, 8, "#22C55E") + P("M218 28 l3 3 l5 -6", stroke="#FFFFFF", stroke_width=1.8)
    b += T(190, 134, "understandable", 7.5, c, 600, "middle")
    return b, c, "A misleading 3D pie chart, a three-step guided tutorial, and the corrected bar chart"


def latent_dag():
    c = "#A78BFA"
    b = bg("#1E1B4B") + dotgrid("#312E81", 12, .9)
    b += rad("u", [(0, "#C4B5FD", .7), (1, "#1E1B4B", 0)])
    nodes = {"X": (40, 104), "M": (120, 118), "Y": (200, 104), "U": (120, 46)}
    for a, z, dash in [("X", "M", None), ("M", "Y", None), ("X", "Y", None), ("U", "X", "4 3"), ("U", "Y", "4 3")]:
        (x1, y1), (x2, y2) = nodes[a], nodes[z]
        d = math.hypot(x2 - x1, y2 - y1)
        ux, uy = (x2 - x1) / d, (y2 - y1) / d
        col = c if dash else "#A5B4FC"
        b += arrow(x1 + ux * 15, y1 + uy * 15, x2 - ux * 15, y2 - uy * 15, col, 1.6, 6) if not dash else \
            L(x1 + ux * 30 * 0 + ux * 15, y1 + uy * 15, x2 - ux * 17, y2 - uy * 17, col, 1.6, stroke_dasharray=dash) + \
            arrow(x2 - ux * 22, y2 - uy * 22, x2 - ux * 15, y2 - uy * 15, col, 1.6, 6)
    b += C(120, 46, 36, "url(#u)")
    for k, (x, y) in nodes.items():
        if k == "U":
            b += C(x, y, 14, "#1E1B4B", stroke=c, stroke_width=1.8, stroke_dasharray="3 2") + T(x, y + 4, "U", 11, c, 700, "middle")
        else:
            b += C(x, y, 13, "#6366F1") + T(x, y + 4, k, 11, "#FFFFFF", 700, "middle")
    b += T(140, 26, "unobserved?", 8, "#C4B5FD", 600) + T(14, 20, "causal DAG", 8, "#818CF8", 600, fam=MONO)
    return b, c, "A causal graph on a dark blueprint grid with a glowing, dashed latent variable"


def catches_eye():
    c = "#DB2777"
    b = bg("#FDF2F8")
    # card A
    b += R(14, 30, 92, 82, "#FFFFFF", 6, stroke="#FBCFE8") + T(22, 44, "A", 9, c, 800)
    b += T(60, 70, "72%", 20, c, 800, "middle") + R(26, 80, 68, 4, FAINT, 2) + R(26, 88, 50, 4, FAINT, 2)
    for k in range(5):
        b += person(32 + k * 14, 106, .55, c if k < 4 else FAINT)
    # card B
    b += R(134, 30, 92, 82, "#FFFFFF", 6, stroke="#FBCFE8") + T(142, 44, "B", 9, "#6B7280", 800)
    for k, h in enumerate([20, 34, 26, 44]):
        b += R(148 + k * 18, 100 - h, 12, h, MUTED, 2)
    b += L(144, 100, 218, 100, FAINT)
    # eye between
    b += P("M104 18 q16 -14 32 0 q-16 14 -32 0z", "#FFFFFF", stroke=INK, stroke_width=1.3) + C(120, 18, 5, c) + C(120, 18, 2, INK)
    b += T(120, 76, "vs", 9, "#9D174D", 700, "middle")
    # preference bar
    b += R(14, 122, 212, 12, "#FCE7F3", 6) + R(14, 122, 136, 12, c, 6) + T(20, 131, "preferred 64%", 7, "#FFFFFF", 700)
    return b, c, "Two infographic designs compared side by side, with an eye and a preference bar"


def making_charts_speak():
    c = "#D97706"
    b = bg("#FEF3C7")
    b += phone(132, 8, 74, 134, INK, "#FFFBEB")
    for k, h in enumerate([18, 30, 24, 38]):
        b += R(142 + k * 14, 58 - h, 10, h, c, 1.5, opacity=f"{.55+k*.15:.2f}")
    b += L(139, 58, 199, 58, MUTED)
    b += bubble(144, 66, 56, 16, "#FFFFFF", "right", stroke="#FCD34D") + T(148, 77, "Which is highest?", 5.8, INK)
    b += bubble(138, 90, 60, 26, c, "left") + T(143, 101, "The 4th bar —", 6, "#FFFFFF", 700) + T(143, 110, "about 2× the 1st.", 6, "#FFFFFF")
    b += R(140, 122, 58, 10, "#FFFFFF", 5, stroke="#FCD34D") + C(192, 127, 3, c)
    # speaker + braille
    b += R(22, 44, 14, 20, INK, 2) + P("M36 44 l16 -12 v44 l-16 -12z", INK)
    for k in range(3):
        b += P(f"M{60+k*9} {38-k*4} q{10+k*3} {16+k*4} 0 {32+k*8}", stroke=c, stroke_width=2, opacity=f"{1-k*.25:.2f}")
    b += braille(18, 104, ["110000", "101000", "100100", "110110", "100010"], INK, 1.15)
    b += T(18, 136, "chart, spoken", 8, "#92400E", 700)
    return b, c, "A phone with a chart and a conversational Q&A, plus a speaker and braille cells"


def persona_palette():
    c = "#E11D48"
    pal = ["#E11D48", "#2563EB", "#059669", "#D97706", "#7C3AED"]
    b = lin("pp", [(0, "#FFF1F2"), (1, "#EEF2FF")], 1, 1) + bg("url(#pp)")
    rows = [(14, 14, 134, "left", 0), (60, 52, 134, "right", 1), (14, 90, 120, "left", 2)]
    for x, y, w, tail, k in rows:
        b += bubble(x, y, w, 28, "#FFFFFF", tail, stroke="#E5E7EB")
        r, xx = rnd(k + 3), x + 9
        while xx < x + w - 16:
            ww = r.uniform(12, 24)
            hi = r.random() < .4
            b += R(xx, y + 11, ww, 7, pal[(k * 2 + int(xx / 9)) % 5] if hi else "#E5E7EB", 2, opacity=".9" if hi else None)
            xx += ww + 4
    # paint palette
    b += P("M176 98 c-22 -4 -30 -30 -16 -52 c14 -22 54 -24 66 0 c8 16 -6 22 -16 20 c-10 -2 -14 10 -6 18 c8 10 -12 18 -28 14z", "#FFFFFF", stroke="#D6D3D1", stroke_width=1.2)
    for (x, y), col in zip([(176, 52), (196, 44), (214, 52), (168, 72), (186, 88)], pal):
        b += C(x, y, 6, col)
    b += T(200, 134, "Big Five → color", 7.5, "#9F1239", 600, "middle")
    return b, c, "Chat bubbles with words highlighted in persona colors next to a painter's palette"


def charts_of_thought():
    c = "#059669"
    b = bg("#FFFFFF") + R(0, 0, W, 3, c)
    # mini chart
    b += R(12, 18, 54, 48, "#F8FAFC", 4, stroke=LINE)
    for k, h in enumerate([16, 30, 12, 24]):
        b += R(18 + k * 12, 58 - h, 8, h, MUTED, 1)
    b += arrow(70, 42, 84, 42, c, 1.6)
    steps = ["1 extract", "2 sort", "3 verify", "4 reason"]
    for k, s in enumerate(steps):
        b += R(88, 14 + k * 14, 58, 11, "#ECFDF5" if k < 3 else c, 3, stroke="#A7F3D0") + T(93, 22 + k * 14, s, 6.6, "#065F46" if k < 3 else "#FFFFFF", 600, fam=MONO)
    b += arrow(150, 42, 162, 42, c, 1.6)
    b += T(198, 46, "50.2", 22, c, 800, "middle") + T(198, 58, "VLAT score", 6.8, "#64748B", anchor="middle")
    # comparison bars
    b += L(16, 82, 226, 82, LINE)
    b += T(16, 98, "human", 7, "#64748B") + R(64, 91, 160 * 28.82 / 55, 9, FAINT, 2) + T(64 + 160 * 28.82 / 55 + 4, 99, "28.8", 7, INK, 600, fam=MONO)
    b += T(16, 116, "LLM + CoT", 7, "#065F46", 700) + R(64, 109, 160 * 50.17 / 55, 9, c, 2) + T(64 + 160 * 50.17 / 55 - 4, 117, "50.2", 7, "#FFFFFF", 700, "end", fam=MONO)
    b += T(16, 138, "chart → table → reasoning", 7.5, INK, 600, fam=MONO)
    return b, c, "Pipeline from chart to structured table to reasoning, with VLAT score 50.2 against a 28.8 human baseline"


def misvisfix():
    c = "#8B5CF6"
    b = bg("#0B1120")
    b += R(8, 8, 224, 134, "#111827", 8, stroke="#1F2937")
    b += R(16, 18, 110, 84, "#0F172A", 5, stroke="#1F2937")
    for k, h in enumerate([22, 60, 40, 52]):
        b += R(28 + k * 24, 92 - h, 16, h, "#60A5FA", 1.5, opacity=".85")
    b += L(22, 92, 122, 92, "#475569")
    b += R(18, 76, 30, 22, "none", 3, stroke="#F87171", stroke_width=1.6, stroke_dasharray="3 2")
    b += T(22, 72, "y-axis starts at 40", 6, "#FCA5A5", 600)
    rows = [("#EF4444", "truncated axis"), ("#F59E0B", "missing label"), ("#22C55E", "colors ok")]
    for k, (col, s) in enumerate(rows):
        y = 22 + k * 22
        b += R(134, y, 90, 17, "#1F2937", 4) + C(143, y + 8.5, 3.4, col) + T(151, y + 11.5, s, 6.6, "#E5E7EB")
    b += R(134, 90, 90, 16, c, 5) + T(179, 101, "Fix automatically", 6.8, "#FFFFFF", 700, "middle")
    b += R(16, 110, 208, 24, "#0F172A", 5, stroke="#1F2937")
    for k, w in enumerate([120, 168, 96]):
        b += R(22, 114 + k * 6.5, w, 3.5, "#334155", 1.5)
    b += P("M202 116 l2 5 l5 2 l-5 2 l-2 5 l-2 -5 l-5 -2 l5 -2z", c)
    return b, c, "Dark dashboard flagging a truncated axis, listing issues and offering an automatic fix"


def chi25_messaging():
    c = "#16A34A"
    b = bg("#F7FEE7")
    # megaphone
    b += PG([(20, 64), (60, 44), (60, 100), (20, 82)], c) + R(12, 64, 10, 18, "#15803D", 2) + R(24, 82, 8, 16, "#15803D", 2)
    for k in range(3):
        b += P(f"M{68+k*6} {56-k*6} q{8+k*2} {16+k*6} 0 {32+k*12}", stroke=c, stroke_width=1.6, opacity=f"{.9-k*.25:.2f}")
    cols = ["#16A34A", "#0EA5E9", "#F59E0B"]
    for k, col in enumerate(cols):
        y = 18 + k * 40
        b += R(100, y, 90, 30, "#FFFFFF", 5, stroke=col, stroke_width=1.4) + R(100, y, 5, 30, col, 2)
        b += bars_text(110, y + 7, [70, 54, 40][k:] + [60, 48][:k], FAINT, 3.5, 7)
        b += person(212, y + 21, .9, col)
    b += T(14, 134, "one message, many readers", 7.5, "#3F6212", 700)
    return b, c, "A megaphone sending differently tailored public messages to three different people"


def bn_sentiment_2023():
    c = "#2563EB"
    b = bg("#EFF6FF")
    rows = [("দারুণ লাগলো!", 1, "#22C55E"), ("ঠিক আছে", 0, "#94A3B8"), ("একদম বাজে", -1, "#EF4444")]
    for k, (s, m, col) in enumerate(rows):
        y = 16 + k * 40
        b += R(12, y, 130, 32, "#FFFFFF", 6, stroke="#BFDBFE") + face(30, y + 16, 10, col, m)
        b += T(46, y + 20, s, 11, INK, 600, fam=BN)
    segs = [(.46, "#22C55E"), (.18, "#FACC15"), (.14, "#94A3B8"), (.22, "#EF4444")]
    a0, cx, cy, r = -math.pi / 2, 190, 66, 32
    for frac, col in segs:
        a1 = a0 + frac * 2 * math.pi
        large = 1 if frac > .5 else 0
        b += P(f"M{f(cx + r*math.cos(a0))} {f(cy + r*math.sin(a0))} A{r} {r} 0 {large} 1 {f(cx + r*math.cos(a1))} {f(cy + r*math.sin(a1))}",
               stroke=col, stroke_width=14)
        a0 = a1
    b += T(190, 70, "multi", 8, c, 700, "middle") + T(190, 122, "comment classes", 7.5, "#1E40AF", 600, "middle")
    return b, c, "Bengali social-media comments with positive, neutral and negative faces next to a class donut chart"


def cvd():
    c = "#EF4444"
    b = bg("#1E1E2E")
    b += R(0, 0, W, 14, "#181825") + T(10, 10, "Account.java", 7, "#A6ADC8", fam=MONO) + R(84, 0, 1, 14, "#313244")
    toks = [("#CBA6F7", 26), ("#89B4FA", 40), ("#CDD6F4", 30)]
    r = rnd(5)
    for i in range(9):
        y = 22 + i * 13
        if i == 5:
            b += R(0, y - 3, W, 12, c, 0, opacity=".22") + R(0, y - 3, 3, 12, c)
        b += T(14, y + 6, str(i + 1), 7, "#6C7086", anchor="end", fam=MONO)
        x = 22 + (8 if 1 <= i <= 7 else 0) + (8 if 3 <= i <= 6 else 0)
        for k in range(r.randint(2, 4)):
            col, w = toks[(i + k) % 3]
            ww = w * r.uniform(.5, 1.1)
            b += R(x, y, ww, 5, col if i != 5 else "#F38BA8", 2, opacity=".85")
            x += ww + 5
    # bug
    b += E(208, 78, 9, 11, c) + C(208, 64, 5, c) + L(199, 72, 192, 68, c, 1.6) + L(217, 72, 224, 68, c, 1.6)
    b += L(199, 84, 192, 88, c, 1.6) + L(217, 84, 224, 88, c, 1.6) + L(208, 68, 208, 89, "#1E1E2E", 1.2)
    b += R(170, 124, 62, 16, "#313244", 4) + T(201, 135, "vulnerable", 7, "#F38BA8", 700, "middle", fam=MONO)
    return b, c, "Code editor with one line highlighted red and a bug icon marking a detected vulnerability"


def hello_autism():
    c = "#0EA5E9"
    b = bg("#E0F2FE") + "".join(C(x, y, rr, "#BAE6FD") for x, y, rr in [(24, 30, 16), (220, 120, 22), (210, 24, 8)])
    b += phone(84, 6, 72, 138, "#0F172A", "#FFFFFF")
    cards = [(91, 18), (122, 18), (91, 52), (122, 52)]
    for (x, y), bgc in zip(cards, ["#FEE2E2", "#DBEAFE", "#DCFCE7", "#FEF9C3"]):
        b += R(x, y, 27, 30, bgc, 4)
    b += C(104.5, 34, 7, "#EF4444") + P("M104 27 q3 -4 6 -3", stroke="#16A34A", stroke_width=1.6)
    b += P("M128 28 h14 l-2 14 h-10z", "#3B82F6") + P("M142 31 q5 0 4 5 q-1 3 -5 3", stroke="#3B82F6", stroke_width=1.4)
    b += PG([(104.5, 58), (95, 66), (114, 66)], "#16A34A") + R(97, 66, 15, 11, "#22C55E")
    b += C(135.5, 67, 6, "#F59E0B") + "".join(L(135.5 + 9 * math.cos(a), 67 + 9 * math.sin(a), 135.5 + 12 * math.cos(a), 67 + 12 * math.sin(a), "#F59E0B", 1.4) for a in [i * math.pi / 4 for i in range(8)])
    b += R(91, 90, 58, 18, c, 5) + T(120, 102, "I want apple", 7, "#FFFFFF", 700, "middle")
    b += bubble(164, 22, 60, 24, "#FFFFFF", "left", stroke="#7DD3FC") + T(194, 38, "Hello!", 10, c, 800, "middle")
    b += person(196, 104, 1.3, "#0369A1")
    return b, c, "Phone app with picture cards (apple, cup, home, sun) and a Hello speech bubble"


def bn_char_digit():
    c = "#1D4ED8"
    b = bg("#FFFDF5")
    b += "".join(L(x, 0, x, H, "#E0E7FF", .6) for x in range(0, W, 10)) + "".join(L(0, y, W, y, "#E0E7FF", .6) for y in range(0, H, 10))
    tf = ["", "rotate(-14 {x} 60)", "scale(.8) translate({x8} 15)", "skewX(-12)", "rotate(12 {x} 60)"]
    for k in range(5):
        x = 30 + k * 45
        t = tf[k].format(x=x, x8=f(x * .25))
        b += T(x, 76, "ক", 38, c if k == 0 else "#3B82F6", 700, "middle", fam=BN, transform=t or None, opacity="1" if k == 0 else f"{.85-k*.1:.2f}")
    b += L(54, 24, 54, 92, "#93C5FD", 1, stroke_dasharray="3 3") + T(140, 22, "augmented", 7.5, "#1E40AF", 600, "middle", fam=MONO)
    b += T(120, 128, "০ ১ ২ ৩ ৪ ৫ ৬ ৭ ৮ ৯", 15, INK, 600, "middle", fam=BN)
    return b, c, "Bengali letter rotated, scaled and skewed for data augmentation, above the ten Bengali digits"


def word2vec():
    c = "#0D9488"
    b = bg("#F0FDFA") + L(20, 128, 228, 128, "#99F6E4") + L(20, 12, 20, 128, "#99F6E4")
    r = rnd(21)
    clusters = [((70, 46), "#10B981", "ভালো"), ((176, 44), "#F59E0B", "সুন্দর"), ((120, 100), "#EF4444", "খারাপ")]
    for (cx, cy), col, w in clusters:
        for _ in range(12):
            b += C(cx + r.gauss(0, 13), cy + r.gauss(0, 8), 2.4, col, opacity=".7")
        b += C(cx, cy, 3.6, col) + T(cx + 6, cy - 6, w, 11, INK, 700, fam=BN)
    b += arrow(20, 128, 68, 48, "#0F766E", 1.4) + arrow(20, 128, 116, 100, "#0F766E", 1.4)
    b += T(226, 142, "word2vec", 7.5, "#0F766E", 600, "end", fam=MONO)
    return b, c, "Word-embedding scatter plot with clusters of Bengali sentiment words and vectors from the origin"


def telemedicine():
    c = "#0891B2"
    b = bg("#ECFEFF") + P("M0 118 q60 -12 120 0 t120 0 v32 h-240z", "#CFFAFE")
    # laptop with doctor
    b += R(18, 24, 86, 58, INK, 5) + R(22, 28, 78, 50, "#FFFFFF", 2) + P("M10 82 h102 l-6 8 h-90z", "#475569")
    b += C(61, 44, 8, "#FCD34D") + P("M45 78 q0 -20 16 -20 q16 0 16 20z", "#F8FAFC", stroke=FAINT)
    b += P("M55 60 q-4 10 2 14 q6 2 8 -4", stroke=c, stroke_width=1.6) + C(65, 70, 2.2, c)
    b += R(66, 31, 18, 10, "#E0F2FE", 2) + P("M72 33 v6 M69 36 h6", stroke="#EF4444", stroke_width=1.6)
    # signal
    b += L(112, 60, 158, 60, c, 1.4, stroke_dasharray="3 3") + C(135, 50, 2.4, c)
    for k in range(3):
        rr = 6 + k * 6
        b += P(f"M{f(135 - rr*.7)} {f(50 - rr*.7)} A{rr} {rr} 0 0 1 {f(135 + rr*.7)} {f(50 - rr*.7)}", stroke=c, stroke_width=1.8, opacity=f"{1-k*.25:.2f}", stroke_linecap="round")
    # village house
    b += PG([(160, 74), (192, 46), (224, 74)], "#B45309") + R(166, 74, 52, 34, "#FDE68A") + R(186, 86, 12, 22, "#92400E")
    b += person(210, 122, .8, "#0E7490")
    return b, c, "A doctor on a laptop video call linked to a rural home"


def ride_driver_cnn():
    c = "#F97316"
    b = bg("#FFF7ED")
    b += C(96, 66, 30, "#FDBA74") + P("M66 60 q0 -34 30 -34 q30 0 30 34 q-6 -18 -30 -16 q-24 -2 -30 16z", "#7C2D12")
    b += C(85, 66, 2.6, INK) + C(107, 66, 2.6, INK) + P("M88 82 q8 6 16 0", stroke=INK, stroke_width=1.6)
    b += P("M50 118 q0 -24 46 -24 q46 0 46 24z", "#1E3A8A")
    for x, y, dx, dy in [(58, 24, 1, 1), (134, 24, -1, 1), (58, 108, 1, -1), (134, 108, -1, -1)]:
        b += P(f"M{x} {y + dy*12} v{-dy*12} h{dx*12}", stroke=c, stroke_width=2.4)
    for x, y in [(85, 66), (107, 66), (96, 74), (88, 82), (104, 82), (76, 56), (116, 56)]:
        b += C(x, y, 1.6, "#22C55E")
    b += R(150, 30, 80, 46, "#FFFFFF", 6, stroke="#FED7AA") + T(158, 46, "driver ID", 7, "#9A3412", 600)
    b += C(162, 62, 6, "#22C55E") + P("M159 62 l2 2 l4 -4", stroke="#FFFFFF", stroke_width=1.5) + T(172, 65, "match", 8, INK, 700)
    b += car(152, 100, 1.75, c)
    return b, c, "A driver's face in a camera frame with landmark points, a verified match card and a car"


def bn_word_hw():
    c = "#1D4ED8"
    b = bg("#FEFCE8") + "".join(L(0, y, W, y, "#BFDBFE", .8) for y in range(22, H, 16)) + L(26, 0, 26, H, "#FCA5A5", 1.2)
    b += T(130, 76, "বাংলাদেশ", 34, "#1E3A8A", 400, "middle", fam=BN, font_style="italic", transform="rotate(-3 130 70)")
    for x, w in [(48, 36), (86, 34), (122, 44), (168, 40)]:
        b += R(x, 42, w, 44, "none", 3, stroke="#F97316", stroke_width=1.2, stroke_dasharray="3 2")
    b += arrow(60, 110, 92, 110, "#1E40AF", 1.4)
    b += R(98, 100, 108, 20, "#FFFFFF", 4, stroke="#93C5FD") + T(152, 115, "বাংলাদেশ ✓", 11, "#15803D", 700, "middle", fam=BN)
    return b, c, "A handwritten Bengali word on ruled notebook paper, segmented into boxes and recognised"


def children_internet():
    c = "#7C3AED"
    b = bg("#FAF5FF")
    cx, cy, r = 60, 72, 46
    b += C(cx, cy, r, "#FFFFFF", stroke="#DDD6FE", stroke_width=2)
    for a0, a1, col in [(-90, 30, "#7C3AED"), (30, 110, "#C4B5FD"), (180, 240, "#A78BFA")]:
        A0, A1 = math.radians(a0), math.radians(a1)
        b += P(f"M{cx} {cy} L{f(cx + 40*math.cos(A0))} {f(cy + 40*math.sin(A0))} A40 40 0 {1 if a1-a0>180 else 0} 1 {f(cx + 40*math.cos(A1))} {f(cy + 40*math.sin(A1))}z", col, opacity=".85")
    for k in range(12):
        a = k * math.pi / 6
        b += L(cx + 42 * math.cos(a), cy + 42 * math.sin(a), cx + 46 * math.cos(a), cy + 46 * math.sin(a), "#6D28D9", 1.4)
    b += C(cx, cy, 14, "#FFFFFF") + L(cx, cy, cx, cy - 26, INK, 2) + L(cx, cy, cx + 16, cy + 6, INK, 2) + C(cx, cy, 2.4, INK)
    ages = [("6–9", 30), ("10–13", 52), ("14–17", 76)]
    for k, (lab, v) in enumerate(ages):
        y = 36 + k * 30
        b += T(124, y + 8, lab, 7.5, "#5B21B6", 600) + R(152, y, v, 12, c, 3, opacity=f"{.5+k*.25:.2f}")
    b += T(124, 22, "daily screen time", 7.5, INK, 700)
    b += R(196, 112, 30, 22, INK, 3) + R(199, 115, 24, 16, "#C4B5FD", 1)
    return b, c, "Clock with screen-time wedges and bars of internet use by children's age group"


def retinal():
    c = "#EA580C"
    b = bg("#09090B") + rad("fundus", [(0, "#FDBA74", 1), (.55, "#EA580C", 1), (.9, "#7C2D12", 1), (1, "#09090B", 1)])
    b += C(96, 75, 66, "url(#fundus)")
    b += rad("disc", [(0, "#FEF9C3", 1), (1, "#FDE047", 0)]) + C(132, 70, 16, "url(#disc)")
    r = rnd(3)
    for k in range(9):
        a = k * 2 * math.pi / 9 + r.uniform(-.2, .2)
        x1, y1 = 132 + 60 * math.cos(a), 70 + 46 * math.sin(a)
        mx, my = 132 + 30 * math.cos(a + .35), 70 + 24 * math.sin(a + .35)
        b += P(f"M132 70 Q{f(mx)} {f(my)} {f(x1)} {f(y1)}", stroke="#7F1D1D", stroke_width=f"{2.4 - (k%3)*.6:.1f}", opacity=".85")
    b += "".join(C(70 + r.uniform(-16, 16), 80 + r.uniform(-14, 14), r.uniform(1.4, 2.6), "#FEF08A") for _ in range(8))
    b += C(92, 78, 5, "#7F1D1D", opacity=".55")
    for k, (lab, v) in enumerate([("DR", .78), ("glaucoma", .14), ("normal", .08)]):
        y = 36 + k * 26
        b += T(172, y, lab, 7.5, "#FED7AA", 600) + R(172, y + 4, 56, 7, "#27272A", 3) + R(172, y + 4, 56 * v, 7, c, 3)
    return b, c, "A retina fundus image with vessels and lesions, beside predicted disease probabilities"


def bn_digit_tl():
    c = "#16A34A"
    b = bg("#F8FAFC")
    for k, d in enumerate("০১২৩৪৫৬৭৮৯"):
        b += R(10 + k * 22, 10, 20, 26, "#FFFFFF", 3, stroke=LINE) + T(20 + k * 22, 30, d, 15, INK, 600, "middle", fam=BN)
    b += L(28, 132, 228, 132, MUTED) + L(28, 48, 28, 132, MUTED)
    for y in (66, 88, 110):
        b += L(28, y, 228, y, "#EEF2F7")
    cnn = [(28 + i * 20, 132 - 80 * (1 - math.exp(-i / 3.2)) + (3 if i % 2 else 0)) for i in range(11)]
    tl = [(28 + i * 20, 132 - 80 * (1 - math.exp(-i / 1.4))) for i in range(11)]
    b += PL(cnn, MUTED, 2) + PL(tl, c, 2.4)
    b += T(222, 60, "transfer", 7.5, c, 700, "end") + T(222, 100, "CNN", 7.5, "#64748B", 700, "end")
    b += T(32, 144, "epochs →", 6.5, MUTED, fam=MONO) + T(32, 58, "acc", 6.5, MUTED, fam=MONO)
    return b, c, "The ten Bengali digits above learning curves where transfer learning converges faster than a plain CNN"


def fb_celebrity():
    c = "#3B82F6"
    b = bg("#F1F5F9")
    b += R(12, 10, 140, 130, "#FFFFFF", 6, stroke=LINE)
    b += C(28, 26, 9, "#FDE68A") + P("M28 19 l2 5 h5 l-4 3 l1.6 5 l-4.6 -3 l-4.6 3 l1.6 -5 l-4 -3 h5z", "#F59E0B")
    b += R(42, 20, 54, 5, INK, 2) + R(42, 29, 30, 4, FAINT, 2)
    b += lin("img", [(0, "#C7D2FE"), (1, "#FBCFE8")], 1, 1) + R(18, 42, 128, 52, "url(#img)", 3)
    b += C(82, 64, 14, "#FFFFFF", opacity=".6") + PG([(78, 57), (78, 71), (90, 64)], "#6366F1")
    for k, w in enumerate([110, 84, 98]):
        b += R(18, 102 + k * 11, 26, 7, "#E2E8F0", 3) + R(48, 103 + k * 11, w * .8, 5, "#F1F5F9", 2)
    reacts = [("#EF4444", 70, "love"), ("#3B82F6", 52, "like"), ("#F59E0B", 30, "haha"), ("#7C3AED", 16, "sad"), ("#DC2626", 10, "angry")]
    b += T(164, 22, "fan emotions", 7.5, INK, 700)
    for k, (col, v, lab) in enumerate(reacts):
        y = 32 + k * 21
        b += C(170, y + 6, 6, col) + R(180, y + 2, v * .78, 9, col, 3, opacity=".75") + T(180, y + 19, lab, 5.8, "#64748B")
    return b, c, "A celebrity's social-media post with comments, beside a bar chart of fan emotion reactions"


def articulation():
    c = "#BE185D"
    b = bg("#FFF1F2")
    b += P("M34 134 V108 C14 96 12 58 30 38 C48 18 84 20 94 44 L98 58 L106 70 L98 72 L100 80 Q99 84 95 84 L97 90 Q95 98 84 97 L78 104 V134 Z", "#FBCFE8", stroke="#9D174D", stroke_width=1.4, stroke_linejoin="round")
    b += P("M90 84 q-5 2 -9 0", stroke="#9D174D", stroke_width=1.6, stroke_linecap="round") + C(84, 54, 2.2, "#9D174D")
    for k in range(3):
        b += P(f"M{106+k*0} {f(76-k*6)} q{6+k*3} {k*6+6} 0 {k*12+12}", stroke=c, stroke_width=1.4, opacity=f"{.9-k*.25:.2f}", transform=f"translate({k*5},0)")
    r = rnd(8)
    for i in range(18):
        for j in range(8):
            v = abs(math.sin(i * .5 + j * .3)) * r.uniform(.3, 1) * (1 - j / 10)
            b += R(112 + i * 6.6, 18 + j * 7, 6.2, 6.4, c, 0, opacity=f"{v:.2f}")
    b += T(112, 14, "spectrogram", 6.5, "#9D174D", 600, fam=MONO)
    for k, (ph, bad) in enumerate([("/k/", False), ("/a/", False), ("/l/", True), ("/a/", False)]):
        x = 112 + k * 30
        b += R(x, 86, 26, 18, "#FFFFFF" if not bad else "#FDE68A", 4, stroke=c if not bad else "#D97706", stroke_width=1.2)
        b += T(x + 13, 99, ph, 8, INK, 700, "middle", fam=MONO)
    b += T(112, 122, "RNN + language model", 7.5, "#9D174D", 600) + T(195, 136, "flagged /l/", 7, "#B45309", 700, "middle")
    return b, c, "A head profile speaking, with a spectrogram and a phoneme sequence where one sound is flagged"


def hate_speech():
    c = "#DC2626"
    b = bg("#FEF2F2")
    words = [("তুমি", .15), ("একটা", .1), ("জঘন্য", .95), ("লোক", .45)]
    x = 14
    for w, a in words:
        ww = 34 if len(w) < 4 else 40
        b += R(x, 34, ww, 24, "#FFFFFF", 5, stroke="#FECACA") + T(x + ww / 2, 51, w, 10, INK, 600, "middle", fam=BN)
        b += R(x, 64, ww, 8, c, 2, opacity=f"{a:.2f}") + T(x + ww / 2, 82, f"{a:.2f}", 6.5, "#991B1B", 600, "middle", fam=MONO)
        x += ww + 4
    b += T(14, 22, "attention weights", 7.5, "#991B1B", 700)
    b += P("M206 30 l20 8 v18 c0 16 -9 25 -20 30 c-11 -5 -20 -14 -20 -30 v-18z", c)
    b += L(199, 50, 213, 64, "#FFFFFF", 2.6, stroke_linecap="round") + L(213, 50, 199, 64, "#FFFFFF", 2.6, stroke_linecap="round")
    b += R(14, 104, 212, 28, "#FFFFFF", 6, stroke="#FECACA") + C(28, 118, 6, c) + T(40, 122, "hate speech · blocked", 8, "#991B1B", 700)
    return b, c, "Bengali words with attention-weight bars under each, a shield, and a blocked verdict"


def depression():
    c = "#818CF8"
    b = lin("dep", [(0, "#1E293B"), (1, "#334155")]) + bg("url(#dep)")
    b += cloud(20, 34, 1.15, "#64748B") + "".join(L(x, 52 + (x % 3) * 4, x - 3, 62 + (x % 3) * 4, "#93C5FD", 1.4, stroke_linecap="round") for x in range(34, 72, 7))
    b += R(96, 14, 130, 56, "#0F172A", 6, stroke="#475569") + C(110, 28, 6, "#475569") + R(120, 25, 40, 5, "#64748B", 2)
    b += T(104, 50, "আজ কিছুই ভালো লাগছে না", 8.8, "#E2E8F0", 500, fam=BN)
    b += R(104, 58, 70, 4, "#334155", 2)
    pts = [(16 + i * 20.8, 92 + i * 3.4 + (6 if i % 3 == 1 else 0) - (4 if i % 4 == 0 else 0)) for i in range(11)]
    b += PL(pts, c, 2.2) + "".join(C(x, y, 2.2, c) for x, y in pts)
    b += L(14, 136, 226, 136, "#475569") + T(16, 146, "mood over time", 6.5, "#94A3B8", fam=MONO)
    b += R(176, 112, 50, 16, c, 4) + T(201, 123, "LSTM+CNN", 6.5, "#0F172A", 700, "middle", fam=MONO)
    return b, c, "Rain cloud, a sad Bengali status update, and a declining mood line"


def plant_diversified():
    c = "#65A30D"
    b = bg("#F7FEE7")
    b += leaf(64, 74, 1.9, -24, "#4D7C0F", "#D9F99D")
    r = rnd(4)
    for _ in range(9):
        b += C(54 + r.uniform(-20, 26), 74 + r.uniform(-30, 30), r.uniform(2.5, 5.5), "#92400E", opacity=".85")
    b += L(64, 132, 64, 146, "#4D7C0F", 2)
    models = [("M1", .71), ("M2", .82), ("M3", .88), ("M4", .94)]
    b += T(136, 22, "modified networks", 7.5, "#3F6212", 700)
    for k, (lab, v) in enumerate(models):
        x = 140 + k * 22
        h = 90 * v
        b += R(x, 124 - h, 15, h, c, 2, opacity=f"{.45+k*.18:.2f}") + T(x + 7.5, 136, lab, 7, "#3F6212", 600, "middle", fam=MONO)
    b += L(134, 124, 230, 124, "#84CC16")
    return b, c, "A diseased leaf with brown spots next to a comparison of four modified network variants"


def fish_market():
    c = "#0284C7"
    b = lin("sea", [(0, "#E0F2FE"), (.55, "#E0F2FE"), (.56, "#38BDF8"), (1, "#0369A1")]) + bg("url(#sea)")
    b += P("M0 84 q15 -6 30 0 t30 0 t30 0 t30 0 t30 0 t30 0 t30 0 t30 0", stroke="#FFFFFF", stroke_width=1.4, opacity=".7")
    b += P("M24 112 q14 -12 30 0 q-16 12 -30 0z", "#FCD34D") + PG([(54, 112), (64, 104), (64, 120)], "#FCD34D") + C(31, 110, 1.6, INK)
    b += P("M40 74 h44 l-8 12 h-30z", "#7C2D12") + L(62, 74, 62, 46, "#44403C", 1.6) + PG([(63, 48), (80, 70), (63, 70)], "#FFFFFF")
    b += arrow(90, 66, 112, 52, "#0C4A6E", 1.6)
    # market stall
    b += R(116, 40, 56, 34, "#FFFFFF") + "".join(R(116 + k * 8, 30, 8, 12, "#EF4444" if k % 2 == 0 else "#FFFFFF") for k in range(7))
    b += R(122, 54, 44, 6, "#FCD34D") + T(144, 70, "market", 6.5, INK, 600, "middle")
    b += arrow(176, 56, 192, 56, "#0C4A6E", 1.6)
    b += phone(196, 24, 32, 56, INK, "#FFFFFF") + R(201, 36, 22, 6, c, 1) + R(201, 46, 22, 6, FAINT, 1) + R(201, 56, 16, 6, FAINT, 1)
    b += T(120, 140, "catch → market → app", 8, "#FFFFFF", 700, "middle")
    return b, c, "A fish and a boat at sea linked to a market stall and a phone app"


def ihealthcare():
    c = "#0D9488"
    b = bg("#F0FDFA")
    for k in range(3):
        y = 34 + k * 22
        b += E(36, y + 20, 20, 6, "#14B8A6") + R(16, y, 40, 20, "#14B8A6") + E(36, y, 20, 6, "#5EEAD4")
    b += T(36, 128, "big data", 7.5, "#115E59", 700, "middle")
    b += arrow(62, 66, 84, 66, c, 1.6)
    nodes = [(96, 46), (96, 66), (96, 86), (118, 56), (118, 76), (138, 66)]
    for a in nodes[:3]:
        for z in nodes[3:5]:
            b += L(*a, *z, "#99F6E4", 1)
    b += L(*nodes[3], *nodes[5], "#99F6E4") + L(*nodes[4], *nodes[5], "#99F6E4")
    b += "".join(C(x, y, 4.5, c) for x, y in nodes)
    b += arrow(146, 66, 160, 66, c, 1.6)
    b += R(164, 24, 66, 86, "#FFFFFF", 6, stroke="#99F6E4") + gauge(197, 74, 22, .72)
    b += T(197, 40, "risk", 8, INK, 700, "middle") + T(197, 98, "high", 8, "#EF4444", 700, "middle")
    return b, c, "Stacked databases feeding a predictive model that drives a patient risk gauge"


def pregnancy_mood():
    c = "#DB2777"
    b = bg("#FDF2F8")
    pts = [(14 + i * 3, 70 + 26 * math.sin(i / 3.2) * (1 - i / 80)) for i in range(50)]
    b += PL(pts, c, 2.4)
    for i, m in [(5, 1), (15, -1), (25, 1), (35, -1), (45, 1)]:
        x, y = pts[i]
        b += face(x, y + (-16 if m == 1 else 16), 8, "#FBCFE8", m)
    b += R(168, 18, 58, 76, "#FFFFFF", 5, stroke="#F9A8D4") + R(185, 14, 24, 9, "#F472B6", 3)
    for k in range(4):
        b += R(176, 32 + k * 14, 7, 7, "none", 1.5, stroke=c) + R(188, 34 + k * 14, 30, 3.5, FAINT, 2)
        if k < 3:
            b += P(f"M177 {35+k*14} l2 2 l4 -4", stroke=c, stroke_width=1.4)
    b += T(197, 110, "survey", 8, "#9D174D", 700, "middle")
    b += T(14, 140, "mood swings during pregnancy", 7.5, "#9D174D", 600)
    return b, c, "An oscillating mood line with happy and sad faces and a survey clipboard"


def smartphone_gpa():
    c = "#4F46E5"
    b = bg("#EEF2FF") + L(28, 124, 226, 124, "#818CF8") + L(28, 14, 28, 124, "#818CF8")
    r = rnd(31)
    for _ in range(40):
        x = r.uniform(34, 222)
        y = 30 + (x - 34) * .42 + r.gauss(0, 13)
        b += C(x, min(max(y, 18), 120), 2.8, c, opacity=".55")
    b += L(32, 32, 224, 112, "#312E81", 2, stroke_dasharray="6 3")
    b += T(222, 136, "screen time →", 7, "#3730A3", 600, "end", fam=MONO)
    b += T(22, 70, "GPA", 7, "#3730A3", 600, "middle", fam=MONO, transform="rotate(-90 22 70)")
    b += phone(194, 12, 26, 44, "#312E81", "#C7D2FE")
    return b, c, "Scatter plot of screen time against GPA with a downward trend line and a phone"


def malnutrition():
    c = "#EA580C"
    b = bg("#FFF7ED")
    def curve(off):
        return [(26 + i * 4, 120 - off - 70 * (1 - math.exp(-i / 18))) for i in range(51)]
    bands = [(-30, "#DCFCE7"), (-14, "#BBF7D0"), (0, "#FEF08A"), (12, "#FECACA")]
    for off, col in bands:
        pts = curve(-off)
        b += PG(pts + [(226, 132), (26, 132)], col)
    b += PG(curve(-24) + [(226, 132), (26, 132)], "#FCA5A5")
    for off in (-30, -14, 0, 12):
        b += PL(curve(-off), "#FFFFFF", 1, opacity=".8")
    r = rnd(9)
    for _ in range(14):
        i = r.randint(3, 48)
        x, y = curve(r.uniform(-28, 26))[i]
        b += C(x, y, 2.6, INK, opacity=".75")
    b += L(26, 132, 226, 132, "#9A3412") + L(26, 20, 26, 132, "#9A3412")
    b += T(226, 144, "age 0–59 months", 7, "#9A3412", 600, "end", fam=MONO) + T(32, 18, "growth z-score bands", 7, "#9A3412", 700)
    return b, c, "Child growth chart with shaded z-score bands and children plotted by age"


def criminal_justice():
    c = "#B45309"
    b = bg("#FFFBEB")
    b += R(116, 30, 8, 92, c) + R(92, 120, 56, 8, c, 2) + C(120, 26, 6, c)
    b += L(44, 40, 196, 52, c, 3)
    b += L(44, 40, 30, 82, "#92400E", 1) + L(44, 40, 58, 82, "#92400E", 1) + P("M24 82 h40 q-4 12 -20 12 q-16 0 -20 -12z", "#F59E0B")
    b += L(196, 52, 182, 94, "#92400E", 1) + L(196, 52, 210, 94, "#92400E", 1) + P("M176 94 h40 q-4 12 -20 12 q-16 0 -20 -12z", "#F59E0B")
    b += person(44, 76, .9, "#78350F")
    b += R(186, 72, 20, 20, "#1F2937", 3) + R(191, 77, 10, 10, "#60A5FA", 1)
    for k in range(3):
        b += L(189 + k * 6, 72, 189 + k * 6, 68, "#1F2937", 1.2) + L(189 + k * 6, 92, 189 + k * 6, 96, "#1F2937", 1.2)
    b += T(44, 116, "human", 8, "#78350F", 700, "middle") + T(196, 124, "machine", 8, "#78350F", 700, "middle")
    b += T(120, 144, "joint judgement", 7.5, "#92400E", 600, "middle")
    return b, c, "Scales of justice balancing a human against a machine"


def bn_speech():
    c = "#22D3EE"
    b = bg("#083344")
    b += R(22, 46, 18, 32, c, 9) + P("M16 64 q0 18 15 18 q15 0 15 -18", stroke=c, stroke_width=2) + L(31, 82, 31, 94, c, 2) + L(23, 94, 39, 94, c, 2)
    b += wave_bars(54, 70, 28, 3.6, 46, c, 7, 2)
    b += arrow(160, 70, 176, 70, "#67E8F9", 1.8)
    b += T(206, 80, "আমি", 26, "#FFFFFF", 700, "middle", fam=BN)
    b += T(20, 130, "speech → Bengali text · RNN", 8, "#67E8F9", 600, fam=MONO)
    return b, c, "Microphone, speech waveform and the resulting Bengali word on a dark teal background"


def carpool():
    c = "#16A34A"
    b = bg("#F1F5F9")
    for d in ["M0 40 q80 20 240 -10", "M0 110 q120 -30 240 20", "M60 0 q-10 80 30 150", "M170 0 q30 70 -10 150"]:
        b += P(d, stroke="#FFFFFF", stroke_width=9) + P(d, stroke="#E2E8F0", stroke_width=1)
    b += P("M18 118 C60 100 70 70 110 64 S170 40 214 30", stroke=c, stroke_width=3.2, stroke_dasharray="1 0")
    for x, y, col in [(76, 82, "#F59E0B"), (128, 58, "#F59E0B"), (168, 44, "#F59E0B")]:
        b += P(f"M{x} {y} c-6 -8 -6 -16 0 -16 c6 0 6 8 0 16z", col) + C(x, y - 11, 2.2, "#FFFFFF")
    b += car(14, 106, .8, c) + P("M210 30 l4 -12 l4 12z", "#DC2626") + C(214, 32, 3, "#DC2626")
    b += R(156, 92, 74, 50, "#FFFFFF", 5, stroke=LINE) + T(162, 102, "Pareto front", 6.5, INK, 700)
    pf = [(166 + i * 7, 134 - 26 * math.exp(-i / 3)) for i in range(9)]
    b += PL(pf, c, 1.4) + "".join(C(x, y, 1.8, c) for x, y in pf)
    r = rnd(2)
    b += "".join(C(r.uniform(176, 222), r.uniform(114, 134), 1.5, FAINT) for _ in range(9))
    return b, c, "A car on a map picking up passengers along an optimal route, with a Pareto-front inset"


def bn_sentiment_supervised():
    c = "#9333EA"
    b = bg("#FFFFFF")
    labs = ["+", "0", "−"]
    m = [[.86, .09, .05], [.12, .74, .14], [.06, .11, .83]]
    b += T(66, 16, "predicted", 7, "#6B21A8", 600, "middle")
    for i in range(3):
        b += T(34 + i * 32 + 16, 28, labs[i], 9, INK, 700, "middle") + T(24, 48 + i * 32, labs[i], 9, INK, 700, "middle")
        for j in range(3):
            v = m[i][j]
            b += R(34 + j * 32, 32 + i * 32, 30, 30, c, 3, opacity=f"{.08+v*.9:.2f}")
            b += T(49 + j * 32, 51 + i * 32, f"{v:.2f}", 7, "#FFFFFF" if v > .5 else INK, 600, "middle", fam=MONO)
    clfs = [("NB", .72), ("SVM", .81), ("LR", .78), ("RF", .76)]
    b += T(150, 32, "classifiers", 7.5, "#6B21A8", 700)
    for k, (lab, v) in enumerate(clfs):
        y = 42 + k * 20
        b += T(150, y + 8, lab, 7, INK, 600, fam=MONO) + R(172, y, 56 * v, 10, c, 2, opacity=f"{.5+.15*k:.2f}")
    b += T(120, 140, "Bengali text · supervised learning", 7.5, "#6B21A8", 600, "middle")
    return b, c, "A confusion matrix for positive, neutral and negative classes and a comparison of classifiers"


def bird_vgg():
    c = "#0EA5E9"
    b = lin("sky", [(0, "#BAE6FD"), (1, "#F0F9FF")]) + bg("url(#sky)")
    b += P("M0 118 q40 -16 80 -6 q30 8 70 -2", stroke="#78350F", stroke_width=4, stroke_linecap="round")
    b += P("M40 106 q-4 -20 14 -30 q10 -6 18 -2 l12 -6 l-6 10 q6 18 -12 28 q-12 6 -26 0z", "#1E3A8A")
    b += P("M48 88 q14 -16 36 -12 q-14 10 -30 14z", "#3B82F6") + C(70, 76, 1.8, "#FFFFFF") + PG([(84, 70), (92, 72), (84, 75)], "#F59E0B")
    b += P("M42 104 l-14 8 l16 -2z", "#1E3A8A") + L(52, 110, 52, 116, "#78350F", 1.2) + L(58, 110, 58, 116, "#78350F", 1.2)
    b += R(24, 62, 74, 52, "none", 2, stroke="#F59E0B", stroke_width=1.8) + R(24, 52, 48, 10, "#F59E0B", 1) + T(27, 60, "bird 0.97", 6.5, "#FFFFFF", 700)
    b += R(126, 22, 104, 96, "#FFFFFF", 6, opacity=".92") + T(134, 36, "VGG-16 top-3", 7.5, INK, 700)
    for k, (lab, v) in enumerate([("magpie robin", .82), ("kingfisher", .11), ("myna", .05)]):
        y = 46 + k * 22
        b += T(134, y + 6, lab, 6.5, "#475569") + R(134, y + 9, 88, 5, "#E0F2FE", 2) + R(134, y + 9, 88 * v, 5, c, 2)
    return b, c, "A bird on a branch inside a detection box with a top-3 species prediction panel"


def crime_map():
    c = "#F43F5E"
    b = bg("#111827")
    for x in range(0, W, 22):
        b += L(x, 0, x + 10, H, "#1F2937", 3)
    for y in range(8, H, 26):
        b += L(0, y, W, y - 6, "#1F2937", 3)
    b += P("M0 96 q60 -10 120 4 t120 -6", stroke="#1E3A8A", stroke_width=8, opacity=".7")
    b += rad("hot", [(0, "#F43F5E", .9), (.5, "#FB923C", .45), (1, "#FB923C", 0)])
    for x, y, r in [(70, 50, 30), (150, 80, 38), (196, 38, 22), (40, 118, 18)]:
        b += C(x, y, r, "url(#hot)")
    b += C(212, 120, 18, "#F9FAFB") + L(212, 120, 212, 108, INK, 2) + L(212, 120, 221, 124, INK, 2) + C(212, 120, 2, INK)
    b += R(10, 10, 74, 16, "#1F2937", 4) + T(16, 21, "hotspots by hour", 7, "#FDA4AF", 600, fam=MONO)
    return b, c, "Dark city map with glowing crime hotspots and a clock"


def ner_hmm():
    c = "#2563EB"
    b = bg("#F8FAFC")
    toks = [("রহিম", "PER", "#2563EB"), ("ঢাকায়", "LOC", "#16A34A"), ("ব্র্যাকে", "ORG", "#EA580C"), ("কাজ", "O", "#94A3B8"), ("করে", "O", "#94A3B8")]
    x = 10
    for w, tag, col in toks:
        ww = 46 if tag != "O" else 36
        b += R(x, 22, ww - 4, 10, col, 2) + T(x + (ww - 4) / 2, 30, tag, 6.6, "#FFFFFF", 700, "middle", fam=MONO)
        b += R(x, 34, ww - 4, 24, "#FFFFFF", 3, stroke=col) + T(x + (ww - 4) / 2, 51, w, 10, INK, 600, "middle", fam=BN)
        x += ww
    xs = [31, 77, 123, 162, 200]
    for k, x0 in enumerate(xs):
        b += C(x0, 104, 12, "#DBEAFE", stroke=c, stroke_width=1.4) + T(x0, 108, f"s{k+1}", 8, c, 700, "middle", fam=MONO)
        b += L(x0, 92, x0, 62, "#BFDBFE", 1, stroke_dasharray="2 2")
        if k < 4:
            b += arrow(x0 + 12, 104, xs[k + 1] - 13, 104, c, 1.3)
    b += T(10, 140, "hidden Markov model + rules", 7.5, "#1E40AF", 600)
    return b, c, "Bengali sentence tokens tagged as person, location and organisation over a hidden Markov state chain"


def road_accident():
    c = "#F59E0B"
    b = lin("rsky", [(0, "#FEF3C7"), (1, "#FFFBEB")]) + bg("url(#rsky)")
    b += PG([(100, 40), (140, 40), (236, 150), (4, 150)], "#475569")
    for k in range(5):
        y0 = 46 + k * 22
        t0, t1 = (y0 - 40) / 110, (y0 + 10 - 40) / 110
        b += PG([(120 - .5 - t0 * 2, y0), (120 + .5 + t0 * 2, y0), (120 + .5 + t1 * 2, y0 + 10), (120 - .5 - t1 * 2, y0 + 10)], "#FDE047")
    b += L(0, 40, 240, 40, "#A3A3A3", .8)
    b += PG([(36, 34), (58, 72), (14, 72)], c, stroke="#B45309", stroke_width=1.4) + T(36, 66, "!", 18, "#1F2937", 800, "middle")
    b += L(36, 72, 36, 96, "#78716C", 2)
    b += R(150, 8, 82, 26, "#FFFFFF", 5, opacity=".95") + T(156, 18, "predicted severity", 6, INK, 600)
    for k, col in enumerate(["#22C55E", "#FACC15", "#F97316", "#EF4444"]):
        b += R(156 + k * 18, 22, 17, 6, col, 1)
    b += PG([(208, 30), (204, 36), (212, 36)], INK)
    for x, y in [(90, 98), (164, 118)]:
        b += P(f"M{x} {y} c-7 -9 -7 -18 0 -18 c7 0 7 9 0 18z", "#EF4444") + C(x, y - 12, 2.4, "#FFFFFF")
    return b, c, "A road in perspective with a warning sign, incident pins and a severity scale"


def abusive_text():
    c = "#E11D48"
    b = bg("#FFF1F2")
    b += bubble(14, 14, 120, 26, "#FFFFFF", "left", stroke="#FECDD3") + T(24, 31, "খেলাটা দারুণ হয়েছে", 9, INK, 500, fam=BN)
    b += bubble(60, 52, 120, 26, "#FFE4E6", "right", stroke=c) + "".join(R(70 + k * 18, 61, 14, 8, "#FDA4AF", 3) for k in range(5))
    b += C(176, 52, 9, c) + T(176, 56, "!", 11, "#FFFFFF", 800, "middle")
    b += bubble(14, 90, 100, 26, "#FFFFFF", "left", stroke="#FECDD3") + T(24, 107, "আবার দেখা হবে", 9, INK, 500, fam=BN)
    for k, n in enumerate([4, 6, 4, 2]):
        for j in range(n):
            y = 98 + (j - (n - 1) / 2) * 8
            b += C(150 + k * 20, y + 10, 2.8, c if k == 3 else "#FDA4AF")
    b += T(220, 140, "abusive", 7, c, 700, "end", fam=MONO)
    return b, c, "Bengali chat with one abusive message masked and flagged, plus a small neural network"


def passman():
    c = "#0F766E"
    b = bg("#F0FDFA")
    b += C(30, 74, 13, "none", stroke=c, stroke_width=4) + R(42, 71, 34, 6, c, 2) + R(66, 77, 4, 8, c) + R(58, 77, 4, 6, c)
    b += T(44, 104, "master", 7.5, "#115E59", 700, "middle")
    b += arrow(84, 74, 98, 74, c, 1.6)
    b += R(100, 56, 40, 36, c, 6) + T(120, 79, "f(x)", 11, "#FFFFFF", 700, "middle", fam=MONO)
    sites = ["mail", "bank", "social"]
    for k, s in enumerate(sites):
        y = 22 + k * 38
        b += L(140, 74, 154, y + 12, "#5EEAD4", 1.2)
        b += R(154, y, 76, 24, "#FFFFFF", 5, stroke="#99F6E4") + T(160, y + 10, s, 6.5, "#64748B", fam=MONO)
        b += "".join(C(162 + j * 7, y + 17, 2, INK) for j in range(8))
    b += E(36, 130, 12, 4, "#94A3B8") + R(24, 118, 24, 12, "#94A3B8") + E(36, 118, 12, 4, "#CBD5E1")
    b += L(20, 136, 52, 112, "#DC2626", 2.4) + T(58, 128, "nothing stored", 7, "#B91C1C", 600)
    return b, c, "A master key passed through a function to generate per-site passwords, with storage crossed out"


def fake_news_chain():
    c = "#B91C1C"
    b = bg("#F5F5F4")
    b += R(16, 10, 120, 92, "#FFFFFF", 2, stroke="#D6D3D1") + R(24, 18, 104, 9, "#1C1917", 1)
    b += R(24, 32, 50, 34, "#D6D3D1") + bars_text(80, 33, [46, 40, 46, 34, 44], "#E7E5E4", 3.5, 7)
    b += bars_text(24, 72, [104, 96, 104, 80], "#E7E5E4", 3.5, 7)
    b += G(R(54, 40, 72, 26, "none", 4, stroke=c, stroke_width=2.4) + T(90, 59, "FAKE", 15, c, 900, "middle"), transform="rotate(-14 90 53)", opacity=".9")
    for k in range(4):
        x = 20 + k * 54
        b += block(x, 112, 1.3, "#1E40AF" if k < 3 else c)
        if k < 3:
            b += E(x + 38, 124, 7, 3.5, "none", stroke="#78716C", stroke_width=1.6)
    b += T(226, 22, "ledger", 7.5, "#44403C", 600, "end", fam=MONO)
    return b, c, "A newspaper stamped FAKE above a chain of blockchain blocks"


def symptom_bn():
    c = "#0891B2"
    b = bg("#ECFEFF")
    b += R(14, 12, 110, 126, "#FFFFFF", 6, stroke="#A5F3FC")
    for k, (s, on) in enumerate([("জ্বর", 1), ("কাশি", 1), ("মাথাব্যথা", 0), ("গলা ব্যথা", 1)]):
        y = 26 + k * 28
        b += R(22, y, 12, 12, c if on else "#FFFFFF", 3, stroke=c, stroke_width=1.3)
        if on:
            b += P(f"M25 {y+6} l2.5 2.5 l5 -5", stroke="#FFFFFF", stroke_width=1.6)
        b += T(40, y + 10, s, 10, INK, 600, fam=BN)
    b += R(144, 18, 12, 74, "#FFFFFF", 6, stroke="#F87171") + R(147, 44, 6, 46, "#EF4444", 3) + C(150, 98, 10, "#EF4444")
    b += R(166, 30, 64, 66, "#FFFFFF", 6, stroke="#A5F3FC") + T(172, 42, "diagnosis", 6.5, "#64748B")
    for k, (lab, v) in enumerate([("flu", .74), ("dengue", .18), ("cold", .08)]):
        y = 50 + k * 14
        b += T(172, y + 6, lab, 6, INK) + R(196, y, 30 * v / .74, 7, c, 2, opacity=f"{1-k*.3:.2f}")
    b += T(198, 126, "CNN", 10, c, 800, "middle", fam=MONO)
    return b, c, "A Bengali symptom checklist, a thermometer and a predicted-diagnosis card"


def transliteration():
    c = "#7C3AED"
    b = bg("#FAF5FF")
    b += R(12, 14, 66, 28, "#FFFFFF", 6, stroke="#DDD6FE") + T(45, 33, "amar", 13, INK, 600, "middle", fam=MONO)
    b += arrow(84, 28, 104, 28, c, 1.8)
    b += R(110, 12, 70, 32, c, 6) + T(145, 34, "আমার", 15, "#FFFFFF", 700, "middle", fam=BN)
    s1, s2 = "amr", "amar"
    n, m = len(s1), len(s2)
    D = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        for j in range(m + 1):
            D[i][j] = j if i == 0 else i if j == 0 else min(D[i - 1][j] + 1, D[i][j - 1] + 1, D[i - 1][j - 1] + (s1[i - 1] != s2[j - 1]))
    path = {(0, 0), (1, 1), (2, 2), (2, 3), (3, 4)}
    x0, y0, cs = 64, 58, 17
    for j, ch in enumerate(" " + s2):
        b += T(x0 + j * cs + cs / 2, y0 - 3, ch, 7, "#6D28D9", 700, "middle", fam=MONO)
    for i, ch in enumerate(" " + s1):
        b += T(x0 - 6, y0 + i * cs + 12, ch, 7, "#6D28D9", 700, "middle", fam=MONO)
        for j in range(m + 1):
            on = (i, j) in path
            b += R(x0 + j * cs, y0 + i * cs, cs - 2, cs - 2, c if on else "#FFFFFF", 2, stroke="#DDD6FE")
            b += T(x0 + j * cs + (cs - 2) / 2, y0 + i * cs + 11, str(D[i][j]), 7, "#FFFFFF" if on else INK, 600, "middle", fam=MONO)
    b += T(160, 90, "edit distance", 7.5, "#6D28D9", 700) + T(160, 102, "= 1", 13, c, 800, fam=MONO)
    return b, c, "Romanised 'amar' auto-corrected to the Bengali word with a Levenshtein edit-distance table"


def dew_computing():
    c = "#0EA5E9"
    b = lin("dew", [(0, "#F0F9FF"), (1, "#E0F2FE")]) + bg("url(#dew)")
    b += cloud(70, 30, 1.4, "#93C5FD") + T(108, 34, "cloud", 7, "#1E3A8A", 700, "middle")
    b += P("M0 74 q30 -10 60 0 t60 0 t60 0 t60 0 v14 q-30 10 -60 0 t-60 0 t-60 0 t-60 0z", "#BAE6FD", opacity=".85")
    b += T(16, 84, "fog", 7, "#0369A1", 700)
    b += P("M120 98 c-10 14 -14 22 -14 28 a14 14 0 0 0 28 0 c0 -6 -4 -14 -14 -28z", c) + E(115, 122, 3, 5, "#FFFFFF", opacity=".6")
    b += T(146, 124, "dew", 8, "#0369A1", 700)
    b += phone(60, 106, 20, 34, INK, "#E0F2FE") + R(164, 112, 30, 20, INK, 2) + R(167, 115, 24, 14, "#E0F2FE")
    b += L(82, 120, 104, 120, c, 1.2, stroke_dasharray="2 2") + L(136, 120, 162, 120, c, 1.2, stroke_dasharray="2 2")
    b += C(212, 40, 14, "#FFFFFF", stroke="#0369A1", stroke_width=2) + R(209, 22, 6, 4, "#0369A1", 1) + L(212, 40, 212, 31, "#EF4444", 2) + L(212, 40, 219, 43, "#0369A1", 1.6)
    return b, c, "Cloud, fog and dew layers with a water droplet next to local devices and a stopwatch"


def pension():
    c = "#15803D"
    b = bg("#F0FDF4")
    b += R(16, 18, 60, 80, "#FFFFFF", 3, stroke="#BBF7D0") + bars_text(24, 28, [40, 32, 44, 28, 36, 40], "#D1D5DB", 3.5, 8)
    b += C(56, 84, 12, "none", stroke="#DC2626", stroke_width=2, opacity=".8") + T(56, 88, "✓", 10, "#DC2626", 700, "middle")
    b += arrow(84, 58, 104, 58, c, 1.8)
    b += phone(108, 14, 46, 86, INK, "#FFFFFF") + C(131, 46, 13, "#FDE047", stroke="#CA8A04", stroke_width=1.4) + T(131, 51, "৳", 13, "#854D0E", 800, "middle", fam=BN)
    b += R(115, 68, 32, 9, c, 3) + T(131, 75, "withdraw", 5.5, "#FFFFFF", 700, "middle")
    b += person(196, 76, 1.5, "#166534") + L(214, 62, 220, 100, "#78350F", 2) + P("M214 62 q-6 -4 -8 2", stroke="#78350F", stroke_width=2)
    b += T(120, 126, "paperwork → digital pension", 8, "#14532D", 700, "middle")
    return b, c, "A stamped paper form becoming a phone pension withdrawal for an older person"


def music_piracy():
    c = "#9333EA"
    b = bg("#FAF5FF")
    factors = ["price", "access", "peers"]
    for k, fct in enumerate(factors):
        y = 24 + k * 38
        b += E(44, y + 10, 32, 13, "#FFFFFF", stroke=c, stroke_width=1.4) + T(44, y + 13, fct, 8, "#6B21A8", 600, "middle")
        b += arrow(77, y + 10, 140, 70, "#C084FC", 1.4)
        b += T(104, y + 12 + (k - 1) * 4, ["β .41", "β .29", "β .36"][k], 6.5, "#7E22CE", 600, "middle", fam=MONO)
    b += R(142, 56, 50, 28, c, 4) + T(167, 74, "piracy", 8.5, "#FFFFFF", 700, "middle")
    b += P("M206 34 v30 a6 5 0 1 1 -3 -4 v-20 l14 -4 v22 a6 5 0 1 1 -3 -4 v-14z", "#7E22CE")
    b += P("M200 112 q0 -22 18 -22 q18 0 18 22", stroke=INK, stroke_width=3) + R(196, 108, 8, 16, INK, 3) + R(232, 108, 8, 16, INK, 3)
    return b, c, "A path diagram of factors leading to music piracy, with a music note and headphones"


def social_socialization():
    c = "#2563EB"
    b = bg("#EFF6FF")
    r = rnd(17)
    pts = [(120, 74)] + [(120 + math.cos(a) * rr, 74 + math.sin(a) * rr * .62) for a, rr in
                         [(k * 2 * math.pi / 13 + r.uniform(-.2, .2), r.choice([52, 88, 70])) for k in range(13)]]
    for i in range(1, len(pts)):
        b += L(*pts[0], *pts[i], "#BFDBFE", 1)
        j = r.randrange(1, len(pts))
        if j != i:
            b += L(*pts[i], *pts[j], "#DBEAFE", 1)
    cols = ["#2563EB", "#F59E0B", "#10B981", "#EC4899"]
    for i, (x, y) in enumerate(pts[1:]):
        b += C(x, y, 7, "#FFFFFF", stroke=cols[i % 4], stroke_width=1.6) + person(x, y + 3, .4, cols[i % 4])
    b += C(120, 74, 13, c) + R(114, 66, 12, 17, "#FFFFFF", 2) + R(116, 69, 8, 9, "#BFDBFE")
    b += bubble(150, 16, 30, 14, "#FFFFFF", "left", stroke="#93C5FD") + T(165, 26, "hi!", 7, c, 700, "middle")
    return b, c, "A social network of students around a phone, each node a person"


def software_piracy():
    c = "#475569"
    b = bg("#F8FAFC")
    b += lin("cd", [(0, "#E0E7FF"), (.3, "#FBCFE8"), (.6, "#BBF7D0"), (1, "#FDE68A")], 1, 1)
    b += C(60, 72, 48, "url(#cd)", stroke="#CBD5E1") + C(60, 72, 13, "#F8FAFC", stroke="#CBD5E1") + C(60, 72, 4, "#E2E8F0")
    b += C(60, 72, 22, "none", stroke="#FFFFFF", stroke_width=6, opacity=".35")
    b += C(60, 72, 30, "none", stroke="#DC2626", stroke_width=4) + L(39, 51, 81, 93, "#DC2626", 4)
    cx, cy, rr = 178, 72, 44
    axes = ["cost", "skill", "ethics", "risk", "access"]
    vals = [.9, .6, .3, .45, .8]
    for k in range(5):
        a = -math.pi / 2 + k * 2 * math.pi / 5
        b += L(cx, cy, cx + rr * math.cos(a), cy + rr * math.sin(a), FAINT)
        b += T(cx + (rr + 6) * math.cos(a), cy + (rr + 6) * math.sin(a) + 3, axes[k], 6, "#64748B", 600, "middle")
    for s in (.5, 1):
        b += PG([(cx + rr * s * math.cos(-math.pi / 2 + k * 2 * math.pi / 5), cy + rr * s * math.sin(-math.pi / 2 + k * 2 * math.pi / 5)) for k in range(5)], "none", stroke=LINE)
    b += PG([(cx + rr * v * math.cos(-math.pi / 2 + k * 2 * math.pi / 5), cy + rr * v * math.sin(-math.pi / 2 + k * 2 * math.pi / 5)) for k, v in enumerate(vals)], "#64748B", opacity=".45", stroke=INK, stroke_width=1.2)
    return b, c, "A software disc with a prohibition sign and a radar chart profiling piracy factors"


def ride_security():
    c = "#F97316"
    b = lin("night", [(0, "#1E1B4B"), (1, "#312E81")]) + bg("url(#night)")
    r = rnd(6)
    b += "".join(C(r.uniform(0, 240), r.uniform(0, 60), r.uniform(.5, 1.2), "#FFFFFF", opacity=f"{r.uniform(.4, .9):.2f}") for _ in range(22))
    b += C(214, 24, 10, "#FEF9C3") + C(219, 21, 9, "#1E1B4B")
    b += R(0, 120, W, 30, "#1F2937") + "".join(R(x, 134, 14, 3, "#FDE047") for x in range(6, W, 30))
    b += L(36, 120, 36, 50, "#64748B", 3) + P("M36 50 q0 -8 12 -8", stroke="#64748B", stroke_width=3) + PG([(42, 42), (56, 42), (52, 48), (46, 48)], "#FDE68A")
    b += PG([(49, 48), (30, 120), (68, 120)], "#FDE68A", opacity=".12")
    b += car(66, 104, 1.6, "#94A3B8", "#475569")
    b += phone(150, 34, 52, 92, "#0F172A", "#F8FAFC")
    b += P("M158 56 q14 10 20 -2 t16 10", stroke="#3B82F6", stroke_width=2) + C(158, 56, 2.6, "#3B82F6") + C(194, 64, 2.6, "#3B82F6")
    b += C(176, 96, 14, "#EF4444") + T(176, 100, "SOS", 8, "#FFFFFF", 800, "middle")
    b += R(160, 74, 32, 4, FAINT, 2)
    return b, c, "A car on a night street next to a phone showing a route and a red SOS button"


def farming_chain():
    c = "#65A30D"
    b = lin("farm", [(0, "#ECFCCB"), (1, "#F7FEE7")]) + bg("url(#farm)")
    b += PG([(0, 150), (0, 90), (100, 80), (110, 150)], "#84CC16")
    for k in range(6):
        b += L(4 + k * 18, 150, 10 + k * 15, 86, "#4D7C0F", 2, opacity=".55")
    b += person(54, 72, 1.3, "#78350F") + P("M42 56 h24 l-4 -6 h-16z", "#CA8A04")
    b += P("M180 96 h40 l-6 30 h-28z", "#B45309") + "".join(C(188 + k * 8, 94, 5, ["#EF4444", "#F59E0B", "#22C55E", "#EF4444"][k]) for k in range(4))
    b += person(200, 64, 1.2, "#1D4ED8")
    b += person(140, 44, .9, "#9CA3AF") + L(128, 24, 152, 52, "#DC2626", 2.4) + L(152, 24, 128, 52, "#DC2626", 2.4)
    b += arrow(80, 110, 176, 110, c, 2)
    for k in range(3):
        b += block(96 + k * 24, 116, .85, "#3F6212")
    b += T(140, 70, "middlemen", 6.5, "#991B1B", 600, "middle")
    return b, c, "Farmer selling straight to a consumer through blockchain blocks, with the middleman crossed out"


def plant_rcnn():
    c = "#FACC15"
    b = bg("#14532D")
    for cx, cy, s, rot, col in [(50, 60, 1.5, -30, "#16A34A"), (120, 80, 1.8, 10, "#22C55E"), (194, 58, 1.4, 35, "#15803D"), (176, 122, 1.1, -60, "#16A34A"), (40, 126, 1, 70, "#15803D")]:
        b += leaf(cx, cy, s, rot, col, "#BBF7D0")
    r = rnd(12)
    for cx, cy in [(58, 52), (128, 70), (190, 64)]:
        for _ in range(4):
            b += C(cx + r.uniform(-6, 6), cy + r.uniform(-6, 6), r.uniform(1.5, 3.2), "#78350F")
    for (x, y, w, h, lab, col) in [(40, 38, 34, 30, "blight .94", c), (112, 56, 34, 30, "rust .88", "#F97316"), (176, 48, 30, 30, "spot .81", "#F43F5E")]:
        b += R(x, y, w, h, "none", 2, stroke=col, stroke_width=1.8) + R(x, y - 10, w + 8, 10, col, 1) + T(x + 2, y - 2.5, lab, 6, "#1F2937", 700, fam=MONO)
    b += R(8, 130, 82, 14, "#052E16", 3, opacity=".8") + T(14, 140, "Faster R-CNN", 7.5, "#BBF7D0", 700, fam=MONO)
    return b, c, "Photo-like leaves on a dark background with labelled disease detection boxes"


def word_prediction():
    c = "#0369A1"
    b = bg("#E2E8F0")
    b += R(10, 10, 220, 28, "#FFFFFF", 6) + T(18, 29, "আমি ভাত", 12, INK, 600, fam=BN) + R(76, 17, 1.6, 15, c)
    b += R(10, 44, 220, 22, "#F8FAFC", 4)
    for k, (w, on) in enumerate([("খাই", True), ("খাবো", False), ("খেয়েছি", False)]):
        x = 14 + k * 72
        b += R(x, 47, 68, 16, c if on else "#E2E8F0", 4) + T(x + 34, 59, w, 9.5, "#FFFFFF" if on else INK, 600, "middle", fam=BN)
    keys = ["অআইঈউঊঋএঐও", "কখগঘঙচছজঝ", "টঠডঢণতথদধ"]
    for i, row in enumerate(keys):
        for j, ch in enumerate(row):
            x = 12 + j * 22.4 + i * 6
            b += R(x, 72 + i * 24, 20, 20, "#FFFFFF", 3) + T(x + 10, 87 + i * 24, ch, 9.5, INK, 500, "middle", fam=BN)
    return b, c, "A Bengali phone keyboard with next-word suggestions above it"


def cloud_multimedia():
    c = "#2563EB"
    b = bg("#EFF6FF")
    b += cloud(80, 34, 1.6, "#BFDBFE") + C(116, 30, 12, c) + PG([(112, 23), (112, 37), (123, 30)], "#FFFFFF")
    devs = [(24, 96, "laptop"), (104, 102, "phone"), (176, 92, "tv")]
    for x, y, kind in devs:
        b += L(118, 50, x + 20, y - 4, "#93C5FD", 1.4, stroke_dasharray="4 3")
        if kind == "laptop":
            b += R(x, y, 40, 26, INK, 3) + R(x + 3, y + 3, 34, 20, "#DBEAFE") + R(x - 4, y + 26, 48, 4, "#475569", 2)
        elif kind == "phone":
            b += phone(x + 8, y - 6, 22, 40, INK, "#DBEAFE")
        else:
            b += R(x, y, 50, 32, INK, 3) + R(x + 3, y + 3, 44, 26, "#DBEAFE") + L(x + 25, y + 32, x + 25, y + 38, INK, 2)
    for x, v in [(24, .9), (112, .7), (176, .8)]:
        b += R(x, 138, 40, 5, "#DBEAFE", 2) + R(x, 138, 40 * v, 5, "#22C55E", 2)
    b += T(10, 16, "QoS-aware streaming", 7.5, "#1E40AF", 700)
    return b, c, "A cloud streaming video to a laptop, phone and TV, each with a quality-of-service bar"


def big_media_health():
    c = "#0D9488"
    b = bg("#F0FDFA")
    for k, x in enumerate([14, 70]):
        b += R(x, 82, 44, 46, "#FFFFFF", 2, stroke="#99F6E4") + R(x + 16, 108, 12, 20, "#5EEAD4")
        b += R(x + 17, 88, 10, 14, "#EF4444", 1) + R(x + 15, 92, 14, 6, "#EF4444", 1)
    b += R(126, 92, 26, 32, "#1F2937", 2) + E(139, 104, 6, 9, "none", stroke="#E5E7EB", stroke_width=1.4) + L(139, 96, 139, 116, "#E5E7EB", 1)
    clouds = [(18, 30), (94, 18), (168, 34)]
    for x, y in clouds:
        b += cloud(x, y, 1.1, "#99F6E4")
    b += L(48, 34, 110, 22, c, 1.6, stroke_dasharray="3 2") + L(140, 22, 186, 36, c, 1.6, stroke_dasharray="3 2") + L(60, 38, 180, 40, c, 1, stroke_dasharray="2 3")
    b += arrow(36, 80, 36, 52, c, 1.4) + arrow(92, 80, 110, 42, c, 1.4) + arrow(152, 96, 186, 50, c, 1.4)
    b += R(166, 90, 64, 40, "#FFFFFF", 5, stroke="#99F6E4") + T(198, 104, "collaborative", 6.5, "#115E59", 700, "middle") + T(198, 116, "resource mgmt", 6.5, "#115E59", 600, "middle")
    return b, c, "Hospitals and medical images sending data to three cooperating clouds"


def triple_e():
    c = "#22C55E"
    b = bg("#0F172A")
    pools = [("hot", "#EF4444", 14), ("warm", "#F59E0B", 88), ("cold", "#38BDF8", 162)]
    for name, col, x in pools:
        b += R(x, 20, 64, 104, "none", 6, stroke=col, stroke_width=1.2, stroke_dasharray="4 3")
        b += T(x + 32, 16, name, 7, col, 700, "middle", fam=MONO)
        for k in range(3):
            b += server(x + 6 + k * 19, 30, 15, 84, "#1E293B", col if name != "cold" or k == 0 else "#334155")
    b += P("M120 128 c-22 0 -26 18 -26 18 c18 2 30 -6 26 -18z", c) + L(96, 146, 112, 136, "#14532D", 1.2)
    b += T(130, 142, "Triple-E", 8, c, 700, fam=MONO)
    return b, c, "Data-center racks in hot, warm and cold pools with an energy-saving leaf"


def qmac():
    c = "#7C3AED"
    b = bg("#F5F3FF")
    b += cloud(150, 34, 1.5, "#DDD6FE") + T(186, 40, "cloud", 7, "#5B21B6", 700, "middle")
    b += tower(108, 60, 1.4, "#6D28D9")
    for k, op in enumerate([.18, .35, 1]):
        x = 16 + k * 26
        b += G(phone(x, 92, 22, 40, INK, "#EDE9FE"), opacity=f"{op}")
    b += P("M24 140 q30 6 64 -2", stroke="#A78BFA", stroke_width=1.4, stroke_dasharray="3 3")
    for k, (x, y) in enumerate([(84, 86), (124, 46), (166, 24)]):
        b += R(x, y, 12, 12, c, 2, opacity=f"{1-k*.15:.2f}")
    b += P("M80 98 Q100 70 108 64 M118 56 Q150 34 168 30", stroke=c, stroke_width=1.4, stroke_dasharray="3 2")
    b += R(150, 100, 80, 36, "#FFFFFF", 6, stroke="#DDD6FE") + T(156, 114, "offload ✓ QoS", 7, "#5B21B6", 700)
    b += T(156, 128, "while moving", 7, "#64748B")
    return b, c, "A moving phone offloading app tasks through a cell tower to the cloud"


def iot_fog_cloud():
    c = "#2563EB"
    b = bg("#F8FAFC")
    layers = [("cloud", "#1D4ED8", 92, 22, 56), ("fog", "#60A5FA", 62, 56, 116), ("IoT", "#BFDBFE", 30, 90, 180)]
    for name, col, x, y, w in layers:
        b += PG([(x + 6, y), (x + w - 6, y), (x + w, y + 30), (x, y + 30)], col)
        b += T(x + w / 2, y + 19, name, 8, "#FFFFFF" if name != "IoT" else "#1E3A8A", 700, "middle")
    for k in range(6):
        b += C(46 + k * 30, 132, 4, "#1E40AF")
    b += P("M208 30 q0 -12 10 -12 q10 0 10 12 v10 l4 5 h-28 l4 -5z", "#F59E0B") + C(218, 49, 3, "#F59E0B")
    b += PG([(176, 26), (168, 42), (176, 42), (170, 56), (186, 36), (178, 36), (184, 26)], "#EF4444")
    b += T(16, 18, "time-sensitive events", 7.5, "#1E3A8A", 700)
    return b, c, "Three-tier IoT, fog and cloud pyramid with an alarm bell and lightning for urgent events"


def numeracy_autism():
    c = "#F59E0B"
    b = bg("#FEF9C3")
    b += R(14, 12, 212, 126, "#1F2937", 12) + R(22, 20, 196, 110, "#FFFFFF", 6)
    def apple(x, y):
        return C(x, y, 8, "#EF4444") + P(f"M{x} {y-8} q3 -6 7 -5", stroke="#16A34A", stroke_width=2)
    b += apple(40, 54) + apple(60, 54) + apple(50, 72)
    b += T(82, 68, "+", 20, INK, 800, "middle")
    b += apple(104, 54) + apple(116, 72)
    b += T(140, 68, "=", 20, INK, 800, "middle")
    b += R(156, 42, 40, 40, "#FEF3C7", 8, stroke=c, stroke_width=2, stroke_dasharray="4 3") + T(176, 70, "?", 22, c, 800, "middle")
    for k, (n, col) in enumerate([("4", "#93C5FD"), ("5", "#86EFAC"), ("6", "#F9A8D4")]):
        b += R(66 + k * 38, 96, 30, 26, col, 6) + T(81 + k * 38, 115, n, 15, INK, 800, "middle")
    return b, c, "A tablet with a counting game: three apples plus two apples equals a number tile to pick"


def safe_driving():
    c = "#DC2626"
    b = bg("#18181B")
    b += P("M0 150 L0 96 Q120 70 240 96 L240 150z", "#27272A")
    b += gauge(60, 112, 34, .8, ("#22C55E", "#FACC15", "#EF4444")) + T(60, 132, "km/h", 7, "#A1A1AA", 600, "middle", fam=MONO)
    b += C(150, 160, 56, "none", stroke="#3F3F46", stroke_width=10)
    b += R(160, 20, 64, 46, "#0A0A0A", 6, stroke="#52525B") + R(164, 24, 56, 38, "#FEF2F2", 3)
    b += PG([(192, 30), (204, 52), (180, 52)], c) + T(192, 49, "!", 11, "#FFFFFF", 800, "middle")
    b += L(192, 66, 192, 80, "#52525B", 3)
    b += T(16, 24, "IoT · phone sensors", 7.5, "#FCA5A5", 600, fam=MONO)
    for k in range(3):
        b += P(f"M{150+k*6} {36-k*3} q-6 8 0 16", stroke=c, stroke_width=1.4, opacity=f"{1-k*.3:.2f}", transform=f"rotate(180 {150+k*6} 44)")
    return b, c, "A car dashboard at night with a speedometer and a phone showing a safety alert"


def ihemha():
    c = "#DB2777"
    b = bg("#FDF2F8")
    b += C(56, 68, 36, "#FBCFE8") + C(44, 60, 3.6, INK) + C(68, 60, 3.6, INK) + P("M40 80 q16 14 32 0", stroke=INK, stroke_width=2.2, stroke_linecap="round")
    for x, y in [(44, 60), (68, 60), (56, 70), (40, 80), (72, 80), (56, 86), (36, 50), (76, 50)]:
        b += C(x, y, 1.6, "#22C55E")
    b += R(16, 26, 80, 84, "none", 3, stroke=c, stroke_width=1.4, stroke_dasharray="4 3") + R(16, 112, 54, 13, c, 2) + T(20, 121, "happy 0.91", 6.5, "#FFFFFF", 700, fam=MONO)
    b += L(124, 22, 124, 128, "#F9A8D4", 2)
    for k, (lab, col) in enumerate([("2014 checkup", "#F472B6"), ("2015 allergy", "#FB7185"), ("2016 surgery", c), ("2017 now", "#9D174D")]):
        y = 30 + k * 28
        b += C(124, y, 5, col) + R(134, y - 9, 92, 18, "#FFFFFF", 4, stroke="#FBCFE8") + T(140, y + 3, lab, 7, INK, 600)
    return b, c, "Face with emotion landmarks next to a medical-history timeline"


def vehicular_cloud():
    c = "#2563EB"
    b = bg("#EFF6FF")
    b += R(0, 96, W, 40, "#475569") + "".join(R(x, 114, 16, 3, "#FFFFFF") for x in range(4, W, 30))
    cars = [(10, 98, "#3B82F6"), (66, 118, "#F59E0B"), (130, 98, "#10B981"), (186, 118, "#EF4444")]
    for x, y, col in cars:
        b += car(x, y, .95, col)
    b += cloud(70, 34, 1.7, "#BFDBFE")
    for x, y, col in cars:
        b += L(x + 20, y - 4, 120, 46, col, 1.2, stroke_dasharray="3 2")
    for k, col in enumerate(["#3B82F6", "#F59E0B", "#10B981", "#EF4444"]):
        b += R(96 + k * 13, 24, 11, 9, col, 1.5)
    b += T(10, 16, "vehicles as a cloud", 7.5, "#1E3A8A", 700)
    return b, c, "Cars on a highway linked to a shared cloud overhead that schedules their tasks"


def soil_sensor():
    c = "#92400E"
    b = bg("#E0F2FE")
    for y, h, col in [(52, 30, "#A16207"), (82, 34, "#854D0E"), (116, 34, "#713F12")]:
        b += R(0, y, W, h, col)
    r = rnd(1)
    b += "".join(C(r.uniform(0, 240), r.uniform(56, 148), r.uniform(.8, 2), "#FDE68A", opacity=".35") for _ in range(30))
    b += L(70, 52, 70, 22, "#15803D", 2.4) + leaf(62, 28, .45, -50, "#22C55E", "#DCFCE7") + leaf(78, 22, .45, 50, "#16A34A", "#DCFCE7")
    b += R(110, 18, 16, 30, "#334155", 3) + R(113, 22, 10, 8, "#22D3EE") + R(116, 48, 4, 64, "#94A3B8") + PG([(116, 112), (120, 112), (118, 120)], "#94A3B8")
    b += L(126, 30, 150, 30, "#334155", 1.4)
    b += R(150, 10, 80, 50, "#FFFFFF", 6, stroke="#BAE6FD")
    for k, (n, v, col) in enumerate([("N", .7, "#22C55E"), ("P", .45, "#F59E0B"), ("K", .6, "#8B5CF6")]):
        x = 162 + k * 22
        b += R(x, 50 - 30 * v, 12, 30 * v, col, 2) + T(x + 6, 57, n, 6.5, INK, 700, "middle", fam=MONO)
    return b, c, "Soil cross-section with a probe sensor and a readout of nitrogen, phosphorus and potassium"


def confederation():
    c = "#1D4ED8"
    b = bg("#F8FAFC")
    pos = [(20, 40, "A"), (140, 34, "B"), (80, 110, "C")]
    for (x1, y1, _), (x2, y2, _) in [(pos[0], pos[1]), (pos[1], pos[2]), (pos[2], pos[0])]:
        b += L(x1 + 22, y1, x2 + 22, y2, "#93C5FD", 2, stroke_dasharray="5 3")
    for x, y, lab in pos:
        b += cloud(x, y, 1.05, "#DBEAFE") + T(x + 23, y + 6, f"IaaS {lab}", 7, c, 700, "middle")
    for x, y in [(80, 32), (54, 78), (118, 76)]:
        b += R(x, y, 12, 9, c, 2)
    for x, y in [(206, 40), (214, 76), (200, 108)]:
        b += C(x, y, 10, "#FDE047", stroke="#CA8A04", stroke_width=1.4) + T(x, y + 4, "$", 10, "#854D0E", 800, "middle")
    b += T(206, 140, "profit + QoS", 7, "#1E3A8A", 700, "middle")
    return b, c, "Three federated IaaS clouds trading virtual machines, with coins for profit"


def energy_sched():
    c = "#16A34A"
    b = bg("#FFFFFF")
    r = rnd(13)
    cols = ["#22C55E", "#0EA5E9", "#A855F7", "#F59E0B"]
    for k in range(4):
        y = 66 + k * 18
        b += T(10, y + 10, f"S{k+1}", 7, "#64748B", 600, fam=MONO) + L(26, y + 15, 230, y + 15, "#F1F5F9")
        x = 28
        while x < 220:
            w = r.uniform(14, 40)
            if r.random() < .7:
                b += R(x, y, min(w, 228 - x), 12, cols[(k + int(x)) % 4], 2, opacity=".85")
            x += w + r.uniform(2, 14)
    pw = [(28 + i * 10, 46 - 26 * abs(math.sin(i / 3.4)) * (1 - i / 34)) for i in range(21)]
    b += PG(pw + [(228, 50), (28, 50)], "#DCFCE7") + PL(pw, c, 2)
    b += T(10, 18, "power", 7, c, 700, fam=MONO) + PG([(220, 8), (212, 24), (218, 24), (214, 36), (226, 18), (220, 18), (224, 8)], "#F59E0B")
    return b, c, "Gantt schedule of jobs on four servers under a falling power curve"


def vm_qos():
    c = "#4F46E5"
    b = bg("#EEF2FF")
    hosts = [[30, 22, 18], [40, 26], [24, 20, 16, 12]]
    cols = ["#6366F1", "#818CF8", "#A5B4FC", "#C7D2FE"]
    for k, vms in enumerate(hosts):
        x = 16 + k * 58
        b += R(x, 36, 50, 100, "#FFFFFF", 4, stroke="#C7D2FE", stroke_width=1.4) + T(x + 25, 30, f"host {k+1}", 6.5, "#3730A3", 700, "middle", fam=MONO)
        y = 132
        for j, h in enumerate(vms):
            y -= h + 2
            b += R(x + 4, y, 42, h, cols[(k + j) % 4], 2) + T(x + 25, y + h / 2 + 3, "VM", 6, "#FFFFFF", 700, "middle", fam=MONO)
    b += R(196, 18, 32, 22, c, 3, stroke="#312E81", stroke_dasharray="3 2") + T(212, 32, "VM", 7, "#FFFFFF", 700, "middle", fam=MONO)
    b += P("M196 40 Q160 50 150 64", stroke=c, stroke_width=1.6, stroke_dasharray="3 2") + PG([(150, 64), (148, 56), (156, 60)], c)
    b += R(190, 104, 42, 30, "#FFFFFF", 5, stroke="#22C55E") + T(211, 117, "SLA", 8, "#15803D", 800, "middle") + T(211, 128, "met", 6.5, "#15803D", 600, "middle")
    return b, c, "Virtual machines packed into hosts with a new VM being placed and an SLA badge"


def wakeup_bs():
    c = "#0891B2"
    b = lin("dn", [(0, "#0F172A"), (.5, "#1E3A5F"), (1, "#E0F2FE")], 1, 0) + bg("url(#dn)")
    def hexp(cx, cy, r):
        return [(cx + r * math.cos(math.pi / 3 * k + math.pi / 6), cy + r * math.sin(math.pi / 3 * k + math.pi / 6)) for k in range(6)]
    r = 22
    for row in range(4):
        for col in range(7):
            cx = 18 + col * r * 1.732 + (row % 2) * r * .866
            cy = 20 + row * r * 1.5
            on = (cx > 110 and (row + col) % 3 != 0) or (cx <= 110 and (row + col) % 4 == 0)
            b += PG(hexp(cx, cy, r - 1), "#22D3EE" if on else "#334155", opacity=".5" if on else ".55", stroke="#0E7490" if on else "#475569")
            col_ = "#FFFFFF" if on else "#64748B"
            b += L(cx, cy - 4, cx, cy + 9, col_, 1.6) + PG([(cx - 4, cy + 9), (cx + 4, cy + 9), (cx, cy + 3)], col_) + C(cx, cy - 5, 1.8, col_)
            if on:
                for k in (5, 9):
                    b += P(f"M{f(cx-k)} {f(cy-5-k*.6)} q{-k*.5:.1f} {k*.6:.1f} 0 {k*1.2:.1f} M{f(cx+k)} {f(cy-5-k*.6)} q{k*.5:.1f} {k*.6:.1f} 0 {k*1.2:.1f}", stroke=col_, stroke_width=1.1, opacity=".85")
            else:
                b += T(cx + 6, cy - 4, "z", 7, "#94A3B8", 700, fam=MONO) + T(cx + 10, cy - 9, "z", 5, "#94A3B8", 700, fam=MONO)
    b += C(20, 136, 7, "#FEF9C3") + C(23, 134, 6, "#0F172A") + C(222, 136, 8, "#FDE047")
    return b, c, "Hexagonal cells of a cellular network where sleeping base stations dim at night and wake by day"


# ------------------------------------------------------------------ title prefix -> drawing
ART = [
    ("Data2VizWiz", data2vizwiz),
    ("GraphWhisper", graphwhisper),
    ("Can LLM Understand Personal Perspectives", tochi_personal),
    ("VisNoob", visnoob),
    ("Interpreting Latent Variables", latent_dag),
    ("What Catches the Eye", catches_eye),
    ("Making Charts Speak", making_charts_speak),
    ("Every Persona Has Their Palette", persona_palette),
    ("Charts-of-Thought", charts_of_thought),
    ("MisVisFix", misvisfix),
    ("Leveraging Large Language Models for Personalized Public Messaging", chi25_messaging),
    ("Multi-class sentiment classification", bn_sentiment_2023),
    ("CVD", cvd),
    ("HELLO", hello_autism),
    ("Bangla handwritten character and digit", bn_char_digit),
    ("A dynamic strategy for classifying sentiment", word2vec),
    ("State of the Art of ICT based Telemedicine", telemedicine),
    ("CNN based Security issues", ride_driver_cnn),
    ("Bangla handwritten word recognition", bn_word_hw),
    ("Behavioral issues of children", children_internet),
    ("Predicting Retinal Diseases", retinal),
    ("Performance analysis on Bangla handwritten digit", bn_digit_tl),
    ("Sentiment analysis on bengali facebook", fb_celebrity),
    ("Implementation of Recurrent Neural Network with Language Model", articulation),
    ("Bangla hate speech", hate_speech),
    ("Depressed people detection", depression),
    ("Plant disease detection through", plant_diversified),
    ("A Digital Platform Design for Supply Chain", fish_market),
    ("iHealthcare", ihealthcare),
    ("Pregnant women", pregnancy_mood),
    ("The Impact of University Students", smartphone_gpa),
    ("A deep learning approach to predict malnutrition", malnutrition),
    ("Joint cognition", criminal_justice),
    ("A speech recognition system for Bengali", bn_speech),
    ("A Driver-Centric Carpooling", carpool),
    ("An automated system of sentiment analysis", bn_sentiment_supervised),
    ("Bird Species", bird_vgg),
    ("Predicting Crime", crime_map),
    ("Named entity recognition", ner_hmm),
    ("Road accident", road_accident),
    ("A deep learning approach to detect abusive", abusive_text),
    ("PassMan", passman),
    ("Fake news detection", fake_news_chain),
    ("Symptom-based disease", symptom_bn),
    ("Auto-correction of english to bengali", transliteration),
    ("An efficient resource allocation mechanism for time-sensitive data in dew", dew_computing),
    ("Digital Governance for Pension", pension),
    ("A Behavioral Model of Music piracy", music_piracy),
    ("Impact of social media on socialization", social_socialization),
    ("Software piracy", software_piracy),
    ("Security concerns of ridesharing", ride_security),
    ("An unorthodox way of farming", farming_chain),
    ("Automated detection of plant diseases", plant_rcnn),
    ("Bangla word prediction", word_prediction),
    ("Quality of service aware cloud resource provisioning", cloud_multimedia),
    ("Big media healthcare", big_media_health),
    ("Triple-E", triple_e),
    ("Q-MAC", qmac),
    ("Enhancing the capabilities of IoT based fog", iot_fog_cloud),
    ("Interactive interface design for learning numeracy", numeracy_autism),
    ("An Intelligent Smartphone Based Approach Using IoT", safe_driving),
    ("IHEMHA", ihemha),
    ("Quality of service aware reliable task scheduling in vehicular", vehicular_cloud),
    ("Test implementation of a sensor device", soil_sensor),
    ("A QoS and profit aware cloud confederation", confederation),
    ("Energy-efficient scheduling algorithms", energy_sched),
    ("An intelligent approach for virtual machine", vm_qos),
    ("A distributed wake-up scheduling", wakeup_bs),
]


def slug(title):
    s = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return s[:48].rstrip("-")


def main():
    src = open(PUBS, encoding="utf-8").read()
    src = re.sub(r'<div class="pub-thumb"[^>]*>.*?</div>', "", src)
    item_re = re.compile(
        r'(<div class="pub-item" data-year="(\d+)" data-venuetype="\w+" data-status="[\w-]+" data-topic="[^"]+">'
        r'<span class="pub-number">[^<]*</span>)(<div class="pub-content">.*?<h3 class="pub-title">(.*?)</h3>)', re.S)
    used, missing = set(), []

    def repl(m):
        year = m.group(2)
        title = html.unescape(re.sub(r"<[^>]+>", "", m.group(4))).strip()
        fn = next((fn for key, fn in ART if title.lower().startswith(key.lower())), None)
        if fn is None:
            missing.append(title)
            return m.group(0)
        if fn.__name__ in used:
            raise SystemExit(f"drawing reused: {fn.__name__} for {title}")
        used.add(fn.__name__)
        body, accent, alt = fn()
        name = slug(title)
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">'
               f'<title>{html.escape(alt)}</title>{body}</svg>')
        with open(os.path.join(OUT, name + ".svg"), "w", encoding="utf-8") as fh:
            fh.write(svg)
        thumb = (f'<div class="pub-thumb" style="--tc:{accent}"><img src="img/pubs/{name}.svg" '
                 f'alt="{html.escape(alt, quote=True)}" width="{W}" height="{H}" loading="lazy"></div>')
        return m.group(1) + thumb + m.group(3)

    src, n = item_re.subn(repl, src)
    if missing:
        raise SystemExit("no drawing for:\n  " + "\n  ".join(missing))
    unused = [fn.__name__ for _, fn in ART if fn.__name__ not in used]
    if unused:
        print("warning: unused drawings:", unused)
    open(PUBS, "w", encoding="utf-8").write(src)
    print("items:", n, "drawings:", len(used))


if __name__ == "__main__":
    main()
