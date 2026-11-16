"""Generate SVG thumbnails for every publication and insert them into publications.html.

Usage: python gen_thumbs.py <site_root>
Idempotent: existing .pub-thumb blocks are replaced.
"""
import hashlib, html, json, os, random, re, sys

ROOT = sys.argv[1]
PUBS = os.path.join(ROOT, "publications.html")
OUT = os.path.join(ROOT, "img", "pubs")
os.makedirs(OUT, exist_ok=True)

TOPIC_COLOR = {
    "LLM/NLP": "#059669",
    "Visualization": "#7C3AED",
    "Accessibility": "#D97706",
    "ML": "#DC2626",
    "Cloud/IoT": "#2563EB",
}
INK, MUTED, FAINT, LINE = "#334155", "#94A3B8", "#CBD5E1", "#E2E8F0"
FONT = "font-family=\"'IBM Plex Mono',Consolas,monospace\""


def svg(body, label, c):
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 150" width="240" height="150">'
        '<rect width="240" height="150" fill="#F8FAFC"/>'
        + "".join(f'<line x1="0" y1="{y}" x2="240" y2="{y}" stroke="#EEF2F7" stroke-width="1"/>' for y in range(15, 150, 15))
        + body
        + f'<rect x="0" y="0" width="4" height="150" fill="{c}"/>'
        + f'<text x="12" y="142" {FONT} font-size="9.5" fill="#64748B" letter-spacing=".3">{html.escape(label)}</text>'
        + "</svg>"
    )


def rect(x, y, w, h, fill, rx=2, extra=""):
    return f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" fill="{fill}" {extra}/>'


def txt(x, y, s, size=9, fill=INK, extra=""):
    return f'<text x="{x}" y="{y}" {FONT} font-size="{size}" fill="{fill}" {extra}>{html.escape(s)}</text>'


def arrow(x1, y1, x2, y2, col=MUTED, w=1.5):
    return (f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{col}" stroke-width="{w}"/>'
            f'<polygon points="{x2},{y2} {x2-5},{y2-3} {x2-5},{y2+3}" fill="{col}"/>')


# ---------------------------------------------------------------- generic motifs
def m_text(c, r):
    b = ""
    for row in range(4):
        x, y = 14, 22 + row * 22
        while x < 140:
            w = r.uniform(12, 30)
            hi = r.random() < 0.22
            b += rect(x, y, w, 10, c if hi else FAINT, 3, f'opacity="{0.85 if hi else 1}"')
            x += w + 4
    b += arrow(150, 55, 166, 55)
    vals = sorted([r.uniform(.35, 1) for _ in range(3)], reverse=True)
    for i, (v, lab) in enumerate(zip(vals, ["pos", "neu", "neg"])):
        b += txt(172, 32 + i * 22, lab, 8, MUTED)
        b += rect(192, 24 + i * 22, 38 * v, 10, c if i == 0 else FAINT, 2)
    return b, "text classification"


def m_cnn(c, r):
    b = ""
    for i in range(6):
        for j in range(6):
            b += rect(14 + i * 7, 40 + j * 7, 6.5, 6.5, c, 0, f'opacity="{r.uniform(.08, .9):.2f}"')
    sizes = [(64, 34, 48), (98, 28, 40), (128, 22, 32)]
    for x, w, h in sizes:
        for k in range(3):
            b += rect(x + k * 4, 61 - h / 2 + k * 3, w * .55, h, "#FFFFFF", 2, f'stroke="{c}" stroke-width="1" opacity="{.5 + k * .25}"')
    for k in range(5):
        h = r.uniform(8, 30) if k != 2 else 46
        b += rect(176 + k * 10, 92 - h, 7, h, c if k == 2 else FAINT, 1)
    b += f'<line x1="172" y1="92" x2="228" y2="92" stroke="{MUTED}"/>'
    return b, "CNN · image recognition"


