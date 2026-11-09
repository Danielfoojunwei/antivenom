"""Convert hackathon_entry_draft.md to .docx (headings, lists, tables, bold/italic)."""
import re
from docx import Document
from docx.shared import Pt
d = Document(); d.styles["Normal"].font.name = "Arial"; d.styles["Normal"].font.size = Pt(11)
L = open("hackathon_entry_draft.md").read().splitlines(); i = 0
def runs(p, t):
    for part in re.split(r"(\*\*[^*]+\*\*|\*[^*]+\*)", t):
        if part.startswith("**"): p.add_run(part[2:-2]).bold = True
        elif part.startswith("*") and len(part) > 1: p.add_run(part[1:-1]).italic = True
        else: p.add_run(part)
while i < len(L):
    l = L[i]
    if l.startswith("|"):
        rows = []
        while i < len(L) and L[i].startswith("|"):
            if not re.match(r"^\|[-:| ]+\|$", L[i]): rows.append([c.strip() for c in L[i].strip("|").split("|")])
            i += 1
        t = d.add_table(rows=len(rows), cols=len(rows[0])); t.style = "Light Grid Accent 1"
        for r, row in enumerate(rows):
            for c, v in enumerate(row): t.cell(r, c).text = ""; runs(t.cell(r, c).paragraphs[0], v)
        continue
    if l.startswith("# "): d.add_heading(l[2:], 0)
    elif l.startswith("### "): d.add_heading(l[4:], 2)
    elif l.startswith("## "): d.add_heading(l[3:], 1)
    elif re.match(r"^\d+\. ", l): runs(d.add_paragraph(style="List Number"), re.sub(r"^\d+\. ", "", l))
    elif l.startswith("- "): runs(d.add_paragraph(style="List Bullet"), l[2:])
    elif l.strip(): runs(d.add_paragraph(), l)
    i += 1
d.save("hackathon_entry_draft.docx"); print("ok")
