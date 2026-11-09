"""Builds AntiVenom_5slide.pptx on the collusion deck's theme (layouts 'Title dark' and 'Content')."""
import copy
from pptx import Presentation
from pptx.util import Emu, Pt, Inches
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR

SRC = "/Users/danielfoojunwei/Downloads/Collusion_Is_Not_a_Secrecy_Problem_5min_Talk.pptx"
p = Presentation(SRC)
# drop the old slides, keep theme and layouts
sldIdLst = p.slides._sldIdLst
for sid in list(sldIdLst):
    p.part.drop_rel(sid.rId); sldIdLst.remove(sid)
TITLE, CONTENT = p.slide_layouts[1], p.slide_layouts[2]
for sh in CONTENT.shapes:
    if sh.has_text_frame and "Collusion" in sh.text_frame.text:
        r = sh.text_frame.paragraphs[0].runs
        r[0].text = "AntiVenom · Apart Swarm Alignment Hackathon 2026 · Track 4: Multi-Agent Oversight and Control"
        for x in r[1:]: x.text = ""
INK, MUTE, OURS, CG, WARN, CARD, WHITE = (RGBColor(0x1f, 0x24, 0x30), RGBColor(0x6b, 0x72, 0x80), RGBColor(0x0f, 0x76, 0x6e),
                                          RGBColor(0x7c, 0x3a, 0xed), RGBColor(0xdc, 0x26, 0x26), RGBColor(0xf3, 0xf4, 0xf6), RGBColor(255, 255, 255))
IN = 914400


def tb(s, x, y, w, h, text, size=14, bold=False, color=INK, align=PP_ALIGN.LEFT, name=None):
    b = s.shapes.add_textbox(Emu(int(x * IN)), Emu(int(y * IN)), Emu(int(w * IN)), Emu(int(h * IN)))
    if name: b.name = name
    tf = b.text_frame; tf.word_wrap = True
    for i, line in enumerate(text.split("\n")):
        para = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        r = para.add_run(); r.text = line; para.alignment = align
        r.font.size = Pt(size); r.font.bold = bold if i == 0 or not isinstance(bold, str) else False; r.font.color.rgb = color
    return b


def card(s, x, y, w, h, head, body, accent=OURS, size=12):
    r = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Emu(int(x * IN)), Emu(int(y * IN)), Emu(int(w * IN)), Emu(int(h * IN)))
    r.adjustments[0] = .08; r.fill.solid(); r.fill.fore_color.rgb = CARD; r.line.color.rgb = accent; r.line.width = Pt(1.5)
    tb(s, x + .12, y + .06, w - .24, .35, head, size + 1, True, accent)
    tb(s, x + .12, y + .4, w - .24, h - .45, body, size, False, INK)


def box(s, x, y, w, h, text, fill, fc=WHITE, size=12, shape=MSO_SHAPE.ROUNDED_RECTANGLE):
    r = s.shapes.add_shape(shape, Emu(int(x * IN)), Emu(int(y * IN)), Emu(int(w * IN)), Emu(int(h * IN)))
    r.fill.solid(); r.fill.fore_color.rgb = fill; r.line.fill.background()
    tf = r.text_frame; tf.word_wrap = True; tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    for i, line in enumerate(text.split("\n")):
        para = tf.paragraphs[0] if i == 0 else tf.add_paragraph(); para.alignment = PP_ALIGN.CENTER
        run = para.add_run(); run.text = line; run.font.size = Pt(size if i == 0 else size - 2); run.font.bold = i == 0; run.font.color.rgb = fc
    return r


def arrow(s, x1, y1, x2, y2, color=MUTE):
    c = s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Emu(int(x1 * IN)), Emu(int(y1 * IN)), Emu(int(x2 * IN)), Emu(int(y2 * IN)))
    c.line.color.rgb = color; c.line.width = Pt(2.25)
    ln = c.line._get_or_add_ln(); from lxml import etree
    ln.append(etree.SubElement(ln, "{http://schemas.openxmlformats.org/drawingml/2006/main}tailEnd", type="triangle"))


def title(s, text):
    s.placeholders[100].text = text


def notes(s, text):
    s.notes_slide.notes_text_frame.text = text


def pic(s, path, x, y, w=None, h=None):
    return s.shapes.add_picture(path, Emu(int(x * IN)), Emu(int(y * IN)), Emu(int(w * IN)) if w else None, Emu(int(h * IN)) if h else None)