def m_rnn(c, r):
    b = ""
    for i in range(5):
        x = 18 + i * 44
        b += rect(x, 50, 30, 26, c, 5, f'opacity="{.35 + i * .15:.2f}"')
        b += f'<circle cx="{x+15}" cy="100" r="6" fill="#FFFFFF" stroke="{MUTED}"/>'
        b += f'<line x1="{x+15}" y1="94" x2="{x+15}" y2="78" stroke="{MUTED}"/>'
        b += f'<line x1="{x+15}" y1="48" x2="{x+15}" y2="32" stroke="{MUTED}"/>'
        b += rect(x + 7, 20, 16, 10, FAINT, 2)
        if i < 4:
            b += arrow(x + 31, 63, x + 42, 63, c, 1.2)
    return b, "sequence model"


def m_wave(c, r):
    b = ""
    for i in range(54):
        a = abs(r.gauss(0, 1)) * 18 * (0.4 + abs(((i % 18) - 9) / 9))
        b += rect(14 + i * 4, 52 - a / 2, 2.5, max(a, 2), c, 1, f'opacity="{.55 + .45 * (i % 3 == 0):.2f}"')
    b += arrow(120, 82, 120, 96)
    x = 30
    while x < 200:
        w = r.uniform(18, 34)
        b += rect(x, 102, w, 10, FAINT, 3)
        x += w + 5
    return b, "speech recognition"


def m_network(c, r):
    b = (f'<path d="M92 48 a16 16 0 0 1 28 -12 a20 20 0 0 1 36 6 a14 14 0 0 1 2 28 h-62 a12 12 0 0 1 -4 -22z" '
         f'fill="{c}" opacity=".14" stroke="{c}" stroke-width="1.4"/>')
    hub = (125, 55)
    nodes = [(r.uniform(18, 222), r.uniform(92, 120)) for _ in range(7)]
    nodes.sort()
    for i, (x, y) in enumerate(nodes):
        b += f'<line x1="{hub[0]}" y1="{hub[1]+15}" x2="{x:.1f}" y2="{y:.1f}" stroke="{c}" stroke-opacity=".35"/>'
        if i:
            b += f'<line x1="{nodes[i-1][0]:.1f}" y1="{nodes[i-1][1]:.1f}" x2="{x:.1f}" y2="{y:.1f}" stroke="{FAINT}"/>'
    for i, (x, y) in enumerate(nodes):
        b += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="{c if i % 3 == 0 else "#FFFFFF"}" stroke="{c}" stroke-width="1.3"/>'
    for i in range(3):
        b += rect(20 + i * 8, 22 + i * 0, 6, 26 - i * 6, c, 1, f'opacity="{.3 + i * .25}"')
        b += rect(196 + i * 8, 22, 6, 12 + i * 7, c, 1, f'opacity="{.3 + i * .25}"')
    return b, "cloud · networks · IoT"


def m_survey(c, r):
    cols = ["#94A3B8", "#CBD5E1", "#E2E8F0", c + "88", c]
    b = f'<line x1="120" y1="14" x2="120" y2="124" stroke="{MUTED}" stroke-dasharray="2 2"/>'
    for row in range(5):
        p = [r.uniform(.05, .3) for _ in range(5)]
        s = sum(p)
        p = [v / s * 190 for v in p]
        start = 120 - (p[0] + p[1] + p[2] / 2)
        x = start
        for k in range(5):
            b += rect(x, 20 + row * 21, p[k], 13, cols[k], 0)
            x += p[k]
    return b, "survey study"


def m_scatter(c, r):
    b = f'<line x1="20" y1="122" x2="228" y2="122" stroke="{MUTED}"/><line x1="20" y1="14" x2="20" y2="122" stroke="{MUTED}"/>'
    a, k = r.uniform(.3, .6), r.uniform(-20, 20)
    for _ in range(34):
        x, y = r.uniform(26, 224), r.uniform(18, 116)
        above = y < 118 - (x - 20) * a + k
        if above:
            b += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.2" fill="{c}" opacity=".85"/>'
        else:
            b += rect(x - 3, y - 3, 6, 6, MUTED, 1, 'opacity=".8"')
    b += (f'<path d="M20 {118+k:.1f} C 90 {118+k-60*a:.1f}, 150 {118+k-110*a:.1f}, 228 {118+k-208*a:.1f}" '
          f'fill="none" stroke="{INK}" stroke-width="1.3" stroke-dasharray="5 3"/>')
    return b, "predictive modeling"


