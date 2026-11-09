"""Render the editable manuscript as a review PDF; never run research models.

Requires reportlab. Use --font-dir if DejaVu fonts are not found locally.
The standard-library table exporter is the authoritative numeric source.
"""
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
import re

from reportlab.graphics.shapes import Drawing, Rect, String, Line
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, LongTable, TableStyle, KeepTogether

ROOT = Path(__file__).resolve().parents[1]
WIDTH = A4[0] - 96
INK = colors.HexColor("#162435")
BLUE = colors.HexColor("#20647d")


def fonts(directory=None):
    candidates = [Path(directory)] if directory else [
        Path("/usr/share/fonts/truetype/dejavu"),
        Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies/native/libreoffice-headless/libreoffice/LibreOfficeDev.app/Contents/Resources/fonts/truetype",
    ]
    for path in candidates:
        if (path / "DejaVuSerif.ttf").is_file():
            for name, filename in (("Paper", "DejaVuSerif.ttf"),
                    ("Paper-Bold", "DejaVuSerif-Bold.ttf"),
                    ("Paper-Italic", "DejaVuSerif-Italic.ttf"),
                    ("Paper-BoldItalic", "DejaVuSerif-BoldItalic.ttf"),
                    ("Mono", "DejaVuSansMono.ttf")):
                pdfmetrics.registerFont(TTFont(name, str(path / filename)))
            pdfmetrics.registerFontFamily("Paper", normal="Paper", bold="Paper-Bold",
                italic="Paper-Italic", boldItalic="Paper-BoldItalic")
            return
    raise RuntimeError("DejaVu fonts missing; specify --font-dir with their directory")


def clean(text):
    text = text.replace("–", "-").replace("—", "-").replace("−", "-").replace("‑", "-")
    return text


def math_markup(text):
    text = clean(text)
    substitutions = {r"\sigma": "σ", r"\lor": "∨", r"\ge": "≥", r"\pi": "π"}
    for src, target in substitutions.items():
        text = text.replace(src, target)
    text = html.escape(text.replace("\\", ""))
    text = re.sub(r"\^\*", "<super>*</super>", text)
    text = re.sub(r"_([a-zA-Z])", r"<sub>\1</sub>", text)
    return '<font name="Paper-Italic">' + text + '</font>'