PH = RGBColor(0x92, 0x40, 0x0e); PHF = RGBColor(0xfe, 0xf3, 0xc7)
def ph(s, x, y, w, h, text, size=12):
    r = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Emu(int(x * IN)), Emu(int(y * IN)), Emu(int(w * IN)), Emu(int(h * IN)))
    r.fill.solid(); r.fill.fore_color.rgb = PHF; r.line.color.rgb = RGBColor(0xd9, 0x77, 0x06); r.line.dash_style = 4
    tf = r.text_frame; tf.word_wrap = True; tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    run = tf.paragraphs[0].add_run(); run.text = text; run.font.size = Pt(size); run.font.color.rgb = PH; tf.paragraphs[0].alignment = PP_ALIGN.CENTER

# ---------- 1. Title ----------
s = p.slides.add_slide(TITLE)
s.placeholders[100].text = "AntiVenom: Question-Scoped False Claims as Portable Antibodies Against Swarm Memory Poisoning"
s.placeholders[101].text = "A new defence: one confirmed poison becomes a portable antibody that protects the whole swarm"
tb(s, .6, 3.05, 12.1, .7, "Daniel Foo · Nanyang Technological University (NTU), Singapore\nApart Research Swarm Alignment Hackathon, 6–8 November 2026 · Track 4: Multi-Agent Oversight and Control", 14, False, WHITE)
for i, (a, b) in enumerate([("60% → 8%", "receivers fooled: untreated → shared claim (Phase 2: 200 incidents, all 5 blocks, clean accuracy within 5 points)"),
                            ("+11.8 pts", "clean accuracy vs the Stealth Lens filter at matched protection"),
                            ("7% vs 5%", "one receiver vs CoordGuard (Phase 1), at 18 s vs 25 s per question")]):
    x = .6 + i * 4.1
    tb(s, x, 4.15, 3.8, .8, a, 30, True, RGBColor(0x5e, 0xea, 0xd4))
    tb(s, x, 4.95, 3.7, .95, b, 12, False, WHITE)
tb(s, .6, 6.75, 12.1, .4, "One pre-registered evaluation in two phases: Phase 1 completed before the sprint weekend, Phase 2 during it (report, Appendix A.2).", 11, False, RGBColor(0xd1, 0xd5, 0xdb))
notes(s, "When one agent confirms a poisoned record, what should it tell the others? AntiVenom passes a question-scoped false claim. We evaluated it in two pre-registered phases. One receiver alone matches CoordGuard's blocking and is faster. In the swarm, the claim cut fooled receivers from 60% to 8% and matched the Stealth Lens filter's protection with 11.8 points more clean accuracy. We also report where it loses: the raw record blocks slightly more on these near-duplicate poisons.")

# ---------- 2. Problem and reframe ----------
def table(s, rows, x, y, w, h, widths, size=10.5, hl_last=False):
    t = s.shapes.add_table(len(rows), len(rows[0]), Emu(int(x * IN)), Emu(int(y * IN)), Emu(int(w * IN)), Emu(int(h * IN))).table
    for c, ww in enumerate(widths): t.columns[c].width = Emu(int(ww * IN))
    for r, row in enumerate(rows):
        for c, v in enumerate(row):
            cell = t.cell(r, c); cell.text = v; para = cell.text_frame.paragraphs[0]; para.runs[0].font.size = Pt(size)
            last = hl_last and r == len(rows) - 1
            para.runs[0].font.bold = r == 0 or last
            cell.fill.solid(); cell.fill.fore_color.rgb = OURS if last else (RGBColor(0x37, 0x41, 0x51) if r == 0 else CARD)
            para.runs[0].font.color.rgb = WHITE if (r == 0 or last) else INK
    return t

s = p.slides.add_slide(CONTENT); title(s, "Swarm poisoning needs a different question")
tb(s, .45, 1.15, 6.2, .4, "One planted claim, stored under three different IDs", 14, True, INK)
for i, rid in enumerate(["#1702", "#4419", "#8830"]):
    y = 1.65 + i * .7
    box(s, .45, y, 1.5, .55, "Agent " + "ABC"[i], RGBColor(0x37, 0x41, 0x51), size=12)
    box(s, 2.05, y, 2.4, .55, "record " + rid + "\n“…main industry is fishing”", WARN, size=11)
    box(s, 4.55, y, 1.0, .55, "caught" if i == 0 else "missed", RGBColor(0x16, 0xa3, 0x4a) if i == 0 else RGBColor(0x9c, 0xa3, 0xaf), size=11)
    box(s, 5.65, y, 1.0, .55, "caught", OURS, size=11)