def m_route(c, r):
    b = ""
    for x in range(24, 230, 28):
        b += f'<line x1="{x}" y1="12" x2="{x}" y2="124" stroke="{LINE}" stroke-width="3"/>'
    for y in range(18, 124, 26):
        b += f'<line x1="12" y1="{y}" x2="232" y2="{y}" stroke="{LINE}" stroke-width="3"/>'
    pts = [(24, 122), (52, 122), (52, 70), (108, 70), (108, 44), (164, 44), (164, 18), (220, 18)]
    b += '<polyline points="' + " ".join(f"{x},{y}" for x, y in pts) + f'" fill="none" stroke="{c}" stroke-width="4" stroke-linejoin="round"/>'
    for x, y in [pts[0], pts[3], pts[5], pts[-1]]:
        b += f'<circle cx="{x}" cy="{y}" r="5.5" fill="#FFFFFF" stroke="{c}" stroke-width="2"/>'
    return b, "route optimization"


def m_chain(c, r):
    b = ""
    for i in range(4):
        x = 14 + i * 56
        b += rect(x, 40, 42, 50, "#FFFFFF", 4, f'stroke="{c}" stroke-width="1.4"')
        b += rect(x, 40, 42, 12, c, 4, f'opacity="{.3 + i * .2:.2f}"')
        for k in range(3):
            b += rect(x + 6, 58 + k * 9, r.uniform(16, 30), 4, FAINT, 1)
        if i < 3:
            b += f'<ellipse cx="{x+49}" cy="65" rx="8" ry="4" fill="none" stroke="{MUTED}" stroke-width="2"/>'
    return b, "blockchain"


def m_security(c, r):
    b = ""
    for k in range(8):
        w = r.uniform(30, 110)
        hi = k == 4
        b += rect(14 + (k % 3) * 8, 16 + k * 13, w, 7, c if hi else FAINT, 2, f'opacity="{.85 if hi else 1}"')
    b += (f'<path d="M180 22 l32 12 v26 c0 22 -14 36 -32 44 c-18 -8 -32 -22 -32 -44 v-26z" fill="{c}" opacity=".15" stroke="{c}" stroke-width="1.6"/>'
          f'<rect x="170" y="58" width="20" height="16" rx="2" fill="{c}"/>'
          f'<path d="M174 58 v-6 a6 6 0 0 1 12 0 v6" fill="none" stroke="{c}" stroke-width="2.2"/>')
    return b, "security"


def m_health(c, r):
    pts, x = [], 14
    while x < 226:
        if r.random() < .18:
            pts += [(x, 70), (x + 4, 40), (x + 8, 98), (x + 12, 62), (x + 16, 70)]
            x += 20
        else:
            pts.append((x, 70 + r.uniform(-3, 3)))
            x += 8
    b = '<polyline points="' + " ".join(f"{a:.1f},{bb:.1f}" for a, bb in pts) + f'" fill="none" stroke="{c}" stroke-width="2"/>'
    b += (f'<path d="M206 24 c-6 -8 -18 -2 -14 8 l14 12 l14 -12 c4 -10 -8 -16 -14 -8z" fill="{c}" opacity=".8"/>')
    for k in range(6):
        h = r.uniform(6, 22)
        b += rect(16 + k * 9, 124 - h, 6, h, FAINT, 1)
    return b, "health informatics"


def m_app(c, r):
    b = rect(84, 10, 72, 122, "#FFFFFF", 10, f'stroke="{INK}" stroke-width="1.5"')
    b += rect(92, 22, 56, 26, c, 4, 'opacity=".25"')
    for k in range(2):
        for j in range(2):
            b += rect(92 + j * 30, 54 + k * 30, 26, 24, c if (k + j) % 2 == 0 else FAINT, 4, f'opacity="{.8 if (k+j)%2==0 else 1}"')
    b += rect(108, 118, 24, 4, FAINT, 2)
    for x, y, s in [(30, 40, 10), (52, 96, 7), (196, 34, 8), (206, 92, 11)]:
        b += f'<circle cx="{x}" cy="{y}" r="{s}" fill="{c}" opacity=".18"/>'
    return b, "mobile app · interface"


