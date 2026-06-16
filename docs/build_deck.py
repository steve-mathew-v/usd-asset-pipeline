"""Generate the MSc proposal presentation deck."""

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.oxml.ns import qn

# palette
NAVY = "0E1628"
NAVY2 = "1A2540"
TEAL = "14B8A6"
TEAL_LT = "2DD4BF"
AMBER = "F59E0B"
SLATE = "64748B"
SLATE_LT = "94A3B8"
LIGHT = "F1F5F9"
WHITE = "FFFFFF"
INK = "0F172A"
LINE = "E2E8F0"

HEAD = "Georgia"
BODY = "Calibri"
MONO = "Consolas"

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
BLANK = prs.slide_layouts[6]
EMU_W, EMU_H = 13.333, 7.5


def rgb(h):
    return RGBColor.from_string(h)


def slide(bg=WHITE):
    s = prs.slides.add_slide(BLANK)
    r = s.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), prs.slide_width, prs.slide_height
    )
    r.fill.solid()
    r.fill.fore_color.rgb = rgb(bg)
    r.line.fill.background()
    r.shadow.inherit = False
    return s


def box(s, x, y, w, h, fill=None, line=None, line_w=1.0, radius=False, shadow=False):
    shp = s.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE,
        Inches(x),
        Inches(y),
        Inches(w),
        Inches(h),
    )
    if fill:
        shp.fill.solid()
        shp.fill.fore_color.rgb = rgb(fill)
    else:
        shp.fill.background()
    if line:
        shp.line.color.rgb = rgb(line)
        shp.line.width = Pt(line_w)
    else:
        shp.line.fill.background()
    shp.shadow.inherit = False
    if shadow:
        el = shp._element.spPr
        ef = el.makeelement(qn("a:effectLst"), {})
        sh = ef.makeelement(
            qn("a:outerShdw"),
            {
                "blurRad": "90000",
                "dist": "40000",
                "dir": "5400000",
                "rotWithShape": "0",
            },
        )
        clr = sh.makeelement(qn("a:srgbClr"), {"val": "0F172A"})
        alpha = clr.makeelement(qn("a:alpha"), {"val": "14000"})
        clr.append(alpha)
        sh.append(clr)
        ef.append(sh)
        el.append(ef)
    return shp


def text(
    s,
    runs,
    x,
    y,
    w,
    h,
    align=PP_ALIGN.LEFT,
    anchor=MSO_ANCHOR.TOP,
    wrap=True,
    space_after=4,
):
    tb = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = wrap
    tf.vertical_anchor = anchor
    tf.margin_left = 0
    tf.margin_right = 0
    tf.margin_top = 0
    tf.margin_bottom = 0
    if isinstance(runs, str):
        runs = [(runs, {})]
    if isinstance(runs[0], tuple):
        runs = [runs]
    for i, para in enumerate(runs):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.space_after = Pt(space_after)
        p.space_before = Pt(0)
        for txt, o in para:
            r = p.add_run()
            r.text = txt
            r.font.name = o.get("font", BODY)
            r.font.size = Pt(o.get("size", 16))
            r.font.bold = o.get("bold", False)
            r.font.italic = o.get("italic", False)
            r.font.color.rgb = rgb(o.get("color", INK))
            if "spacing" in o:
                _set_spacing(r, o["spacing"])
    return tb


def _set_spacing(run, pts):
    rPr = run._r.get_or_add_rPr()
    rPr.set("spc", str(int(pts * 100)))


def bullets(s, items, x, y, w, h, size=15, color=INK, gap=10, marker=TEAL, msize=None):
    tb = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = 0
    tf.margin_right = 0
    tf.margin_top = 0
    tf.margin_bottom = 0
    for i, item in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(gap)
        p.space_before = Pt(0)
        rm = p.add_run()
        rm.text = "—  "
        rm.font.name = BODY
        rm.font.size = Pt(msize or size)
        rm.font.bold = True
        rm.font.color.rgb = rgb(marker)
        if isinstance(item, tuple):
            head, rest = item
            r1 = p.add_run()
            r1.text = head
            r1.font.name = BODY
            r1.font.size = Pt(size)
            r1.font.bold = True
            r1.font.color.rgb = rgb(color)
            r2 = p.add_run()
            r2.text = rest
            r2.font.name = BODY
            r2.font.size = Pt(size)
            r2.font.color.rgb = rgb(color)
        else:
            r = p.add_run()
            r.text = item
            r.font.name = BODY
            r.font.size = Pt(size)
            r.font.color.rgb = rgb(color)
    return tb


