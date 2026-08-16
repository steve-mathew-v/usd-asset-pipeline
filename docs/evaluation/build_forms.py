"""Generate Word (.docx) evaluation forms: a blank pack and two filled samples."""

import os

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt, RGBColor

HERE = os.path.dirname(os.path.abspath(__file__))

SUS_ITEMS = [
    "I think that I would like to use this system frequently.",
    "I found the system unnecessarily complex.",
    "I thought the system was easy to use.",
    "I think that I would need the support of a technical person to use this system.",
    "I found the various functions in this system were well integrated.",
    "I thought there was too much inconsistency in this system.",
    "I would imagine that most people would learn to use this system very quickly.",
    "I found the system very cumbersome to use.",
    "I felt very confident using the system.",
    "I needed to learn a lot of things before I could get going with this system.",
]

CHECKED, EMPTY = "☒", "☐"  # ☒ , ☐


def heading(doc, text, level=1):
    doc.add_heading(text, level=level)


def para(doc, text="", italic=False, bold=False, color=None, size=None):
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.italic = italic
    run.bold = bold
    if color:
        run.font.color.rgb = RGBColor.from_string(color)
    if size:
        run.font.size = Pt(size)
    return p


def checkbox(doc, text, checked=False):
    p = doc.add_paragraph()
    p.add_run(f"{CHECKED if checked else EMPTY}  {text}")


def write_in(doc, label, answer=None):
    p = doc.add_paragraph()
    p.add_run(f"{label}  ").bold = True
    if answer:
        run = p.add_run(answer)
        run.italic = True
        run.font.color.rgb = RGBColor.from_string("1F4E79")
    else:
        p.add_run("________________________________________")


def sus_score(answers):
    total = 0
    for i, ans in enumerate(answers, start=1):
        total += (ans - 1) if i % 2 == 1 else (5 - ans)
    return total * 2.5


def sus_table(doc, answers=None):
    table = doc.add_table(rows=1, cols=6)
    table.style = "Table Grid"
    hdr = table.rows[0].cells
    for idx, label in enumerate(["Statement", "1", "2", "3", "4", "5"]):
        run = hdr[idx].paragraphs[0].add_run(label)
        run.bold = True
    for i, item in enumerate(SUS_ITEMS):
        row = table.add_row().cells
        row[0].paragraphs[0].add_run(f"{i + 1}. {item}")
        for col in range(1, 6):
            mark = ""
            if answers is not None and answers[i] == col:
                mark = "X"
            cell_par = row[col].paragraphs[0]
            cell_par.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = cell_par.add_run(mark)
            run.bold = True


def consent_section(doc, signed_name=None, pid=None):
    heading(doc, "1. Participant Information & Consent")
    para(
        doc,
        "You are invited to take part in a short study evaluating a USD asset "
        "pipeline that lets artists share versioned 3D assets between Maya and "
        "Houdini through a central server. This is part of an MSc Computer "
        "Animation & Visual Effects project at the NCCA, Bournemouth University.",
    )
    para(doc, "Taking part is voluntary. You may skip any question and stop at "
              "any time. Your responses are anonymous (stored against an ID, not "
              "your name) and used only for this academic project; only "
              "aggregated results and anonymised quotes are reported.")
    para(doc, "Please tick each box and sign:", bold=True)
    for text in [
        "I have read and understood the information above.",
        "I understand my participation is voluntary and I can withdraw at any time.",
        "I understand my responses are anonymous and used only for this project.",
        "I agree to take part.",
    ]:
        checkbox(doc, text, checked=signed_name is not None)
    write_in(doc, "Participant ID:", pid)
    write_in(doc, "Signature:", signed_name)
    write_in(doc, "Date:", "01/09/2026" if signed_name else None)


def background_section(doc, answers=None):
    heading(doc, "2. Background Questionnaire")
    a = answers or {}

    para(doc, "1. Which DCC tools do you use? (tick all)", bold=True)
    for tool in ["Maya", "Houdini", "Blender", "Other"]:
        checkbox(doc, tool, checked=tool in a.get("tools", []))

    para(doc, "2. Experience with 3D DCC tools:", bold=True)
    for lvl in ["Beginner (< 1 yr)", "Intermediate (1-3 yrs)", "Advanced (3+ yrs)"]:
        checkbox(doc, lvl, checked=a.get("experience") == lvl)

    para(doc, "3. Have you used USD before?", bold=True)
    for opt in ["Never", "A little", "Regularly"]:
        checkbox(doc, opt, checked=a.get("usd") == opt)

    para(doc, "4. How do you currently share assets? (tick all)", bold=True)
    for opt in ["Cloud drive", "Shared network folder", "Messaging / email",
                "Version control", "A dedicated pipeline / asset manager", "Other"]:
        checkbox(doc, opt, checked=opt in a.get("sharing", []))

    para(doc, "5. How often do you hit problems with your current method?", bold=True)
    for opt in ["Never", "Rarely", "Sometimes", "Often"]:
        checkbox(doc, opt, checked=a.get("problems") == opt)

    para(doc, "6. Have you used a dedicated pipeline / asset manager before?", bold=True)
    checkbox(doc, "No", checked=a.get("prior_tool") == "No")
    checkbox(doc, "Yes", checked=a.get("prior_tool") not in (None, "No"))