RULES = [
    (m_chain, ["blockchain"]),
    (m_security, ["vulnerability", "password", "security"]),
    (m_text, ["sentiment", "hate speech", "abusive", "depressed", "named entity", "transliteration", "emotions towards"]),
    (m_wave, ["speech recognition", "articulation"]),
    (m_cnn, ["handwritten", "plant disease", "retinal", "bird", "r-cnn"]),
    (m_rnn, ["gru", "word prediction"]),
    (m_app, ["autism", "android", "numeracy", "pension", "digital platform"]),
    (m_survey, ["behavioral", "piracy", "impact of", "socialization", "pregnant", "internet usage"]),
    (m_network, ["cloud", "iot", "dew computing", "vehicular", "cellular", "sensor", "data center", "virtual machine", "offloading", "pool management"]),
    (m_health, ["health", "telemedicine", "symptom", "emotion computing"]),
    (m_route, ["carpool", "route"]),
    (m_scatter, []),
]


# ---------------------------------------------------------------- bespoke (recent, first-authored)
def b_charts_of_thought(c):
    b = ""
    for k, h in enumerate([30, 52, 22, 44]):
        b += rect(16 + k * 13, 86 - h, 9, h, MUTED, 1)
    b += f'<line x1="12" y1="86" x2="70" y2="86" stroke="{MUTED}"/>'
    b += arrow(74, 62, 88, 62)
    for k in range(4):
        b += rect(92, 34 + k * 12, 18, 9, FAINT, 1) + rect(112, 34 + k * 12, 20, 9, c, 1, 'opacity=".35"')
    b += arrow(136, 62, 148, 62)
    b += txt(152, 20, "VLAT score", 8, MUTED)
    b += rect(152, 30, 80 * 28.82 / 55, 14, FAINT, 2) + txt(154, 41, "human 28.8", 8, INK)
    b += rect(152, 52, 80 * 50.17 / 55, 14, c, 2) + txt(154, 63, "CoT 50.2", 8, "#FFFFFF", 'font-weight="700"')
    b += txt(16, 112, "chart → table → reasoning", 8.5, INK)
    return b, "IEEE TVCG · VIS 2025"


def b_misvisfix(c):
    bad, good = "#DC2626", "#059669"
    b = txt(14, 18, "truncated axis", 8, bad)
    for k, h in enumerate([20, 62, 38]):
        b += rect(18 + k * 22, 96 - h, 16, h, bad, 1, 'opacity=".75"')
    b += f'<line x1="14" y1="96" x2="88" y2="96" stroke="{MUTED}"/>'
    b += f'<path d="M14 96 l4 -3 l4 3 l4 -3" fill="none" stroke="{bad}" stroke-width="1.5"/>'
    b += f'<polygon points="92,26 106,50 78,50" fill="#FEF3C7" stroke="#D97706"/>' + txt(89, 47, "!", 12, "#D97706", 'font-weight="700"')
    b += arrow(112, 64, 134, 64, c, 2)
    b += txt(144, 18, "corrected", 8, good)
    for k, h in enumerate([56, 66, 60]):
        b += rect(148 + k * 24, 96 - h, 18, h, good, 1, 'opacity=".75"')
    b += f'<line x1="144" y1="96" x2="226" y2="96" stroke="{MUTED}"/>'
    b += txt(16, 116, "detect · explain · correct", 8.5, INK)
    return b, "IEEE TVCG · VIS 2025"