def kicker(s, txt, x, y, color=TEAL):
    text(
        s,
        [
            [
                (
                    txt.upper(),
                    {
                        "font": MONO,
                        "size": 12,
                        "bold": True,
                        "color": color,
                        "spacing": 2,
                    },
                )
            ]
        ],
        x,
        y,
        6,
        0.3,
    )


# ---------------------------------------------------------------- slide 1: title
s = slide(NAVY)
box(s, 0.9, 1.0, 0.12, 1.9, fill=TEAL)
text(
    s,
    [
        [
            (
                "MSc Computer Animation & Visual Effects  ·  NCCA, Bournemouth",
                {"font": MONO, "size": 13, "color": TEAL_LT, "spacing": 1},
            )
        ]
    ],
    1.25,
    1.05,
    11,
    0.4,
)
text(
    s,
    [
        [
            (
                "A Lightweight USD-Based Asset",
                {"font": HEAD, "size": 40, "bold": True, "color": WHITE},
            )
        ],
        [
            (
                "Pipeline for Cross-DCC Collaboration",
                {"font": HEAD, "size": 40, "bold": True, "color": WHITE},
            )
        ],
    ],
    1.25,
    1.55,
    11.2,
    1.9,
    space_after=2,
)
text(
    s,
    [
        [
            (
                "Reliable, versioned asset exchange for small studios and student teams",
                {"size": 18, "color": SLATE_LT, "italic": True},
            )
        ]
    ],
    1.25,
    3.5,
    11,
    0.5,
)
box(s, 1.25, 4.6, 10.8, 0.02, fill=NAVY2)
text(
    s,
    [
        [("Project Proposal", {"size": 14, "bold": True, "color": WHITE})],
        [
            (
                "[Your name]  ·  Supervisor: [TBC]  ·  [Date]",
                {"size": 13, "color": SLATE_LT},
            )
        ],
    ],
    1.25,
    4.85,
    11,
    0.9,
    space_after=3,
)

# ---------------------------------------------------------------- slide 2: problem
s = slide(WHITE)
kicker(s, "The problem", 0.9, 0.7)
text(
    s,
    [
        [
            (
                "Small teams have no real asset pipeline",
                {"font": HEAD, "size": 32, "bold": True, "color": INK},
            )
        ]
    ],
    0.9,
    1.05,
    11.5,
    0.8,
)

cards = [
    (
        "Big studios",
        "Heavyweight systems — ShotGrid/Flow, Perforce, proprietary asset managers. Powerful, but costly and assume dedicated pipeline staff.",
        SLATE,
    ),
    (
        "Small teams",
        "Fall back to manual file-sharing: cloud drives, naming conventions, messaging. No versioning, no “approved” state, no cross-app consistency.",
        AMBER,
    ),
    (
        "The cost",
        "Wrong versions used, missing textures, overwritten work, time lost chasing the latest file. Errors that a pipeline is meant to prevent.",
        TEAL,
    ),
]
cx = 0.9
for title, body, accent in cards:
    box(s, cx, 2.1, 3.74, 3.7, fill=LIGHT, radius=True, shadow=True)
    box(s, cx + 0.4, 2.5, 0.5, 0.5, fill=accent, radius=True)
    text(
        s,
        [[(title, {"font": HEAD, "size": 19, "bold": True, "color": INK})]],
        cx + 0.4,
        3.2,
        3.0,
        0.5,
    )
    text(s, [[(body, {"size": 14.5, "color": SLATE})]], cx + 0.4, 3.75, 2.95, 1.9)
    cx += 3.95

# ---------------------------------------------------------------- slide 3: prototype
s = slide(WHITE)
kicker(s, "Starting point", 0.9, 0.7, color=AMBER)
text(
    s,
    [
        [
            (
                "I built a prototype — and it showed me the limits",
                {"font": HEAD, "size": 30, "bold": True, "color": INK},
            )
        ]
    ],
    0.9,
    1.05,
    11.5,
    0.8,
)