def sus_section(doc, answers=None):
    heading(doc, "3. System Usability Scale (SUS)")
    para(doc, "For each statement, mark how much you agree, from 1 = Strongly "
              "disagree to 5 = Strongly agree. Answer with your first reaction.",
         italic=True)
    sus_table(doc, answers)
    if answers is not None:
        score = sus_score(answers)
        band = ("Excellent" if score >= 85 else "Good" if score >= 68
                else "Below average" if score >= 51 else "Poor")
        para(doc)
        para(doc, f"SUS score: {score:.1f} / 100  ({band})", bold=True,
             color="1F4E79")


def poststudy_section(doc, answers=None):
    heading(doc, "4. Post-Study Questionnaire")
    a = answers or {}

    para(doc, "1. Compared with how you normally share assets, this tool was:",
         bold=True)
    for opt in ["Much worse", "Worse", "About the same", "Better", "Much better"]:
        checkbox(doc, opt, checked=a.get("compare") == opt)

    para(doc, "2. Confidence you'd import the correct, latest version vs your "
              "current method:", bold=True)
    for opt in ["Much less", "Less", "Same", "More", "Much more"]:
        checkbox(doc, opt, checked=a.get("confidence") == opt)

    para(doc, "3. How useful was the version history?", bold=True)
    for opt in ["Not useful", "Slightly", "Useful", "Very useful"]:
        checkbox(doc, opt, checked=a.get("versioning") == opt)

    for q, key in [
        ("4. What did you like most?", "like"),
        ("5. What was confusing or frustrating?", "confusing"),
        ("6. Was anything missing that you expected?", "missing"),
        ("7. Would you use this on a real project? Why / why not?", "woulduse"),
    ]:
        para(doc, q, bold=True)
        if a.get(key):
            para(doc, a[key], italic=True, color="1F4E79")
        else:
            para(doc, "____________________________________________________")
            para(doc, "____________________________________________________")