def b_graphwhisper(c, label="accessible chart Q&A"):
    pts = [(16, 96), (40, 80), (64, 86), (88, 54), (112, 60), (136, 30)]
    b = f'<line x1="14" y1="104" x2="140" y2="104" stroke="{MUTED}"/>'
    b += '<polyline points="' + " ".join(f"{x},{y}" for x, y in pts) + f'" fill="none" stroke="{MUTED}" stroke-width="2"/>'
    for x, y in pts:
        b += f'<circle cx="{x}" cy="{y}" r="3" fill="{MUTED}"/>'
    b += rect(150, 18, 80, 24, "#FFFFFF", 8, f'stroke="{MUTED}"') + txt(156, 34, "When did it peak?", 7, INK)
    b += rect(150, 52, 80, 34, c, 8, 'opacity=".9"') + txt(156, 66, "In 2025, at its", 7, "#FFFFFF") + txt(156, 77, "highest value.", 7, "#FFFFFF")
    for k in range(3):
        b += f'<path d="M{150 + k*7} 104 a{6+k*5} {6+k*5} 0 0 1 0 {-1}" fill="none"/>'
    b += (f'<path d="M156 104 q6 -8 0 -16 M164 108 q10 -12 0 -24 M172 112 q14 -16 0 -32" fill="none" stroke="{c}" stroke-width="1.6" opacity=".7" transform="translate(30,-2)"/>'
          f'<rect x="168" y="94" width="10" height="12" rx="2" fill="{c}"/>')
    return b, label


def b_making_charts_speak(c):
    b, _ = b_graphwhisper(c)
    return b, "CHI 2026 · accessibility"


def b_persona_palette(c):
    pal = ["#DC2626", "#2563EB", "#059669", "#D97706", "#7C3AED"]
    b = ""
    rows = [(14, 16, 150, 0), (76, 50, 150, 1), (14, 84, 130, 2)]
    for x, y, w, k in rows:
        b += rect(x, y, w, 26, "#FFFFFF", 9, f'stroke="{LINE}"')
        xx = x + 8
        rr = random.Random(k)
        while xx < x + w - 20:
            ww = rr.uniform(12, 26)
            hi = rr.random() < .35
            b += rect(xx, y + 9, ww, 8, pal[(k + int(xx)) % 5] if hi else FAINT, 2)
            xx += ww + 4
    for k, col in enumerate(pal):
        b += f'<circle cx="{200 + (k % 2) * 16}" cy="{24 + k * 18}" r="6" fill="{col}"/>'
    b += txt(188, 120, "Big Five", 7.5, MUTED)
    return b, "CHI 2026 · persona colors"


def b_personalized_messaging(c, label="LLM × conjoint"):
    traits = ["O", "C", "E", "A", "N"]
    r = random.Random(7)
    b = txt(14, 18, "message", 7.5, MUTED)
    for j in range(5):
        b += txt(62 + j * 16, 18, traits[j], 8, INK, 'font-weight="700"')
    for i in range(5):
        b += rect(14, 26 + i * 18, 40, 12, FAINT, 2)
        for j in range(5):
            b += rect(58 + j * 16, 26 + i * 18, 14, 14, c, 2, f'opacity="{r.uniform(.1, 1):.2f}"')
    b += arrow(146, 66, 162, 66)
    b += txt(168, 30, "2,040", 12, c, 'font-weight="700"') + txt(168, 42, "participants", 7, MUTED)
    b += txt(168, 70, "−99%", 12, c, 'font-weight="700"') + txt(168, 82, "survey cost", 7, MUTED)
    return b, label


def b_visnoob(c):
    b = (f'<circle cx="52" cy="64" r="38" fill="{FAINT}"/>'
         f'<path d="M52 64 L52 26 A38 38 0 0 1 88 76 z" fill="#DC2626" opacity=".7"/>'
         f'<path d="M52 64 L88 76 A38 38 0 0 1 30 95 z" fill="#94A3B8"/>')
    b += txt(22, 118, "130%?", 9, "#DC2626", 'font-weight="700"')
    b += arrow(100, 64, 124, 64, c, 2)
    for k, (lab, w) in enumerate([("A", 80), ("B", 56), ("C", 34), ("D", 20)]):
        b += txt(132, 34 + k * 20, lab, 8, INK) + rect(142, 25 + k * 20, w, 12, c, 2, f'opacity="{1 - k * .18:.2f}"')
    b += f'<circle cx="222" cy="116" r="9" fill="#059669"/><path d="M217 116 l4 4 l7 -8" fill="none" stroke="#FFF" stroke-width="2"/>'
    return b, "guided fixing for novices"