box(s, 0.9, 2.15, 5.5, 4.0, fill=NAVY, radius=True, shadow=True)
text(
    s,
    [
        [
            (
                "WHAT WORKS",
                {
                    "font": MONO,
                    "size": 12,
                    "bold": True,
                    "color": TEAL_LT,
                    "spacing": 2,
                },
            )
        ]
    ],
    1.3,
    2.5,
    4.5,
    0.3,
)
bullets(
    s,
    [
        "FastAPI + MongoDB server, DCC-agnostic",
        "Maya client: upload, approve, import",
        "“Ready” state gates what others pull",
        "Auto front/top thumbnails on publish",
        "PySide6 GUI + automated test suite",
    ],
    1.3,
    3.0,
    4.8,
    3.0,
    size=15,
    color="E2E8F0",
    marker=TEAL_LT,
    gap=11,
)

box(s, 6.7, 2.15, 5.7, 4.0, fill=LIGHT, radius=True, shadow=True)
text(
    s,
    [
        [
            (
                "WHAT IT REVEALED",
                {"font": MONO, "size": 12, "bold": True, "color": AMBER, "spacing": 2},
            )
        ]
    ],
    7.1,
    2.5,
    4.5,
    0.3,
)
bullets(
    s,
    [
        (".obj is a dead end — ", "no materials, hierarchy, or variants"),
        ("No versioning — ", "re-upload overwrites history"),
        ("Weak auth — ", "a root password check"),
        ("One hard-coded DCC — ", "doesn’t generalise"),
        ("Localhost only — ", "no real deployment story"),
    ],
    7.1,
    3.0,
    5.0,
    3.0,
    size=15,
    color=INK,
    marker=AMBER,
    gap=11,
)

# ---------------------------------------------------------------- slide 4: research question
s = slide(NAVY)
box(s, 0.9, 1.5, 0.12, 3.4, fill=TEAL)
kicker(s, "Research question", 1.25, 1.55, color=TEAL_LT)
text(
    s,
    [
        [
            (
                "Can a lightweight, USD-based asset",
                {"font": HEAD, "size": 30, "bold": True, "color": WHITE},
            )
        ],
        [
            (
                "system provide ",
                {"font": HEAD, "size": 30, "bold": True, "color": WHITE},
            ),
            (
                "reliable, versioned,",
                {"font": HEAD, "size": 30, "bold": True, "color": TEAL_LT},
            ),
        ],
        [
            ("cross-DCC", {"font": HEAD, "size": 30, "bold": True, "color": TEAL_LT}),
            (
                " asset exchange for small",
                {"font": HEAD, "size": 30, "bold": True, "color": WHITE},
            ),
        ],
        [
            (
                "studios — and does it ",
                {"font": HEAD, "size": 30, "bold": True, "color": WHITE},
            ),
            ("measurably", {"font": HEAD, "size": 30, "bold": True, "color": TEAL_LT}),
        ],
        [
            ("improve", {"font": HEAD, "size": 30, "bold": True, "color": TEAL_LT}),
            (
                " on manual file-sharing?",
                {"font": HEAD, "size": 30, "bold": True, "color": WHITE},
            ),
        ],
    ],
    1.25,
    2.15,
    11,
    3.4,
    space_after=4,
)
text(
    s,
    [
        [
            (
                "Measured on usability and error reduction, with real artists.",
                {"size": 16, "italic": True, "color": SLATE_LT},
            )
        ]
    ],
    1.25,
    5.7,
    11,
    0.5,
)

# ---------------------------------------------------------------- slide 5: why USD
s = slide(WHITE)
kicker(s, "Why USD", 0.9, 0.7)
text(
    s,
    [
        [
            (
                "The technical spine, not a buzzword",
                {"font": HEAD, "size": 32, "bold": True, "color": INK},
            )
        ]
    ],
    0.9,
    1.05,
    11.5,
    0.8,
)

box(s, 0.9, 2.1, 3.5, 3.9, fill=LIGHT, radius=True, shadow=True)
text(
    s,
    [[(".obj", {"font": MONO, "size": 22, "bold": True, "color": SLATE})]],
    1.25,
    2.45,
    3,
    0.5,
)
text(
    s,
    [[("the prototype", {"size": 13, "italic": True, "color": SLATE_LT})]],
    1.25,
    2.95,
    3,
    0.3,
)
bullets(
    s,
    [
        "Geometry only",
        "No materials / textures",
        "No hierarchy or variants",
        "Overwrite = lost history",
    ],
    1.25,
    3.5,
    3.0,
    2.3,
    size=14,
    color=SLATE,
    marker=SLATE_LT,
    gap=9,
)

