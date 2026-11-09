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
s.placeholders[100].text = "AntiVenom: One Captured Poison, a Protected Swarm"
s.placeholders[101].text = "Which parts of a shared claim warning protect agents, what they cost, and how they can be misused"
tb(s, .6, 3.05, 12.1, .7, "Daniel Foo · Nanyang Technological University (NTU), Singapore\nApart Research Swarm Alignment Hackathon, 6–8 November 2026 · Track 4: Multi-Agent Oversight and Control", 14, False, WHITE)
for i, (a, b) in enumerate([("60% → 8%", "receivers fooled: shared IDs → shared claim (200 incidents, all 5 blocks, no clean loss beyond 5 points)"),
                            ("2% vs 8%", "against our prediction: sharing the raw record protected slightly more than the claim"),
                            ("−18 pts", "clean accuracy lost to a forged claim: shared claims must be authenticated")]):
    x = .6 + i * 4.1
    tb(s, x, 4.15, 3.8, .8, a, 30, True, RGBColor(0x5e, 0xea, 0xd4))
    tb(s, x, 4.95, 3.7, .95, b, 12, False, WHITE)
tb(s, .6, 6.75, 12.1, .4, "Builds on the author's unpublished earlier prototype (disclosed in the report). All results shown were run during the sprint.", 11, False, RGBColor(0xd1, 0xd5, 0xdb))
notes(s, "When one agent confirms a poisoned record, what should it tell the others? AntiVenom passes a question-scoped false claim. Instead of claiming it beats everything, we took it apart and tested each piece with one factor changed at a time, on 200 incidents in five replicate blocks. Three results: sharing the claim cut fooled receivers from 60% to 8%; sharing the raw record did slightly better, against our prediction; and a forged claim costs clean accuracy, so claims need authentication.")

# ---------- 2. The idea ----------
s = p.slides.add_slide(CONTENT); title(s, "The idea: share what the poison claims, not where it is")
tb(s, .45, 1.2, 6.2, .4, "Same planted claim, three different record IDs", 14, True, INK)
for i, rid in enumerate(["#1702", "#4419", "#8830"]):
    y = 1.75 + i * .78
    box(s, .45, y, 1.6, .6, "Receiver " + "BCD"[i], RGBColor(0x37, 0x41, 0x51), size=12)
    box(s, 2.2, y, 2.3, .6, "record " + rid + "\n“…main industry is fishing”", WARN, size=11)
    box(s, 4.65, y, .95, .6, "caught" if i == 0 else "missed", RGBColor(0x16, 0xa3, 0x4a) if i == 0 else RGBColor(0x9c, 0xa3, 0xaf), size=11)
    box(s, 5.7, y, .95, .6, "checked", OURS, size=11)
tb(s, 4.55, 1.38, 1.2, .4, "Share ID", 11, True, MUTE, PP_ALIGN.CENTER)
tb(s, 5.6, 1.38, 1.2, .4, "Share claim", 11, True, OURS, PP_ALIGN.CENTER)
rows = [("Closest prior work", "What it shares", "In this sprint"),
        ("BinaryShield", "semantic fingerprint", "run (B3)"),
        ("Stealth Lens", "nothing; attention filter", "run (B2)"),
        ("A-MemGuard", "lesson in the prompt", "run (A8, T6)"),
        ("Raw record + cosine", "the record itself", "run (A2, T9)"),
        ("SeCon-RAG, MIRAGE, Membrane, Cordon-MAS", "checks, graphs, cards", "cited"),
        ("AntiVenom", "question-scoped false claim", "tested by stage")]
t = s.shapes.add_table(len(rows), 3, Emu(int(6.95 * IN)), Emu(int(1.2 * IN)), Emu(int(5.95 * IN)), Emu(int(3.2 * IN))).table
for c, w in enumerate((2.45, 2.0, 1.5)): t.columns[c].width = Emu(int(w * IN))
for r, row in enumerate(rows):
    for c, v in enumerate(row):
        cell = t.cell(r, c); cell.text = v; para = cell.text_frame.paragraphs[0]; para.runs[0].font.size = Pt(10.5)
        para.runs[0].font.bold = r in (0, len(rows) - 1)
        cell.fill.solid(); cell.fill.fore_color.rgb = OURS if r == len(rows) - 1 else (RGBColor(0x37, 0x41, 0x51) if r == 0 else CARD)
        para.runs[0].font.color.rgb = WHITE if r in (0, len(rows) - 1) else INK
card(s, .45, 4.75, 12.45, 1.4, "Inspired by antivenom", "Antivenom is raised from a small captured sample, recognises the toxin rather than the snake, circulates everywhere, and is given only on signs of envenoming. AntiVenom mirrors each step: one confirmed record, a claim not an ID, broadcast, and a gate on evidence of the claim. A design hypothesis, tested below, not a guarantee.", OURS, 11)
notes(s, "If the finder shares the record's ID, receivers whose copies are named differently are not protected. Sharing what the record claims lets each receiver look for that claim. The idea sits next to close prior work: BinaryShield shares fingerprints, A-MemGuard reuses lessons, Stealth Lens filters by attention. We run the closest of these, and make no claim to be first.")