tb(s, 4.5, 1.35, 1.1, .3, "share ID", 10, True, MUTE, PP_ALIGN.CENTER); tb(s, 5.6, 1.35, 1.1, .3, "share claim", 10, True, OURS, PP_ALIGN.CENTER)
table(s, [("Prior focus", "AntiVenom's reframe", "What it revealed"),
          ("How a passage looks (clusters, attention)", "What the poison claims", "Stealth Lens protection, +11.8 pts clean"),
          ("Each agent defends itself; share IDs or trust", "A detection is a transferable antibody", "8% fooled vs 60% with shared IDs"),
          ("Filter every query", "The claim can be the trigger", "Gate restores clean accuracy, gives back protection")],
      6.95, 1.2, 5.95, 2.2, (2.0, 1.9, 2.05), 10.5)
tb(s, .45, 3.95, 12.4, .35, "Inspired by antivenom: each step of the treatment becomes a step of the defence", 13, True, INK)
steps = [("Capture a sample", "Catch one record"), ("Recognise the toxin, not the snake", "Distil the claim, not the ID"),
         ("Circulate everywhere", "Broadcast 257 bytes"), ("Treat on symptoms", "Act when the claim appears")]
for k, (a, b) in enumerate(steps):
    x = .45 + k * 3.15
    box(s, x, 4.4, 2.9, .65, "🐍 " + a, RGBColor(0xb4, 0x53, 0x09), size=12)
    box(s, x, 5.3, 2.9, .65, "🤖 " + b, OURS, size=12)
    arrow(s, x + 1.45, 5.05, x + 1.45, 5.3)
notes(s, "In a swarm a planted record reaches every agent, often renamed. Sharing an ID protects only agents whose copy has the same name. Prior defences ask how a passage looks or whether its source is trusted, and each agent decides alone. AntiVenom asks what the poison is trying to make agents believe: every working copy must carry that claim. The design mirrors antivenom: capture a sample, recognise the toxin rather than the snake, circulate, and treat only on symptoms.")

# ---------- 3. How it works, how we tested it ----------
s = p.slides.add_slide(CONTENT); title(s, "How AntiVenom works, and how we tested it")
pipe = [("Finder catches\none record", RGBColor(0x37, 0x41, 0x51)), ("Distil (Q, C)\n257-byte claim", OURS), ("Claim check\nNLI entailment ≥ 0.00217", OURS),
        ("+ attention\nfused score ≥ 0.0989", OURS), ("Delete + refill\nnext-ranked evidence", OURS), ("Gate (optional)\nact if max e ≥ 0.975", RGBColor(0xb4, 0x53, 0x09))]
for k, (t_, c_) in enumerate(pipe):
    x = .45 + k * 2.1
    box(s, x, 1.25, 1.9, 1.05, t_, c_, size=12)
    if k < 5: arrow(s, x + 1.9, 1.78, x + 2.1, 1.78)
tb(s, .45, 2.4, 12.4, .4, "Every receiver uses only the shared claim and its own reader; thresholds fixed on calibration at 5% clean removal; the reader is never fine-tuned.", 11, False, MUTE)
tl = [("📚 Calibration", "NQ 1–20 · all thresholds frozen"), ("🧪 Phase 1 · one receiver", "100 fresh questions vs CoordGuard and TrustRAG"),
      ("🐝 Phase 2 · swarm", "200 incidents × 3 receivers, 14 set-ups, 5 blocks; each test changes one factor")]
for k, (a, b) in enumerate(tl):
    x = .45 + k * 4.18
    card(s, x, 3.0, 3.95, 1.25, a, b, OURS, 12)
    if k < 2: arrow(s, x + 3.95, 3.62, x + 4.18, 3.62)
for k, (a, b) in enumerate([("Controls", "Same incidents, poisons and contexts for every set-up; sham and forged claims; random deletion; arm order shuffled; 5/5 drift checks identical."),
                            ("Pre-registered", "Protocol, incidents and code hashed before outcomes; a code check refuses any test that changes two settings."),
                            ("Scoring checked", "Rules vs blinded LLM judge (300 answers) and blinded human (58): about 94% and 89% rule accuracy.")]):
    card(s, .45 + k * 4.18, 4.5, 3.95, 1.65, a, b, MUTE, 11)