box(s, 4.7, 2.1, 7.7, 3.9, fill=NAVY, radius=True, shadow=True)
text(
    s,
    [[("OpenUSD", {"font": MONO, "size": 22, "bold": True, "color": TEAL_LT})]],
    5.05,
    2.45,
    5,
    0.5,
)
text(
    s,
    [
        [
            (
                "industry interchange standard — native in Maya, Houdini, Unreal, Blender",
                {"size": 13, "italic": True, "color": SLATE_LT},
            )
        ]
    ],
    5.05,
    2.95,
    7,
    0.3,
)
bullets(
    s,
    [
        (
            "Composition = versioning  ",
            "each publish is a new layer; a stable stub references the approved one",
        ),
        (
            "Asset resolution  ",
            "a logical URI resolves to the right version (Ar 2.0, stretch goal)",
        ),
        (
            "Rich data  ",
            "hierarchy, materials (MaterialX), metadata travel with the asset",
        ),
        ("Native per-DCC bridges  ", "export/import via each tool’s own USD support"),
    ],
    5.05,
    3.5,
    7.0,
    2.4,
    size=14,
    color="E2E8F0",
    marker=TEAL_LT,
    gap=9,
)

# ---------------------------------------------------------------- slide 6: aims & objectives
s = slide(WHITE)
kicker(s, "Aims & objectives", 0.9, 0.7)
text(
    s,
    [
        [
            (
                "What the project sets out to do",
                {"font": HEAD, "size": 32, "bold": True, "color": INK},
            )
        ]
    ],
    0.9,
    1.05,
    11.5,
    0.8,
)
objectives = [
    (
        "01",
        "Review existing pipelines",
        "Large-studio tools, open-source (Kitsu, Prism) and USD pipelines — articulate the gap.",
    ),
    (
        "02",
        "Build a versioned server",
        "Authenticated, versioned USD storage with an “approved” state.",
    ),
    ("03", "Two DCC clients", "USD publish / consume in Maya and Houdini."),
    ("04", "Real versioning", "Consume “latest approved” or a pinned version."),
    (
        "05",
        "Evaluate with artists",
        "Task-based study, SUS questionnaire, comparison vs manual workflow.",
    ),
    ("06", "Deploy properly", "Docker, CI, and a documented setup beyond localhost."),
]
gx, gy = 0.9, 2.15
for i, (num, head, body) in enumerate(objectives):
    col = i % 3
    row = i // 3
    x = gx + col * 3.95
    y = gy + row * 1.95
    box(s, x, y, 3.74, 1.75, fill=LIGHT, radius=True, shadow=True)
    text(
        s,
        [[(num, {"font": HEAD, "size": 26, "bold": True, "color": TEAL})]],
        x + 0.35,
        y + 0.25,
        1.2,
        0.6,
    )
    text(
        s,
        [[(head, {"font": BODY, "size": 15.5, "bold": True, "color": INK})]],
        x + 1.25,
        y + 0.28,
        2.3,
        0.5,
    )
    text(s, [[(body, {"size": 12.5, "color": SLATE})]], x + 1.25, y + 0.72, 2.35, 0.95)

# ---------------------------------------------------------------- slide 7: methodology / architecture
s = slide(WHITE)
kicker(s, "Methodology", 0.9, 0.7)
text(
    s,
    [
        [
            (
                "Design-and-build, with an empirical evaluation",
                {"font": HEAD, "size": 30, "bold": True, "color": INK},
            )
        ]
    ],
    0.9,
    1.05,
    11.8,
    0.8,
)


# architecture row
def node(s, x, y, w, h, title, sub_lines, fill, tcolor, scolor):
    box(s, x, y, w, h, fill=fill, radius=True, shadow=True)
    text(
        s,
        [[(title, {"font": BODY, "size": 16, "bold": True, "color": tcolor})]],
        x,
        y + 0.42,
        w,
        0.5,
        align=PP_ALIGN.CENTER,
    )
    text(
        s,
        [[(line, {"size": 12, "color": scolor})] for line in sub_lines],
        x,
        y + 0.95,
        w,
        0.8,
        align=PP_ALIGN.CENTER,
        space_after=2,
    )


