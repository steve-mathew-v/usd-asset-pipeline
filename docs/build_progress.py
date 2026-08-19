"""Generate the 'planned vs delivered' progress presentation deck."""

import os

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

NAVY = "1E293B"
ACCENT = "0E7490"
ACCENT_LT = "22D3EE"
GREEN = "15803D"
AMBER = "B45309"
GREY = "64748B"
SLATE = "475569"
SLATE_LT = "94A3B8"
LIGHT = "F1F5F9"
LINE = "CBD5E1"
WHITE = "FFFFFF"
INK = "1E293B"

HEAD = "Georgia"
BODY = "Calibri"
MONO = "Consolas"

HERE = os.path.dirname(os.path.abspath(__file__))

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
BLANK = prs.slide_layouts[6]
_num = [0]


def rgb(h):
    return RGBColor.from_string(h)


def slide(bg=WHITE):
    _num[0] += 1
    s = prs.slides.add_slide(BLANK)
    r = s.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), prs.slide_width, prs.slide_height
    )
    r.fill.solid()
    r.fill.fore_color.rgb = rgb(bg)
    r.line.fill.background()
    r.shadow.inherit = False
    return s


def box(s, x, y, w, h, fill=None, line=None, radius=False):
    shp = s.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE,
        Inches(x), Inches(y), Inches(w), Inches(h),
    )
    if fill:
        shp.fill.solid()
        shp.fill.fore_color.rgb = rgb(fill)
    else:
        shp.fill.background()
    if line:
        shp.line.color.rgb = rgb(line)
    else:
        shp.line.fill.background()
    shp.shadow.inherit = False
    return shp


def text(s, runs, x, y, w, h, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, gap=4):
    tb = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    for m in ("margin_left", "margin_right", "margin_top", "margin_bottom"):
        setattr(tf, m, 0)
    if isinstance(runs[0], tuple):
        runs = [runs]
    for i, para in enumerate(runs):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.space_after = Pt(gap)
        p.space_before = Pt(0)
        for txt, o in para:
            run = p.add_run()
            run.text = txt
            run.font.name = o.get("font", BODY)
            run.font.size = Pt(o.get("size", 16))
            run.font.bold = o.get("bold", False)
            run.font.italic = o.get("italic", False)
            run.font.color.rgb = rgb(o.get("color", INK))
            if "spacing" in o:
                run._r.get_or_add_rPr().set("spc", str(int(o["spacing"] * 100)))
    return tb


def bullets(s, items, x, y, w, h, size=15, color=INK, gap=10, marker=ACCENT):
    tb = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    for m in ("margin_left", "margin_right", "margin_top", "margin_bottom"):
        setattr(tf, m, 0)
    for i, item in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(gap)
        p.space_before = Pt(0)
        mk = p.add_run()
        mk.text = "•  "
        mk.font.name = BODY
        mk.font.size = Pt(size)
        mk.font.bold = True
        mk.font.color.rgb = rgb(marker)
        run = p.add_run()
        run.text = item
        run.font.name = BODY
        run.font.size = Pt(size)
        run.font.color.rgb = rgb(color)
    return tb


def header(s, kick, title):
    text(s, [[(kick.upper(), {"font": MONO, "size": 12, "bold": True,
                              "color": ACCENT, "spacing": 2})]], 0.9, 0.55, 11, 0.3)
    text(s, [[(title, {"font": HEAD, "size": 29, "bold": True, "color": INK})]],
         0.9, 0.9, 11.6, 0.8)


def footer(s):
    text(s, [[("USD Asset Pipeline — Progress", {"size": 10, "color": SLATE_LT})]],
         0.9, 7.05, 7, 0.3)
    text(s, [[(str(_num[0]), {"size": 10, "color": SLATE_LT})]],
         12.0, 7.05, 0.8, 0.3, align=PP_ALIGN.RIGHT)


def chip(s, x, y, label, color):
    w = 1.7
    box(s, x, y, w, 0.42, fill=color, radius=True)
    text(s, [[(label, {"size": 11, "bold": True, "color": WHITE})]],
         x, y, w, 0.42, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)


# ---------------------------------------------------------------- 1: title
s = slide(NAVY)
box(s, 0.9, 2.4, 0.14, 2.3, fill=ACCENT_LT)
text(s, [[("MSc PROJECT — FINAL PRESENTATION", {"font": MONO, "size": 13,
          "bold": True, "color": ACCENT_LT, "spacing": 2})]], 1.3, 2.45, 11, 0.4)
text(s, [
    [("Planned vs Delivered", {"font": HEAD, "size": 42, "bold": True, "color": WHITE})],
    [("A USD Asset Pipeline for Cross-DCC Collaboration",
      {"font": HEAD, "size": 22, "bold": True, "color": SLATE_LT})],
], 1.3, 3.0, 11.4, 1.8, gap=6)
text(s, [[("Steve Mathew Varghese  ·  NCCA, Bournemouth University",
           {"size": 14, "color": SLATE_LT})]], 1.3, 5.1, 11, 0.4)

