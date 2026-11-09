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


# ---------- 1. Title ----------
s = p.slides.add_slide(TITLE)
s.placeholders[100].text = "One Captured Poison, a Protected Swarm"
s.placeholders[101].text = "AntiVenom: turning one detected poisoned record into a shareable antibody for agent swarms"
tb(s, .6, 3.05, 12.1, .7, "Daniel Foo · Nanyang Technological University (NTU), Singapore\nApart Research Swarm Alignment Hackathon, 6–8 November 2026 · Track 4: Multi-Agent Oversight and Control", 14, False, WHITE)
stats = [("76% → 7%", "agents endorsing a planted false answer: no defence → AntiVenom, on 100 fresh pre-registered questions"),
         ("62% → 9%", "swarm receivers fooled when the finder shares record IDs → when it shares the claim signature"),
         ("15% vs 21%", "good evidence thrown away by AntiVenom vs the CoordGuard baseline, at the same attack-blocking level")]
for i, (a, b) in enumerate(stats):
    x = .6 + i * 4.1
    tb(s, x, 4.15, 3.8, .8, a, 34, True, RGBColor(0x5e, 0xea, 0xd4))
    tb(s, x, 4.95, 3.7, .95, b, 12, False, WHITE)
tb(s, .6, 6.75, 12.1, .4, "Builds on the author's preexisting AntiVenom code (marked as such); weekend work is listed on slide 5.", 11, False, RGBColor(0xd1, 0xd5, 0xdb))
notes(s, "I'm Daniel Foo from NTU. Agents in a swarm share memory and retrieval, so one planted record can mislead many of them. "
         "AntiVenom takes one poisoned record that an agent has caught, turns it into a small claim signature, and shares that signature so the other agents can neutralise their own copies. "
         "Three numbers: it cuts false-answer endorsement from 76% to 7% on a pre-registered fresh test; sharing the signature instead of record IDs cuts fooled receivers from 62% to 9%; "
         "and it throws away less good evidence than CoordGuard: 15% of clean passages against 21%.")

# ---------- 2. Why it is new ----------
s = p.slides.add_slide(CONTENT); title(s, "What's new: share what the poison says, not where it is")
# left: illustration of three receivers with renamed copies
tb(s, .45, 1.2, 6.2, .4, "Same planted claim, three different record IDs", 14, True, INK)
for i, rid in enumerate(["#1702", "#4419", "#8830"]):
    y = 1.75 + i * .78
    box(s, .45, y, 1.6, .6, "Receiver " + "BCD"[i], RGBColor(0x37, 0x41, 0x51), size=12)
    box(s, 2.2, y, 2.3, .6, "record " + rid + "\n“…main industry is fishing”", WARN, size=11)
    ok_id = i == 0
    box(s, 4.65, y, .95, .6, "caught" if ok_id else "missed", RGBColor(0x16, 0xa3, 0x4a) if ok_id else RGBColor(0x9c, 0xa3, 0xaf), size=11)
    box(s, 5.7, y, .95, .6, "caught", RGBColor(0x16, 0xa3, 0x4a), size=11)
tb(s, 4.55, 1.38, 1.2, .4, "Share ID", 11, True, MUTE, PP_ALIGN.CENTER)
tb(s, 5.6, 1.38, 1.2, .4, "Share claim", 11, True, OURS, PP_ALIGN.CENTER)
tb(s, .45, 4.05, 6.3, .5, "Measured over 80 incidents: sharing IDs leaves 62% of receivers fooled; sharing the claim signature, 9%.", 11, False, INK)
box(s, .45, 4.95, 12.45, .38, "Prior defences ask: does this passage look suspicious? is its source trusted?   AntiVenom asks: what is the poison trying to make agents believe?", RGBColor(0x37, 0x41, 0x51), size=12)
# right: what each defence shares after a detection
rows = [("Defence", "Shares after a detection", "Renamed copies", "No training"),
        ("TrustRAG, CoordGuard", "nothing", "–", "●"),
        ("Shared record IDs", "record IDs", "○", "●"),
        ("MAPLE-Guard", "trust scores", "◐", "○"),
        ("SecureCollaRAG", "source reliability", "◐", "○"),
        ("PerMIT", "verdicts on exact bytes", "○", "○"),
        ("AgentAntibody", "nothing (one agent)", "●", "●"),
        ("AntiVenom", "the false claim, ~250 B", "●", "●")]