ay = 2.35
node(
    s,
    0.9,
    ay,
    3.2,
    1.85,
    "DCC Clients",
    ["Maya + Houdini", "USD publish / consume"],
    LIGHT,
    INK,
    SLATE,
)
node(
    s,
    5.05,
    ay,
    3.2,
    1.85,
    "FastAPI Server",
    ["auth · versioning", "approved state"],
    NAVY,
    WHITE,
    SLATE_LT,
)
node(
    s,
    9.2,
    ay,
    3.2,
    1.85,
    "USD Storage",
    ["versioned layers", "+ asset stubs"],
    LIGHT,
    INK,
    SLATE,
)
# arrows
for ax in (4.2, 8.35):
    a = s.shapes.add_shape(
        MSO_SHAPE.RIGHT_ARROW, Inches(ax), Inches(ay + 0.72), Inches(0.7), Inches(0.4)
    )
    a.fill.solid()
    a.fill.fore_color.rgb = rgb(TEAL)
    a.line.fill.background()
    a.shadow.inherit = False

box(s, 0.9, 4.6, 11.5, 0.018, fill=LINE)
text(
    s,
    [
        [
            (
                "EVALUATION",
                {"font": MONO, "size": 12, "bold": True, "color": TEAL, "spacing": 2},
            )
        ]
    ],
    0.9,
    4.85,
    6,
    0.3,
)
ev = [
    (
        "Usability study  ",
        "6–10 artists, fixed publish/consume tasks; time + success rate",
    ),
    ("SUS questionnaire  ", "standard, citable usability score"),
    ("Comparative analysis  ", "tool vs manual file-sharing: errors + time"),
    ("Technical eval  ", "performance as asset count and size scale"),
]
bullets(s, ev[:2], 0.9, 5.25, 5.6, 1.6, size=14, color=INK, gap=10)
bullets(s, ev[2:], 6.8, 5.25, 5.6, 1.6, size=14, color=INK, gap=10)

# ---------------------------------------------------------------- slide 8: timeline
s = slide(WHITE)
kicker(s, "Timeline", 0.9, 0.7)
text(
    s,
    [
        [
            (
                "~14 weeks, scoped to one summer",
                {"font": HEAD, "size": 32, "bold": True, "color": INK},
            )
        ]
    ],
    0.9,
    1.05,
    11.5,
    0.8,
)
phases = [
    (
        "Wk 1–2",
        "Review & scope",
        "Literature + tools review; lock the question with supervisor",
    ),
    (
        "Wk 3–4",
        "Server core",
        "Auth, versioned USD storage, approved state, tests + CI",
    ),
    ("Wk 5–7", "Maya client", "USD publish / consume, version selection"),
    ("Wk 8–9", "Houdini client", "USD publish / consume"),
    ("Wk 10–11", "Versioning + deploy", "Resolution layer; Docker; pilot the study"),
    ("Wk 12–14", "Study & write-up", "Run user study, analyse, finalise thesis"),
]
ty = 2.2
for i, (wk, head, body) in enumerate(phases):
    y = ty + i * 0.83
    box(s, 0.9, y, 1.9, 0.66, fill=NAVY, radius=True)
    text(
        s,
        [[(wk, {"font": MONO, "size": 14, "bold": True, "color": TEAL_LT})]],
        0.9,
        y,
        1.9,
        0.66,
        align=PP_ALIGN.CENTER,
        anchor=MSO_ANCHOR.MIDDLE,
    )
    box(s, 3.0, y, 9.4, 0.66, fill=LIGHT, radius=True)
    text(
        s,
        [
            [
                (head + "   ", {"size": 15, "bold": True, "color": INK}),
                (body, {"size": 13.5, "color": SLATE}),
            ]
        ],
        3.35,
        y,
        8.9,
        0.66,
        anchor=MSO_ANCHOR.MIDDLE,
    )