def b_data2vizwiz(c):
    b = ""
    for k, h in enumerate([40, 52, 30, 46]):
        b += rect(16 + k * 16, 96 - h, 12, h, MUTED, 1)
    b += f'<line x1="12" y1="96" x2="80" y2="96" stroke="{MUTED}"/>' + txt(14, 112, "default", 8, MUTED)
    b += arrow(88, 62, 116, 62, c, 2)
    b += f'<path d="M100 44 l2 5 l5 2 l-5 2 l-2 5 l-2 -5 l-5 -2 l5 -2z" fill="{c}"/>'
    for k, (y1, y2) in enumerate([(40, 70), (62, 34), (84, 88), (50, 58)]):
        col = c if y2 < y1 - 10 or y2 > y1 + 10 else MUTED
        b += f'<line x1="140" y1="{y1}" x2="214" y2="{y2}" stroke="{col}" stroke-width="2"/>'
        b += f'<circle cx="140" cy="{y1}" r="3.5" fill="{col}"/><circle cx="214" cy="{y2}" r="3.5" fill="{col}"/>'
    b += txt(134, 112, "recommended", 8, c)
    return b, "LLM chart recommendation"


def b_latent_dag(c):
    nodes = {"X": (34, 90), "Y": (206, 90), "M": (120, 104), "U": (120, 34)}
    b = ""
    for a, z in [("X", "M"), ("M", "Y"), ("X", "Y")]:
        (x1, y1), (x2, y2) = nodes[a], nodes[z]
        b += f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{MUTED}" stroke-width="1.6"/>'
    for z in ["X", "Y"]:
        (x1, y1), (x2, y2) = nodes["U"], nodes[z]
        b += f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{c}" stroke-width="1.6" stroke-dasharray="4 3"/>'
    for k, (x, y) in nodes.items():
        lat = k == "U"
        b += f'<circle cx="{x}" cy="{y}" r="13" fill="{"#FFFFFF" if lat else c}" fill-opacity="{1 if lat else .85}" stroke="{c}" stroke-width="1.6" {"stroke-dasharray=\"3 2\"" if lat else ""}/>'
        b += txt(x - 4, y + 4, k, 10, c if lat else "#FFFFFF", 'font-weight="700"')
    b += txt(140, 30, "latent", 8, c)
    return b, "EuroVA 2026 · causal DAGs"


def b_catches_eye(c):
    b = rect(16, 14, 120, 112, "#FFFFFF", 4, f'stroke="{LINE}"')
    b += rect(24, 22, 104, 14, FAINT, 2) + rect(24, 42, 48, 40, c, 3, 'opacity=".25"') + rect(78, 42, 50, 18, FAINT, 2)
    b += rect(78, 64, 50, 18, FAINT, 2) + rect(24, 88, 104, 30, FAINT, 2)
    b += f'<circle cx="48" cy="62" r="22" fill="{c}" opacity=".22"/><circle cx="48" cy="62" r="11" fill="{c}" opacity=".35"/>'
    b += f'<circle cx="104" cy="28" r="14" fill="{c}" opacity=".18"/>'
    b += f'<path d="M156 66 q30 -28 60 0 q-30 28 -60 0z" fill="#FFFFFF" stroke="{INK}" stroke-width="1.5"/><circle cx="186" cy="66" r="9" fill="{c}"/><circle cx="186" cy="66" r="3.5" fill="{INK}"/>'
    b += txt(156, 104, "conjoint", 8, MUTED)
    return b, "EuroVis 2026 · poster"