# ---------------------------------------------------------------- 2: the plan
s = slide(WHITE)
header(s, "What was proposed", "The plan")
text(s, [[("Research question:  ", {"size": 15, "bold": True, "color": ACCENT}),
          ("Can a lightweight, USD-based system give small teams reliable, "
           "versioned, cross-DCC asset exchange — and improve on manual "
           "file-sharing?", {"size": 15, "color": INK})]], 0.9, 1.8, 11.5, 1.0)
text(s, [[("Six objectives were set:", {"size": 14, "bold": True, "color": SLATE})]],
     0.9, 3.0, 11, 0.3)
bullets(s, [
    "Review existing asset pipelines and identify the gap",
    "Build a server with versioned storage and an approved state",
    "USD publish / consume in two DCCs (Maya + Houdini)",
    "Consume the latest approved version, or a pinned one",
    "Evaluate with artists (task study + SUS + comparison)",
    "Deploy properly (Docker, CI, reproducible environment)",
], 0.9, 3.45, 11.5, 3.2, size=15, gap=9)
footer(s)

# ---------------------------------------------------------------- 3: planned vs delivered
s = slide(WHITE)
header(s, "Progress", "Planned vs delivered")
text(s, [[("The tool is complete; four of six objectives are fully delivered "
           "and the evaluation is underway.", {"size": 15, "italic": True,
           "color": SLATE})]], 0.9, 1.75, 11.6, 0.6)

rows = [
    ("Review existing pipelines", "IN PROGRESS", AMBER),
    ("Versioned server + approved state", "DELIVERED", GREEN),
    ("USD publish / consume in Maya + Houdini", "DELIVERED", GREEN),
    ("Latest-approved or pinned version", "DELIVERED", GREEN),
    ("Evaluate with artists (SUS + tasks)", "IN PROGRESS", AMBER),
    ("Deploy (Docker, CI, cloud)", "DELIVERED", GREEN),
]
y = 2.5
for label, status, color in rows:
    box(s, 0.9, y, 8.6, 0.62, fill=LIGHT, radius=True)
    text(s, [[(label, {"size": 14.5, "bold": True, "color": INK})]],
         1.2, y, 8.0, 0.62, anchor=MSO_ANCHOR.MIDDLE)
    chip(s, 9.75, y + 0.1, status, color)
    y += 0.74
footer(s)

# ---------------------------------------------------------------- 4: what was delivered
s = slide(WHITE)
header(s, "Delivered", "The working system")
box(s, 0.9, 1.85, 5.7, 4.7, fill=LIGHT, radius=True)
text(s, [[("PIPELINE", {"font": MONO, "size": 12, "bold": True, "color": ACCENT,
           "spacing": 2})]], 1.25, 2.15, 5, 0.3)
bullets(s, [
    "USD assets (.usd / .usda / .usdc / .usdz)",
    "Full version history — approve latest or pin a version",
    "Maya client (tested end-to-end) + Houdini client",
    "PySide6 management GUI (server, users, assets)",
    "Automatic front/top thumbnails on publish",
], 1.25, 2.6, 5.1, 3.8, size=14.5, gap=12)

box(s, 6.9, 1.85, 5.5, 4.7, fill=NAVY, radius=True)
text(s, [[("ENGINEERING", {"font": MONO, "size": 12, "bold": True,
           "color": ACCENT_LT, "spacing": 2})]], 7.25, 2.15, 5, 0.3)
bullets(s, [
    "FastAPI + MongoDB Atlas, files in GridFS",
    "Deployed on Render — always-on cloud URL",
    "Authentication + per-user accounts",
    "15 automated tests + GitHub Actions CI",
    "Docker, uv, PEP 8 enforced",
], 7.25, 2.6, 4.9, 3.8, size=14.5, color="E2E8F0", marker=ACCENT_LT, gap=12)
footer(s)

# ---------------------------------------------------------------- 5: evaluation
s = slide(WHITE)
header(s, "Evaluation", "Planned and current status")
box(s, 0.9, 1.9, 5.7, 4.3, fill=LIGHT, radius=True)
text(s, [[("PLANNED", {"font": MONO, "size": 12, "bold": True, "color": SLATE,
           "spacing": 2})]], 1.25, 2.2, 5, 0.3)
bullets(s, [
    "Task-based usability study with artists",
    "System Usability Scale (SUS) questionnaire",
    "Comparison against manual file-sharing",
    "Consent, background and post-study forms",
], 1.25, 2.65, 5.1, 3.3, size=14.5, color=INK, marker=SLATE, gap=12)