# ---------------------------------------------------------------- slide 9: scope & risks
s = slide(WHITE)
kicker(s, "Scope & risk", 0.9, 0.7)
text(
    s,
    [
        [
            (
                "Deliberately bounded",
                {"font": HEAD, "size": 32, "bold": True, "color": INK},
            )
        ]
    ],
    0.9,
    1.05,
    11.5,
    0.8,
)

box(s, 0.9, 2.1, 3.6, 3.9, fill=LIGHT, radius=True, shadow=True)
text(
    s,
    [
        [
            (
                "IN SCOPE",
                {"font": MONO, "size": 12, "bold": True, "color": TEAL, "spacing": 2},
            )
        ]
    ],
    1.25,
    2.45,
    3,
    0.3,
)
bullets(
    s,
    [
        "USD interchange",
        "Versioning + approved state",
        "Maya + Houdini clients",
        "Auth + Docker deploy",
        "Automated tests",
        "User evaluation",
    ],
    1.25,
    2.95,
    3.0,
    3.0,
    size=14,
    color=INK,
    marker=TEAL,
    gap=10,
)

box(s, 4.75, 2.1, 3.6, 3.9, fill=LIGHT, radius=True, shadow=True)
text(
    s,
    [
        [
            (
                "FUTURE WORK",
                {"font": MONO, "size": 12, "bold": True, "color": SLATE, "spacing": 2},
            )
        ]
    ],
    5.1,
    2.45,
    3,
    0.3,
)
bullets(
    s,
    [
        "Substance / texture round-trip",
        "Full custom Ar 2.0 resolver",
        "Shot / sequence mgmt",
        "Real-time multi-user",
        "Cloud-scale storage",
    ],
    5.1,
    2.95,
    3.0,
    3.0,
    size=14,
    color=SLATE,
    marker=SLATE_LT,
    gap=10,
)

box(s, 8.6, 2.1, 3.8, 3.9, fill=NAVY, radius=True, shadow=True)
text(
    s,
    [
        [
            (
                "KEY RISKS",
                {"font": MONO, "size": 12, "bold": True, "color": AMBER, "spacing": 2},
            )
        ]
    ],
    8.95,
    2.45,
    3,
    0.3,
)
bullets(
    s,
    [
        ("USD learning curve  ", "use prebuilt usd-core; week-1 spike"),
        ("Resolver too big  ", "fall back to server-side resolution"),
        ("Recruiting artists  ", "use NCCA cohort; short tasks"),
    ],
    8.95,
    2.95,
    3.15,
    3.0,
    size=13.5,
    color="E2E8F0",
    marker=AMBER,
    gap=12,
)

# ---------------------------------------------------------------- slide 10: contributions / close
s = slide(NAVY)
kicker(s, "Expected contribution", 0.9, 0.8, color=TEAL_LT)
text(
    s,
    [[("What this adds", {"font": HEAD, "size": 34, "bold": True, "color": WHITE})]],
    0.9,
    1.2,
    11,
    0.9,
)
contribs = [
    (
        "A working tool",
        "An open-source, self-hostable USD asset pipeline built for small teams.",
    ),
    (
        "A design analysis",
        "What a minimal USD pipeline actually requires, grounded in a review of existing systems.",
    ),
    (
        "Empirical evidence",
        "Whether it improves usability and reduces errors vs manual workflows.",
    ),
]
cx = 0.9
for title, body in contribs:
    box(s, cx, 2.5, 3.74, 2.7, fill=NAVY2, radius=True)
    box(s, cx + 0.4, 2.9, 0.5, 0.12, fill=TEAL)
    text(
        s,
        [[(title, {"font": HEAD, "size": 19, "bold": True, "color": WHITE})]],
        cx + 0.4,
        3.25,
        3.0,
        0.6,
    )
    text(s, [[(body, {"size": 14, "color": SLATE_LT})]], cx + 0.4, 3.85, 2.95, 1.2)
    cx += 3.95
text(
    s,
    [
        [
            ("Thank you", {"font": HEAD, "size": 20, "bold": True, "color": WHITE}),
            ("    Questions welcome.", {"size": 16, "italic": True, "color": SLATE_LT}),
        ]
    ],
    0.9,
    5.8,
    11,
    0.6,
)

prs.save(r"C:\Work\code\obj-pipeline\docs\MSc_Proposal.pptx")
print("saved MSc_Proposal.pptx with", len(prs.slides._sldIdLst), "slides")