def inline(text):
    maths = []
    def protect(match):
        maths.append(math_markup(match[1]))
        return "MATHSLOT" + str(len(maths)-1) + "ENDMATHSLOT"
    text = re.sub(r"\\\((.*?)\\\)", protect, text)
    text = html.escape(clean(text))
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)",
        lambda m: '<link href="' + m[2] + '" color="#20647d">' + m[1] + '</link>'
        if m[2].startswith("https://") else m[1], text)
    text = re.sub(r"`([^`]+)`", r'<font name="Mono" size="7.5">\1</font>', text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<i>\1</i>", text)
    for n, value in enumerate(maths):
        text = text.replace("MATHSLOT" + str(n) + "ENDMATHSLOT", value)
    return text


def styles():
    common = dict(fontName="Paper", fontSize=9.1, leading=13, textColor=INK,
        spaceAfter=7, allowWidows=0, allowOrphans=0)
    body = ParagraphStyle("body", **common)
    return {
        "body": body,
        "title": ParagraphStyle("title", parent=body, fontName="Paper-Bold", fontSize=18,
            leading=23, alignment=TA_CENTER, spaceAfter=14),
        "h2": ParagraphStyle("h2", parent=body, fontName="Paper-Bold", fontSize=11.2,
            leading=15, spaceBefore=12, spaceAfter=6, keepWithNext=True),
        "h3": ParagraphStyle("h3", parent=body, fontName="Paper-Bold", fontSize=9.5,
            leading=13, spaceBefore=8, spaceAfter=5, keepWithNext=True),
        "cell": ParagraphStyle("cell", parent=body, fontSize=6.9, leading=9, spaceAfter=0),
        "bullet": ParagraphStyle("bullet", parent=body, leftIndent=13, firstLineIndent=-11),
        "code": ParagraphStyle("code", parent=body, fontName="Mono", fontSize=7,
            leading=10, leftIndent=8, rightIndent=8, backColor=colors.HexColor("#f1f4f5")),
        "caption": ParagraphStyle("caption", parent=body, keepWithNext=True),
    }


def control_figure():
    summary = json.loads((ROOT / "results/memform_drop_all_summary_v1.json").read_text())
    # Exact same complete-control rates as the editable SVG/table, displayed
    # on a common 0-100% axis. No error-bar claim is inferred from these bars.
    rates = summary["all_target"]["rates"]
    drawing = Drawing(WIDTH, 185)
    palette = [colors.HexColor(c) for c in ("#207b79", "#ba8252", "#8393a5")]
    panels = [("clean", "correct", "Clean task correctness"),
              ("poisoned", "endorsed", "Poisoned-action endorsement")]
    for p, (condition, metric, title) in enumerate(panels):
        left = p * (WIDTH / 2) + 20
        top = 163
        drawing.add(String(left, top, title, fontName="Paper-Bold", fontSize=8.2, fillColor=INK))
        drawing.add(Line(left + 36, 34, left + 36, 143, strokeColor=colors.HexColor("#ccd6dd")))
        for tick in (0, 50, 100):
            x = left + 36 + tick * 1.55
            drawing.add(Line(x, 34, x, 143, strokeColor=colors.HexColor("#e5e9ec")))
            drawing.add(String(x, 20, str(tick), textAnchor="middle", fontName="Paper", fontSize=7, fillColor=INK))
        for i, (method, label) in enumerate((("entail", "Entail"), ("OR", "OR"), ("drop_all", "Empty"))):
            value = rates[condition][method][metric]
            y = 118 - i * 33
            drawing.add(String(left + 30, y + 4, label, textAnchor="end", fontName="Paper", fontSize=7.5, fillColor=INK))
            drawing.add(Rect(left + 36, y, 155 * value, 17, fillColor=palette[i], strokeColor=None))
            drawing.add(String(left + 39 + 155 * value, y + 4, f"{100 * value:.2f}%", fontName="Paper", fontSize=7, fillColor=INK))
    drawing.add(String(WIDTH / 2, 1, "212 already-used local families; paired inference and simultaneous bounds in Table 2",
        textAnchor="middle", fontName="Paper", fontSize=7, fillColor=INK))
    return drawing


def markdown_story(text, sty):
    lines, story, i = text.splitlines(), [], 0
    while i < len(lines):
        line = lines[i].strip()
        if not line or line.startswith("<!--"):
            i += 1
            continue
        if line.startswith("```"):
            code = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                code.append(lines[i]); i += 1
            story.append(Paragraph("<br/>".join(html.escape(clean(x)) for x in code), sty["code"]))
            i += 1
            continue
        if line.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                row = [cell.strip() for cell in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r"[:\- ]+", cell) for cell in row):
                    rows.append(row)
                i += 1
            count = len(rows[0])
            if any(len(row) != count for row in rows):
                raise ValueError("Malformed Markdown table")
            width = [WIDTH / count] * count
            if count == 10:
                rows[0] = ["Cond.", "Signature method", "Endpoint", "Effect (pp)",
                    "Paired 95% CI (pp)", "Simultaneous 95% (pp)", "1 / 0", "0 / 1", "Holm8 p", "Verdict"]
                for row in rows[1:]:
                    row[8] = f"{float(row[8]):.3g}"
                weights = [40, 65, 42, 38, 66, 66, 28, 28, 55, 63]
                width = [WIDTH * w / sum(weights) for w in weights]
            elif count == 5:
                width = [WIDTH * x for x in (.31, .14, .22, .22, .11)]
            table = LongTable([[Paragraph(inline(cell), sty["cell"]) for cell in row] for row in rows],
                colWidths=width, repeatRows=1, hAlign="LEFT")
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e7eff2")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f6f8f9")]),
                ("LINEBELOW", (0, 0), (-1, 0), .6, BLUE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]))
            group = [table]
            if story and isinstance(story[-1], Paragraph) and story[-1].style.name == "caption":
                group.insert(0, story.pop())
            story.extend([KeepTogether(group), Spacer(1, 8)])
            if count == 10:
                story.append(Paragraph("Discordant columns show signature / empty-history endpoint indicators. Paired intervals are descriptive; simultaneous bounds and Holm tests are separate procedures.", sty["cell"]))
                story.append(Spacer(1, 7))
            continue
        if line.startswith("!["):
            story.append(control_figure()); i += 1; continue
        heading = re.match(r"^(#{1,3}) (.+)", line)
        if heading:
            key = {1: "title", 2: "h2", 3: "h3"}[len(heading[1])]
            story.append(Paragraph(inline(heading[2]), sty[key])); i += 1; continue
        is_bullet = bool(re.match(r"^(?:\d+\.|-) ", line))
        para = [line]
        i += 1
        while i < len(lines) and lines[i].strip() and not re.match(r"^(?:#|\||```|!\[|<!--|\d+\. |\- )", lines[i].strip()):
            para.append(lines[i].strip()); i += 1
        style = "caption" if line.startswith("**Table ") else "bullet" if is_bullet else "body"
        story.append(Paragraph(inline(" ".join(para)), sty[style]))
    return story


def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#d5dfe5")); canvas.setLineWidth(.4)
    canvas.line(48, A4[1]-31, A4[0]-48, A4[1]-31)
    canvas.setFillColor(colors.HexColor("#5d6e7b")); canvas.setFont("Paper", 7)
    canvas.drawString(48, A4[1]-24, "ANTIVENOM | Research draft | 4 November 2026")
    canvas.drawRightString(A4[0]-48, 29, str(doc.page))
    canvas.drawString(48, 29, "Completed local evidence; fresh confirmation and human validation pending")
    canvas.restoreState()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--font-dir")
    parser.add_argument("--output", default="output/pdf/antivenom_manuscript_draft.pdf")
    args = parser.parse_args()
    fonts(args.font_dir)
    out = ROOT / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    text = (ROOT / "paper/manuscript.md").read_text()
    document = SimpleDocTemplate(str(out), pagesize=A4, leftMargin=48, rightMargin=48,
        topMargin=45, bottomMargin=47, title="Incident-Derived Evidence Filtering: Utility Gains and Limits",
        author="", pageCompression=1, invariant=1)
    document.build(markdown_story(text, styles()), onFirstPage=footer, onLaterPages=footer)
    print(out)


if __name__ == "__main__":
    main()