t = s.shapes.add_table(len(rows), 4, Emu(int(6.95 * IN)), Emu(int(1.2 * IN)), Emu(int(5.95 * IN)), Emu(int(3.35 * IN))).table
for c, w in enumerate((1.75, 2.3, 1.0, .9)): t.columns[c].width = Emu(int(w * IN))
for r, row in enumerate(rows):
    for c, v in enumerate(row):
        cell = t.cell(r, c); cell.text = v
        para = cell.text_frame.paragraphs[0]; para.runs[0].font.size = Pt(10.5)
        if c >= 2: para.alignment = PP_ALIGN.CENTER
        para.runs[0].font.bold = r in (0, len(rows) - 1)
        cell.fill.solid(); cell.fill.fore_color.rgb = OURS if r == len(rows) - 1 else (RGBColor(0x37, 0x41, 0x51) if r == 0 else CARD)
        para.runs[0].font.color.rgb = WHITE if r in (0, len(rows) - 1) else (OURS if v == "●" else INK)
tb(s, 6.95, 4.58, 5.95, .3, "● yes   ◐ partly   ○ no   – not applicable. Prior defences' entries read from their papers.", 9, False, MUTE)
# bottom: three novelty points
pts = [("1  The unit of sharing is the claim", "It survives renamed and paraphrased copies, because receivers check meaning, not identity."),
       ("2  Two recognisers", "A specific one (entails the shared claim?) and a general one (the reader's own attention) that catches what entailment misses."),
       ("3  One capture, no training", "One caught record is enough. No model training, no infrastructure, weights unchanged.")]
for i, (h, b) in enumerate(pts):
    card(s, .45 + i * 4.18, 5.45, 4.0, 1.25, h, b, OURS, 11)
notes(s, "What is new. Today, when one agent detects poison, the others learn little: single-agent defences share nothing, and multi-agent ones share trust scores or verdicts tied to exact bytes. "
         "The left side shows why that fails. The same false claim reaches three receivers under three different record IDs. Sharing the ID protects one of them; sharing the claim protects all three. "
         "Measured over 80 incidents, that is 62% of receivers fooled against 9%. Three things are new together: the claim is the unit of sharing, it is checked by two recognisers, and one capture with no training is enough. "
         "The closest idea, AgentAntibody, reuses abstract antibodies inside one agent against prompt injection; we share them across a swarm against poisoning. The deeper change is the question: prior defences ask whether a passage looks suspicious or a source is trusted; we ask what the poison is trying to make agents believe, which is the one thing an attacker cannot drop.")

# ---------- 3. Worked example ----------
s = p.slides.add_slide(CONTENT); title(s, "What happens: one real question, step by step")
steps = [("Capture", "Finder catches one planted record"), ("Signature", "Reader extracts question + false claim"),
         ("Broadcast", "~250 bytes to every agent"), ("Check", "Each receiver scores its own passages"), ("Neutralise", "Remove flagged, refill, answer")]
for i, (h, b) in enumerate(steps):
    x = .45 + i * 2.55
    box(s, x, 1.15, 2.2, .78, h + "\n" + b, OURS if i in (1, 3) else RGBColor(0x37, 0x41, 0x51), size=12)
    if i < 4: arrow(s, x + 2.2, 1.54, x + 2.55, 1.54)
card(s, .45, 2.15, 4.2, 3.75, "The incident",
     "Question: “What is the main industry in the Canadian Shield?”\n\n"
     "Caught record: “…its primary income sector is not mining but rather fishing…”\n\n"
     "Signature shared: question “What is the main industry in the Canadian Shield?” + claim “not mining but rather fishing”. Receivers test: The answer to the question … is not mining but rather fishing.\n\n"
     "No defence answers: “fishing.”\nDefended answer: “Mining is the main industry in the Canadian Shield.”", OURS, 11)
pic(s, "fig/worked.png", 4.85, 2.15, w=8.1)
box(s, .45, 6.05, 12.45, .42, "Why it works: a poison has to state its false claim to work, and stating it is exactly what AntiVenom detects. Rewording escapes the claim check, but not the reader's attention.", OURS, size=12)
tb(s, 4.95, 5.55, 8, .5, "Real values from NQ question test363 (development set). Four planted passages entail the claim; the fifth is caught only by attention. No clean passage is removed.", 10, False, MUTE)
notes(s, "Here is what actually happens, on one real question: what is the main industry in the Canadian Shield? The true answer is mining. Five planted passages say fishing. "
         "One agent catches one of them. The reader turns it into a signature, the question plus the false claim, and broadcasts it. "
         "A receiver then scores its own ten passages. The signature check catches four planted passages, because they assert the claim. The fifth says it differently and slips past, "
         "but the reader's attention is drawn to it, so the attention check catches it. No clean passage crosses either line. The five are removed, the gaps refilled, and the answer flips from fishing back to mining. Why it works: a poison has to state its false claim to work, and that is exactly what we check; clean evidence almost never states it, and rewording that escapes the claim check still draws the reader's attention.")