BESPOKE = [
    ("Charts-of-Thought", b_charts_of_thought),
    ("MisVisFix", b_misvisfix),
    ("GraphWhisper", lambda c: b_graphwhisper(c, "TVCG (review) · BLV users")),
    ("Making Charts Speak", b_making_charts_speak),
    ("Every Persona Has Their Palette", b_persona_palette),
    ("Can LLM Understand Personal Perspectives", lambda c: b_personalized_messaging(c, "TOCHI (review) · LLM × conjoint")),
    ("Leveraging Large Language Models for Personalized Public Messaging", lambda c: b_personalized_messaging(c, "CHI 2025 · LLM × conjoint")),
    ("VisNoob", b_visnoob),
    ("Data2VizWiz", b_data2vizwiz),
    ("Interpreting Latent Variables", b_latent_dag),
    ("What Catches the Eye", b_catches_eye),
]

# Reclassify venue types to match the CV (TVCG journal papers; workshop/EA/poster).
RETYPE = {
    "Charts-of-Thought": "journal",
    "MisVisFix": "journal",
    "Making Charts Speak": "workshop",
    "Every Persona Has Their Palette": "workshop",
    "Interpreting Latent Variables": "workshop",
    "What Catches the Eye": "workshop",
    "Leveraging Large Language Models for Personalized Public Messaging": "workshop",
}


def slug(title):
    s = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return s[:48].rstrip("-")


src = open(PUBS, encoding="utf-8").read()
src = re.sub(r'<div class="pub-thumb"[^>]*>.*?</div>', "", src)

item_re = re.compile(
    r'(<div class="pub-item" data-year="(\d+)" data-venuetype=")(\w+)(" data-status="([\w-]+)" data-topic="([^"]+)">'
    r'<span class="pub-number">[^<]*</span>)(<div class="pub-content">.*?<h3 class="pub-title">(.*?)</h3>)', re.S)

report, used = [], set()


def repl(m):
    year, vtype, status, topic = m.group(2), m.group(3), m.group(5), m.group(6)
    title = html.unescape(re.sub(r"<[^>]+>", "", m.group(8))).strip()
    c = TOPIC_COLOR.get(topic, "#0891B2")
    for key, t in RETYPE.items():
        if title.startswith(key) and status == "published":
            vtype = t
    fn = None
    for key, f in BESPOKE:
        if title.startswith(key) and (status == "under-review") == (key in ("GraphWhisper", "Can LLM Understand Personal Perspectives", "VisNoob", "Data2VizWiz")):
            fn = f
    if fn:
        body, label = fn(c)
        kind = "bespoke"
    else:
        low = title.lower()
        for f, kws in RULES:
            if not kws or any(k in low for k in kws):
                break
        r = random.Random(hashlib.md5(title.encode()).hexdigest())
        body, label = f(c, r)
        kind = f.__name__
    name = slug(title)
    if name in used:
        name += "-" + year
    used.add(name)
    with open(os.path.join(OUT, name + ".svg"), "w", encoding="utf-8") as fh:
        fh.write(svg(body, label, c))
    report.append((year, kind, topic, title[:70]))
    alt = html.escape(f"Illustration: {label}", quote=True)
    thumb = (f'<div class="pub-thumb" style="--tc:{c}"><img src="img/pubs/{name}.svg" alt="{alt}" '
             f'width="240" height="150" loading="lazy"></div>')
    return m.group(1) + vtype + m.group(4) + thumb + m.group(7)


src, n = item_re.subn(repl, src)

# TVCG venue/tag fixes for the two VIS 2025 papers
src = src.replace(
    '<span class="pub-venue-tag">IEEE VIS\'25</span>',
    '<span class="pub-venue-tag journal">TVCG &middot; VIS\'25</span>')
src = src.replace(
    "In Proceedings of the IEEE Visualization Conference (IEEE VIS), 2025. (Accepted)",
    "IEEE Transactions on Visualization and Computer Graphics (TVCG), vol. 32, no. 1, 2026 &middot; Presented at IEEE VIS 2025")

open(PUBS, "w", encoding="utf-8").write(src)
for row in report:
    print(*row, sep=" | ")
print("items:", n)