def build_blank(path):
    doc = Document()
    title = doc.add_heading("USD Asset Pipeline", level=0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sub = para(doc, "Participant Evaluation Forms", size=14)
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    para(doc, "MSc Computer Animation & Visual Effects — NCCA, Bournemouth",
         italic=True).alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_page_break()

    consent_section(doc)
    doc.add_page_break()
    background_section(doc)
    doc.add_page_break()
    sus_section(doc)
    doc.add_page_break()
    poststudy_section(doc)
    doc.save(path)
    print("saved", os.path.basename(path))


SAMPLES = [
    {
        "name": "SAMPLE — A. Rivera (illustrative)",
        "pid": "P1 (SAMPLE)",
        "bg": {
            "tools": ["Maya"],
            "experience": "Intermediate (1-3 yrs)",
            "usd": "A little",
            "sharing": ["Cloud drive", "Messaging / email"],
            "problems": "Sometimes",
            "prior_tool": "No",
        },
        "sus": [5, 2, 5, 1, 4, 2, 5, 1, 4, 2],
        "post": {
            "compare": "Much better",
            "confidence": "Much more",
            "versioning": "Very useful",
            "like": "Publishing straight from the shelf and the automatic "
                    "thumbnails — I could see exactly what each asset was.",
            "confusing": "Nothing major. It took a second to realise publishing "
                         "and approving are separate steps.",
            "missing": "A search box would help once there are lots of assets.",
            "woulduse": "Yes — it removes the guesswork of which file is current.",
        },
    },
    {
        "name": "SAMPLE — J. Okafor (illustrative)",
        "pid": "P2 (SAMPLE)",
        "bg": {
            "tools": ["Maya", "Blender"],
            "experience": "Beginner (< 1 yr)",
            "usd": "Never",
            "sharing": ["Cloud drive"],
            "problems": "Often",
            "prior_tool": "No",
        },
        "sus": [4, 3, 3, 3, 3, 2, 4, 3, 3, 3],
        "post": {
            "compare": "Better",
            "confidence": "More",
            "versioning": "Useful",
            "like": "That old versions are never lost — I usually overwrite "
                    "things by accident.",
            "confusing": "The difference between 'publish' and 'approve' wasn't "
                         "obvious at first, and I wasn't always sure it worked.",
            "missing": "Clearer confirmation after each action, and a way to see "
                       "all my assets in Maya.",
            "woulduse": "Probably, once the wording is a little clearer for "
                        "beginners.",
        },
    },
    {
        "name": "SAMPLE — M. Haas (illustrative)",
        "pid": "P3 (SAMPLE)",
        "bg": {
            "tools": ["Houdini", "Maya"],
            "experience": "Advanced (3+ yrs)",
            "usd": "Regularly",
            "sharing": ["Shared network folder", "Version control"],
            "problems": "Rarely",
            "prior_tool": "Yes",
        },
        "sus": [5, 2, 5, 1, 5, 1, 4, 2, 5, 1],
        "post": {
            "compare": "Much better",
            "confidence": "Much more",
            "versioning": "Very useful",
            "like": "The versioning behaves like a real studio pipeline — "
                    "approving a specific version is exactly right.",
            "confusing": "Little for me; as a TD I'd also want a scripting API.",
            "missing": "Batch publish and an API token for automation.",
            "woulduse": "Yes, especially for small teams without ShotGrid.",
        },
    },
    {
        "name": "SAMPLE — L. Nguyen (illustrative)",
        "pid": "P4 (SAMPLE)",
        "bg": {
            "tools": ["Maya"],
            "experience": "Intermediate (1-3 yrs)",
            "usd": "A little",
            "sharing": ["Cloud drive", "Messaging / email"],
            "problems": "Sometimes",
            "prior_tool": "No",
        },
        "sus": [4, 2, 4, 2, 4, 2, 4, 2, 4, 3],
        "post": {
            "compare": "Better",
            "confidence": "More",
            "versioning": "Useful",
            "like": "Not having to message people the latest file every time.",
            "confusing": "Wasn't always sure my publish had uploaded until I "
                         "checked.",
            "missing": "A progress indicator while a big asset uploads.",
            "woulduse": "Yes, for group projects.",
        },
    },
    {
        "name": "SAMPLE — R. Silva (illustrative)",
        "pid": "P5 (SAMPLE)",
        "bg": {
            "tools": ["Maya", "Blender"],
            "experience": "Advanced (3+ yrs)",
            "usd": "A little",
            "sharing": ["Cloud drive", "Shared network folder"],
            "problems": "Sometimes",
            "prior_tool": "No",
        },
        "sus": [5, 2, 4, 1, 4, 2, 5, 2, 4, 2],
        "post": {
            "compare": "Much better",
            "confidence": "Much more",
            "versioning": "Very useful",
            "like": "Auto thumbnails and the approve step — it's clear which is "
                    "the blessed version.",
            "confusing": "The approve-versus-publish split, briefly.",
            "missing": "Search/filter and tags once there are many assets.",
            "woulduse": "Yes.",
        },
    },
    {
        "name": "SAMPLE — T. Abed (illustrative)",
        "pid": "P6 (SAMPLE)",
        "bg": {
            "tools": ["Blender", "Maya"],
            "experience": "Beginner (< 1 yr)",
            "usd": "Never",
            "sharing": ["Cloud drive"],
            "problems": "Often",
            "prior_tool": "No",
        },
        "sus": [3, 3, 3, 3, 3, 4, 3, 3, 2, 4],
        "post": {
            "compare": "About the same",
            "confidence": "Same",
            "versioning": "Slightly",
            "like": "The idea of keeping every version is good.",
            "confusing": "I got lost between publish, approve and import, and "
                         "wasn't sure what had succeeded.",
            "missing": "Much clearer step-by-step feedback and labels.",
            "woulduse": "Maybe later, once it's more beginner-friendly.",
        },
    },
]


def build_samples(path):
    doc = Document()
    title = doc.add_heading("USD Asset Pipeline", level=0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    para(doc, "Sample Completed Forms", size=14).alignment = WD_ALIGN_PARAGRAPH.CENTER
    warn = para(
        doc,
        "These are ILLUSTRATIVE EXAMPLES only — invented to show what a "
        "completed form looks like. They are NOT real participant data.",
        bold=True,
        color="C00000",
    )
    warn.alignment = WD_ALIGN_PARAGRAPH.CENTER

    for sample in SAMPLES:
        doc.add_page_break()
        banner = doc.add_heading(sample["name"], level=1)
        banner.runs[0].font.color.rgb = RGBColor.from_string("C00000")
        consent_section(doc, signed_name=sample["name"], pid=sample["pid"])
        background_section(doc, sample["bg"])
        sus_section(doc, sample["sus"])
        poststudy_section(doc, sample["post"])

    doc.save(path)
    print("saved", os.path.basename(path))


if __name__ == "__main__":
    build_blank(os.path.join(HERE, "Evaluation-Forms-Blank.docx"))
    build_samples(os.path.join(HERE, "Evaluation-Forms-Samples.docx"))