box(s, 6.9, 1.9, 5.5, 4.3, fill=LIGHT, radius=True)
text(s, [[("DONE SO FAR", {"font": MONO, "size": 12, "bold": True,
           "color": GREEN, "spacing": 2})]], 7.25, 2.2, 5, 0.3)
bullets(s, [
    "Full evaluation pack built (forms + task sheet)",
    "Participant responses collected",
    "Analysis and write-up in progress",
], 7.25, 2.65, 4.9, 2.6, size=14.5, color=INK, marker=GREEN, gap=12)
text(s, [[("SUS results collected — analysis underway.",
           {"size": 13, "italic": True, "color": SLATE})]], 7.25, 5.5, 4.9, 0.5)
footer(s)

# ---------------------------------------------------------------- 6: timeline
s = slide(WHITE)
header(s, "Timeline", "Where things stand")
phases = [
    ("Review & scope", "DELIVERED", GREEN),
    ("Server + versioning", "DELIVERED", GREEN),
    ("Maya + Houdini clients", "DELIVERED", GREEN),
    ("Cloud deployment", "DELIVERED", GREEN),
    ("User study — data collection", "DELIVERED", GREEN),
    ("Analysis & dissertation write-up", "IN PROGRESS", AMBER),
]
y = 2.0
for label, status, color in phases:
    box(s, 0.9, y, 8.6, 0.6, fill=LIGHT, radius=True)
    text(s, [[(label, {"size": 14.5, "bold": True, "color": INK})]],
         1.2, y, 8.0, 0.6, anchor=MSO_ANCHOR.MIDDLE)
    chip(s, 9.75, y + 0.09, status, color)
    y += 0.72
text(s, [[("Development finished ahead of plan; the remaining work is analysis "
           "and writing.", {"size": 14, "italic": True, "color": SLATE})]],
     0.9, 6.5, 11.5, 0.5)
footer(s)

# ---------------------------------------------------------------- 7: remaining / future
s = slide(WHITE)
header(s, "What's left", "Remaining and future work")
box(s, 0.9, 1.9, 5.7, 4.3, fill=LIGHT, radius=True)
text(s, [[("TO FINISH (THIS PROJECT)", {"font": MONO, "size": 12, "bold": True,
           "color": AMBER, "spacing": 2})]], 1.25, 2.2, 5, 0.3)
bullets(s, [
    "Analyse the SUS and task results",
    "Complete the literature review",
    "Write up findings and conclusions",
], 1.25, 2.65, 5.1, 2.6, size=14.5, color=INK, marker=AMBER, gap=12)

box(s, 6.9, 1.9, 5.5, 4.3, fill=LIGHT, radius=True)
text(s, [[("FUTURE WORK", {"font": MONO, "size": 12, "bold": True,
           "color": GREY, "spacing": 2})]], 7.25, 2.2, 5, 0.3)
bullets(s, [
    "Full USD composition + custom Ar resolver",
    "Substance / texture round-trip",
    "Search, tags and batch operations",
    "Larger, controlled A/B user study",
], 7.25, 2.65, 4.9, 3.3, size=14.5, color=INK, marker=GREY, gap=12)
footer(s)

# ---------------------------------------------------------------- 8: summary
s = slide(NAVY)
text(s, [[("SUMMARY", {"font": MONO, "size": 12, "bold": True,
           "color": ACCENT_LT, "spacing": 2})]], 0.9, 0.8, 11, 0.3)
text(s, [[("A working, deployed pipeline — evaluation underway",
           {"font": HEAD, "size": 30, "bold": True, "color": WHITE})]],
     0.9, 1.2, 11.5, 0.9)
bullets(s, [
    "Delivered a versioned, USD, cross-DCC asset pipeline (Maya + Houdini)",
    "Cloud-hosted, tested, and usable by a small team today",
    "Evaluation instruments built and responses collected",
    "Remaining: analysis and the written dissertation",
], 0.9, 2.5, 11.5, 2.6, size=17, color="E2E8F0", marker=ACCENT_LT, gap=14)
box(s, 0.9, 5.5, 11.5, 0.02, fill=SLATE)
text(s, [[("Contribution:  ", {"size": 14, "bold": True, "color": ACCENT_LT}),
          ("a lightweight, self-hostable USD pipeline with real version "
           "control for small studios.", {"size": 14, "color": SLATE_LT})]],
     0.9, 5.75, 11.5, 0.6)
text(s, [[("Thank you", {"font": HEAD, "size": 18, "bold": True, "color": WHITE})]],
     0.9, 6.5, 11, 0.5)

prs.save(os.path.join(HERE, "Progress_Presentation.pptx"))
print("saved Progress_Presentation.pptx with", len(prs.slides._sldIdLst), "slides")