# ---------- 4. Results ----------
s = p.slides.add_slide(CONTENT); title(s, "Matches the state of the art, and keeps more good evidence")
pic(s, "fig/parity.png", .35, 1.15, w=7.2)
tb(s, .45, 3.95, 4.8, 1.0, "Pre-registered fresh test, 100 questions: blocking is the same as CoordGuard and TrustRAG (no difference survives correction). Deleting the same number of passages at random leaves 64% fooled. Rule-scored; one-poison, no-prefix and timing are development data.", 11, False, INK)
pic(s, "fig/precision3d.png", 7.65, 1.05, h=2.95)
tb(s, 10.55, 1.3, 2.4, 1.6, "Less good evidence discarded than CoordGuard: 15% vs 21%, and far less with one poison or no prefix.", 12, True, OURS)
pic(s, "fig/latency.png", .45, 4.8, h=1.55)
tb(s, 3.4, 5.1, 1.7, 1.3, "Faster: 18 s vs 25 s and 36 s.", 12, True, OURS)
pic(s, "fig/failure.png", 5.4, 4.2, h=2.1)
tb(s, 9.45, 4.55, 3.45, 1.6, "Fails safely: says “don't know” instead of inventing an answer (16% wrong vs 43% for TrustRAG).", 12, True, OURS)
box(s, .45, 6.38, 12.45, .42, "vs CoordGuard:  same blocking (7% vs 5%)  ·  good evidence lost 15% vs 21%  ·  one poison 3% vs 72%  ·  18 s vs 25 s  ·  no training", OURS, size=12)
notes(s, "Results. On the pre-registered fresh test, AntiVenom blocks the attack as well as CoordGuard and TrustRAG; none of the differences survives correction, so this is parity. "
         "The random-deletion control shows the effect comes from detection. Beyond parity, it discards less good evidence than CoordGuard, 15% against 21%, and far less with one poison or without the prefix; it is faster than both, "
         "and when it fails it says it does not know instead of inventing an answer. The caveat: simple cosine similarity to the caught record shares many of the precision gains.")

# ---------- 5. Swarm + design rules ----------
s = p.slides.add_slide(CONTENT); title(s, "In a swarm: the trade-off, the rules, and this weekend's test")
pic(s, "fig/swarm.png", .4, 1.15, w=6.4)
rules = [("1", "Share the claim, not the ID", "IDs miss renamed copies (62% fooled); the signature catches them (9%)."),
         ("2", "Cut only on evidence of the claim", "Signature alone keeps clean accuracy (52% vs 53%); ungated attention drops it to 33%."),
         ("3", "Pair a specific signal with a general one", "Signature + attention survives the unluckiest capture (95%).")]
for i, (n, h, b) in enumerate(rules):
    y = 1.2 + i * 1.0
    box(s, 7.05, y, .5, .5, n, OURS, size=15, shape=MSO_SHAPE.OVAL)
    tb(s, 7.7, y - .06, 5.2, .4, h, 13, True, INK); tb(s, 7.7, y + .3, 5.2, .6, b, 11, False, INK)
card(s, 7.05, 4.2, 5.85, 1.9, "This weekend (judged work)",
     "Gated signature sharing on fresh incidents, against shared IDs, cosine, SecureCollaRAG (trained source-reliability filter) and MAPLE-Guard's retrieval gate. "
     "Measures protection and clean accuracy; blind human scoring.", CG, 11)
box(s, .45, 6.12, 12.45, .5, "When one agent finds poison, share what it says, and act only where it is said.", CG, size=15)
tb(s, .45, 6.68, 12.4, .6, "Limits: rule-scored, human labels pending; one main reader (Mistral transfers; Llama claim extraction failed); cosine matches us in question answering; "
                          "serial homogeneous agents, not autonomous contagion; non-adaptive attacker.", 10, False, MUTE)
notes(s, "In a swarm, sharing the claim instead of the ID cuts fooled receivers from 62% to 9% with clean accuracy unchanged. Adding attention blocks almost everything but costs clean accuracy, "
         "so attention should only act once the signature has matched. Three design rules follow. This weekend's judged test runs that gated version on fresh incidents, "
         "against shared IDs, cosine and two published multi-agent defences, SecureCollaRAG and MAPLE-Guard's retrieval gate, with blind human scoring. Thank you.")

p.save("AntiVenom_5slide.pptx"); print("saved")