notes(s, "The finder turns one caught record into a question and a false claim. Each receiver checks its passages for that claim with an NLI model, optionally adds its reader's attention, deletes what matches and refills from the next-ranked evidence. We tested it in two pre-registered phases with one shared calibration: one receiver against published defences, then the swarm, one factor per test in five replicate blocks.")

# ---------- 4. Results ----------
s = p.slides.add_slide(CONTENT); title(s, "Results: published-defence protection, and every part matters")
tb(s, .45, 1.1, 5.6, .35, "Phase 1 · one receiver vs published defences", 13, True, INK)
pic(s, "../report/fig/parity.png", .45, 1.5, w=5.6)
card(s, .45, 3.85, 5.6, 2.3, "Matches CoordGuard, faster", "7% vs 5% fooled (no defence 76%); random deletion 64%, so the gain is detection. 18 s vs 25 s per question. With one poison: 3% vs 72% clean passages lost; without the prefix shortcut at matched recall: 9% vs 52%.", OURS, 11)
tb(s, 6.3, 1.1, 6.6, .35, "Phase 2 · the swarm, one factor per test (all 5 blocks)", 13, True, INK)
table(s, [("Question", "Result", "What it means"),
          ("Claim vs shared IDs?", "−52.0 pts", "60% → 8% fooled; IDs miss renamed copies"),
          ("Real vs sham claim?", "−47.3 pts", "Protection comes from the claim's content"),
          ("Claim with vs without question?", "−11.2 pts", "The question scopes the claim"),
          ("Add the reader's attention?", "−6.8 pts", "1% fooled, but −13 pts clean"),
          ("Delete vs warn?", "−9.2 pts", "Remove poison, don't argue with it"),
          ("Refill vs delete only?", "+3.7 pts acc.", "Refill turns removals into right answers"),
          ("Claim vs raw record?", "+5.8 pts", "Record blocks more on near-copies")],
      6.3, 1.5, 6.6, 4.3, (2.35, 1.25, 3.0), 10.5)
tb(s, 6.3, 5.95, 6.6, .4, "Differences in endorsement unless noted; 95% CIs exclude zero; Holm-corrected p < 0.001.", 10, False, MUTE)
notes(s, "Phase 1: one receiver alone blocks as well as CoordGuard and TrustRAG, faster, and loses far fewer clean passages when the benchmark's shortcuts are removed. Phase 2: in the swarm, the claim cut fooled receivers from 60% to 8%; its content and its question matter; attention adds protection at a clean cost; deleting beats warning; refilling helps. Against our prediction, the raw record blocks slightly more on these near-duplicate poisons.")

# ---------- 5. Scorecard, costs, conclusion ----------
s = p.slides.add_slide(CONTENT); title(s, "Where AntiVenom stands, what it costs, what it means")
table(s, [("Defence", "Protects others?", "Fooled", "Clean vs untreated"),
          ("Shared record IDs", "only if names match", "60.2%", "0.0"),
          ("Raw record + cosine", "yes; sends record", "2.3%", "−3.0"),
          ("BinaryShield-style fingerprint", "yes", "2.3%", "−2.3"),
          ("Stealth Lens", "no", "9.3%", "−13.0"),
          ("Self-check prompt", "no", "59.0%", "+0.2"),
          ("AntiVenom claim + attention", "yes; 257-byte claim", "1.3%", "−13.3"),
          ("AntiVenom claim", "yes; 257-byte claim", "8.2%", "−1.2")],
      .45, 1.15, 7.0, 3.4, (2.6, 1.85, 1.0, 1.55), 10.5, hl_last=True)
pic(s, "../report/fig/sprint_tradeoff.png", 7.7, 1.1, h=3.45)
card(s, .45, 4.75, 6.1, 1.45, "Costs, reported", "Raw record blocks more on near-duplicate poisons. The gate as calibrated lets 31% of attacks through. A forged claim costs 17.7 pts clean: authenticate claims.", WARN, 11)
card(s, 6.8, 4.75, 6.1, 1.45, "Conclusion", "Share what the poison claims, not where it is stored. One 257-byte claim protects a swarm at almost no clean cost; next: diverse, adaptive poisons.", OURS, 11)
notes(s, "The scorecard puts every defence on the same two axes from the swarm phase. Identifiers protect nobody. Content-based messages protect; among them, the claim keeps clean accuracy closest to untreated, and it matches the Stealth Lens filter's protection with 11.8 points more clean accuracy. We report the costs: the record blocks more on near-copies, the gate gives back protection, and forged claims cause harm, so claims must be authenticated.")

p.save("ANTIVENOM_5slide.pptx"); print("saved")
