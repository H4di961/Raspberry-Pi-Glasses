from pathlib import Path
import hashlib
import html
import json
import re
import textwrap
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Preformatted
from reportlab.platypus.tableofcontents import TableOfContents
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs'
styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name='BodyGuide', fontName='Helvetica', fontSize=10, leading=15, spaceAfter=8))
styles.add(ParagraphStyle(name='ChapterGuide', fontName='Helvetica-Bold', fontSize=20, leading=25, spaceAfter=18))
styles.add(ParagraphStyle(name='SectionGuide', fontName='Helvetica-Bold', fontSize=12, leading=16, spaceBefore=13, spaceAfter=8))
styles.add(ParagraphStyle(name='CodeGuide', fontName='Courier', fontSize=7.5, leading=10, leftIndent=8, spaceAfter=8, backColor=colors.HexColor('#f2f3f5'), borderPadding=5))
styles.add(ParagraphStyle(name='CoverGuide', fontName='Helvetica-Bold', fontSize=32, leading=38, spaceAfter=24))
styles.add(ParagraphStyle(name='SubGuide', fontName='Helvetica', fontSize=15, leading=23, textColor=colors.HexColor('#43515e'), spaceAfter=20))

class GuideDoc(SimpleDocTemplate):
    def afterFlowable(self, flowable):
        if isinstance(flowable, Paragraph) and flowable.style.name == 'ChapterGuide':
            title = flowable.getPlainText()
            key = 'chapter-' + hashlib.sha256(title.encode()).hexdigest()[:16]
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(title, key, 0)
            self.notify('TOCEntry', (0, title, self.page, key))

def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor('#ccd2d8'))
    canvas.line(46, 40, A4[0]-46, 40)
    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(colors.HexColor('#52606d'))
    canvas.drawString(46, 27, 'PI-project_glasses | Technical guide | 15 September 2026')
    canvas.drawRightString(A4[0]-46, 27, str(doc.page))
    canvas.restoreState()

def escaped(text):
    safe = html.escape(text)
    return re.sub(r'https?://[^\s<>]+', lambda m: '<link href="'+m.group(0)+'" color="#245b87">'+m.group(0)+'</link>', safe)

story = [Spacer(1, 55), Paragraph('PI-project_glasses', styles['CoverGuide']),
         Paragraph('From the camera to the chess move', styles['SubGuide']),
         Paragraph('A detailed command reference and explanation of your Raspberry Pi glasses project.', styles['SubGuide']),
         Spacer(1, 25), Paragraph('Pi Zero 2 W + Camera Module 3 Wide NoIR<br/>Phone browser + Windows PC chess mode', styles['BodyGuide']),
         Spacer(1, 30), Paragraph('Includes setup, services, streaming, Gemini, browser inference, board tracking, Stockfish, troubleshooting and annotated source locations.', styles['BodyGuide']),
         Spacer(1, 30), Paragraph('Status: live camera and experimental chess controller implemented. Actual piece recognition on your chess set has not yet been validated.', styles['BodyGuide']), PageBreak(),
         Paragraph('Contents', styles['Heading1'])]
toc = TableOfContents()
toc.levelStyles = [ParagraphStyle(name='TOCGuide', fontName='Helvetica', fontSize=10, leading=15, spaceBefore=5, rightIndent=24)]
story.extend([toc, PageBreak()])

def add_code(lines, numbered=False):
    wrapped = []
    for i, line in enumerate(lines, 1):
        prefix = f'{i:4d}  ' if numbered else ''
        chunks = textwrap.wrap(line.expandtabs(4), width=96-len(prefix), replace_whitespace=False, drop_whitespace=False, break_long_words=True, break_on_hyphens=False) or ['']
        wrapped.append(prefix+chunks[0])
        wrapped.extend(('      ' if numbered else '  ')+part for part in chunks[1:])
    for start in range(0, len(wrapped), 32):
        story.append(Preformatted('\n'.join(wrapped[start:start+32]), styles['CodeGuide']))

def parse_markdown(text):
    paragraph = []
    code = None
    first = True
    def flush():
        if paragraph:
            story.append(Paragraph(escaped(' '.join(paragraph)), styles['BodyGuide']))
            paragraph.clear()
    for line in text.splitlines():
        if line.startswith('```'):
            flush()
            if code is None:
                code = []
            else:
                add_code(code)
                code = None
            continue
        if code is not None:
            code.append(line)
        elif line.startswith('# '):
            flush()
            if not first:
                story.append(PageBreak())
            first = False
            story.append(Paragraph(escaped(line[2:]), styles['ChapterGuide']))
        elif line.startswith('## '):
            flush()
            story.append(Paragraph(escaped(line[3:]), styles['SectionGuide']))
        elif not line.strip():
            flush()
        else:
            paragraph.append(line)
    flush()

parse_markdown((OUT/'PI-project_glasses-guide.md').read_text(encoding='utf-8-sig'))
manifest = {}
for relative in ['chess-mode/app.py', 'chess-mode/game.py', 'chess-mode/templates/chess.html', 'chess-mode/test_game.py', 'chess-mode/requirements.txt', 'chess-mode/probe_pieces.py']:
    path = ROOT/relative
    content = path.read_bytes()
    digest = hashlib.sha256(content).hexdigest()
    manifest[relative] = digest
    story.extend([PageBreak(), Paragraph(escaped('Source appendix: '+relative), styles['ChapterGuide']), Paragraph('Snapshot SHA-256: '+digest, styles['BodyGuide']), Paragraph('Line numbers refer to the original file. Indented continuation lines are print wrapping, not extra source lines. Use the original file for executable copies.', styles['BodyGuide'])])
    add_code(content.decode('utf-8-sig').splitlines(), numbered=True)

pdf = OUT/'PI-project_glasses-guide.pdf'
doc = GuideDoc(str(pdf), pagesize=A4, leftMargin=46, rightMargin=46, topMargin=48, bottomMargin=56, title='PI-project_glasses - Detailed technical guide', author='Project documentation', pageCompression=1)
doc.multiBuild(story, onFirstPage=footer, onLaterPages=footer)
reader = PdfReader(pdf)
text = '\n'.join(page.extract_text() or '' for page in reader.pages)
assert len(reader.pages) >= 20
assert 'Automatic startup with systemd' in text
assert 'Source appendix' in text
manifest['pdf_pages'] = len(reader.pages)
manifest['pdf_bytes'] = pdf.stat().st_size
manifest['guide_words'] = len((OUT/'PI-project_glasses-guide.md').read_text(encoding='utf-8-sig').split())
(OUT/'guide-manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
print(json.dumps(manifest, indent=2))