# ---------- 3. Experiment ----------
s = p.slides.add_slide(CONTENT); title(s, "The experiment: one question per stage, one factor per test")
stages = [("S0 Setup", "attack works?", "C0/C1"), ("S1 What to share", "claim vs IDs · record vs IDs · claim vs record", "T1 · T1b · T9"),
          ("S2 Content", "real vs sham · with vs without question", "T2 · T8"), ("S3 Detection", "attention adds?", "T3"),
          ("S4 Neutralise", "delete vs warn · refill", "T6 · T5"), ("S5 Normal use", "gate on vs off", "T4"), ("S6 Misuse", "forged claim", "T7")]
for i, (h, q, tst) in enumerate(stages):
    x = .45 + i * 1.79
    box(s, x, 1.25, 1.65, 1.55, h + "\n" + q, OURS if i in (1, 2, 3) else RGBColor(0x37, 0x41, 0x51), size=11)
    tb(s, x, 2.85, 1.65, .4, tst, 12, True, OURS, PP_ALIGN.CENTER)
    if i < 6: arrow(s, x + 1.65, 2.02, x + 1.79, 2.02)
for i, (h, b) in enumerate([("Controls", "Same incidents, poisons, receivers and contexts for every arm. Thresholds frozen on calibration (5% clean removal each). Arm order shuffled; drift checked."),
                            ("Replication", "200 incidents (HotpotQA + MS MARCO) in 5 blocks of 40, each with its own seeds. Results per block and pooled; T1 primary, Holm for the rest."),
                            ("Pre-registered", "Protocol, incidents and code hashed and committed before any answer existed. A code check enforces one factor per test. Claims ledger with nulls fixed.")]):
    card(s, .45 + i * 4.18, 3.5, 4.0, 1.9, h, b, OURS, 11)
box(s, .45, 5.65, 12.45, .5, "Benchmarks (descriptive only): B1 self-check prompt · B2 Stealth Lens attention filter · B3 BinaryShield-style shared fingerprint", RGBColor(0x37, 0x41, 0x51), size=13)
notes(s, "Last sprint's feedback was that we changed too many things at once. So this time every test changes exactly one setting, enforced in code, and every claim maps to one test. Seven stages of an incident, eleven tests, five replicate blocks, all frozen before any result existed. Three external benchmarks show where AntiVenom sits, but never support a causal claim.")

# ---------- 4. Results ----------
s = p.slides.add_slide(CONTENT); title(s, "Results: what each part contributes")
pic(s, "../report/fig/sprint_forest.png", .35, 1.15, w=8.1)
card(s, 8.6, 1.2, 4.3, 1.7, "T1 primary: supported", "Claim vs IDs: -52.0 points [-57.0, -46.7], all 5 blocks. IDs gave zero protection: every copy was renamed.", OURS, 11)
card(s, 8.6, 3.05, 4.3, 1.45, "In the predicted direction", "Content matters (T2), the question matters (T8), attention adds (T3), removal beats warning (T6), refill helps (T5).", OURS, 11)
card(s, 8.6, 4.65, 4.3, 1.45, "Against the prediction", "T9: the raw record protected more than the claim (2% vs 8%). Gate (T4) gave back protection.", WARN, 11)
tb(s, .45, 6.3, 12.4, .5, "Rule-scored, cross-checked by a blinded LLM judge (κ 0.84 / 0.87); human adjudication of 58 rows pending. Effects: paired, per incident; Holm-corrected.", 10, False, MUTE)
notes(s, "Here is every test. T1, the primary: sharing the claim cut endorsement by 52 points, in all five blocks, and IDs did nothing because every copy was renamed. Every component behaved as predicted, with two exceptions in amber. Sharing the raw record protected a bit more than the claim, which we put down to PoisonedRAG's near-duplicate poisons, and the gate restored clean accuracy but gave back most of the protection.")

# ---------- 5. Cost, misuse, benchmarks ----------
s = p.slides.add_slide(CONTENT); title(s, "Costs, misuse, and where it sits among benchmarks")
pic(s, "../report/fig/sprint_tradeoff.png", .4, 1.15, h=3.75)
card(s, 7.05, 1.2, 5.85, 1.15, "Gate (T4)", "Clean accuracy back to untreated, but endorsement rose from 1% to 31%: as calibrated it fires too rarely.", WARN, 11)
card(s, 7.05, 2.45, 5.85, 1.15, "Forged claim (T7)", "A true answer sent as 'false' cost 18 points of clean accuracy: authenticate shared claims.", WARN, 11)
card(s, 7.05, 3.7, 5.85, 1.2, "Benchmarks", "Stealth Lens: 9% fooled, −13 pts clean; the claim matches it with better clean accuracy. Fingerprint ≈ raw record (2%).", BENCH if False else CG, 11)
card(s, .45, 5.0, 12.45, 1.15, "Limits", "Previously used questions; near-duplicate poisons; non-adaptive attacker; one reader (Qwen2.5-7B); serial homogeneous agents; capture assumed; claim checks cannot catch true-but-misapplied evidence (Lazy Grounding).", MUTE, 11)
notes(s, "What does it cost? Attention buys protection at a clean cost. The gate restores clean accuracy but lets about a third of attacks through as calibrated. A forged claim removes good evidence, so shared claims must be authenticated. Among benchmarks, the claim matches Stealth Lens protection with better clean accuracy, and a BinaryShield-style fingerprint matches the raw record. The lesson: share content, not identifiers; and on diverse, adaptive poisons the claim may earn more than here.")

p.save("ANTIVENOM_5slide.pptx"); print("saved")
