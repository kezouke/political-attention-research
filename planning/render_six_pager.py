"""Render the review memo as six readable, self-contained PDF pages."""
from pathlib import Path
import re
from html import escape
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'planning/research-six-pager-ru.md'
OUTPUT = ROOT / 'output/pdf/political-economy-research-six-pager-ru.pdf'
FONT_DIR = Path('/System/Library/Fonts/Supplemental')
for name, fname in [
    ('Memo', 'Times New Roman.ttf'),
    ('Memo-Bold', 'Times New Roman Bold.ttf'),
    ('Memo-Italic', 'Times New Roman Italic.ttf'),
    ('Memo-BoldItalic', 'Times New Roman Bold Italic.ttf'),
    ('MemoSans', 'Arial.ttf'),
    ('MemoSans-Bold', 'Arial Bold.ttf'),
]:
    pdfmetrics.registerFont(TTFont(name, str(FONT_DIR / fname)))
pdfmetrics.registerFontFamily('Memo', normal='Memo', bold='Memo-Bold',
                             italic='Memo-Italic', boldItalic='Memo-BoldItalic')

INK = HexColor('#192127')
MUTED = HexColor('#56616a')
ACCENT = HexColor('#243e51')
RULE = HexColor('#bcc5cb')
WIDTH, HEIGHT = A4
LEFT = 51
TEXT_WIDTH = WIDTH - 2 * LEFT

BODY = ParagraphStyle('body', fontName='Memo', fontSize=11.5, leading=14.65,
                      textColor=INK, spaceAfter=8.2, allowWidows=0, allowOrphans=0)
TITLE = ParagraphStyle('title', fontName='Memo-Bold', fontSize=20, leading=23,
                       textColor=INK, spaceAfter=11)
SECTION = ParagraphStyle('section', fontName='Memo-Bold', fontSize=14.5, leading=18.2,
                         textColor=INK, spaceAfter=14)
META = ParagraphStyle('meta', fontName='MemoSans', fontSize=8.7, leading=11.3,
                      textColor=MUTED, spaceAfter=14)
REF = ParagraphStyle('refs', fontName='Memo', fontSize=9, leading=11.5,
                     textColor=MUTED)

def markup(text):
    result = escape(text)
    result = re.sub(r'\[([^\]]+)\]\((https?://[^)]+)\)',
                    lambda m: f'<a href="{m[2]}" color="#243e51"><u>{m[1]}</u></a>', result)
    result = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', result)
    return result

def para(text, style):
    return Paragraph(markup(text), style)

def measure(p):
    return p.wrap(TEXT_WIDTH, HEIGHT)[1]

def draw(p, y):
    h = measure(p)
    p.drawOn(c, LEFT, y - h)
    return y - h - p.style.spaceAfter

text = SOURCE.read_text()
for bad in ['\u2014', '\u2011', '\u2013']:
    assert bad not in text, f'Unexpected dash {bad!r}'
pages = text.split('---PAGE---')
assert len(pages) == 6
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
c = canvas.Canvas(str(OUTPUT), pagesize=A4, pageCompression=1)
c.setTitle('Когда кризис меняет политический выбор: план исследования')
c.setAuthor('Елисей Смирнов / Codex')
c.setSubject('Шестистраничная исследовательская записка для согласования, 6 ноября 2026')
c.setKeywords('политическая экономия, популизм, кризис, исследовательский план, six-pager')

overflows = []
for page_num, raw in enumerate(pages, 1):
    main, refs = raw.split(':::sources')
    refs = refs.rsplit(':::', 1)[0].strip()
    blocks = [p.strip() for p in main.strip().split('\n\n') if p.strip()]
    section_heading = next(p[3:] for p in blocks if p.startswith('## '))
    c.bookmarkPage(f'section-{page_num}')
    c.addOutlineEntry(section_heading, f'section-{page_num}')
    c.setFont('MemoSans-Bold', 8.1)
    c.setFillColor(ACCENT)
    c.drawString(LEFT, HEIGHT - 30, 'POLITICAL ATTENTION RESEARCH')
    c.setFont('MemoSans', 8.1)
    c.setFillColor(MUTED)
    c.drawRightString(WIDTH - LEFT, HEIGHT - 30, 'Для согласования · 06.11.2026')
    c.setStrokeColor(RULE)
    c.setLineWidth(.45)
    c.line(LEFT, HEIGHT - 40, WIDTH - LEFT, HEIGHT - 40)

    content = []
    for block in blocks:
        if block.startswith('# '):
            content.append(para(block[2:], TITLE))
        elif block.startswith('## '):
            content.append(para(block[3:], SECTION))
        elif block.startswith('**Исследовательская записка'):
            content.append(para(block.replace('**', ''), META))
        else:
            content.append(para(block, BODY))
    reference = para(refs, REF)
    ref_h = measure(reference)
    ref_top = 50 + ref_h
    min_body_bottom = ref_top + 23
    y = HEIGHT - 60
    need = sum(measure(p) + p.style.spaceAfter for p in content)
    available = y - min_body_bottom
    print(f'page {page_num}: {len(main.split())} words, body {need:.1f}pt / {available:.1f}pt available; refs {ref_h:.1f}pt')
    if need > available:
        overflows.append(f'Page {page_num} overflows by {need - available:.1f}pt. Edit prose or layout.')
    for p in content:
        y = draw(p, y)
    c.setLineWidth(.35)
    c.setStrokeColor(RULE)
    c.line(LEFT, ref_top + 8, WIDTH - LEFT, ref_top + 8)
    reference.drawOn(c, LEFT, 50)
    c.setFont('MemoSans', 8)
    c.setFillColor(MUTED)
    c.drawString(LEFT, 27, 'Исследовательская записка · версия 1.0')
    c.drawRightString(WIDTH - LEFT, 27, f'{page_num} / 6')
    c.showPage()
if overflows:
    raise ValueError('\n'.join(overflows))
c.save()
print(OUTPUT)
