"""Makes the small test files (a PDF, a Word file, a text file) that the browser tests upload. Usage: python e2e/make_test_files.py <folder>"""
import sys
import textwrap
from pathlib import Path

out = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/e2e_files")
out.mkdir(parents=True, exist_ok=True)
text = ("Photosynthesis converts light energy into chemical energy inside chloroplasts. Chlorophyll absorbs red and blue light and reflects green light. "
        "The light reactions produce ATP and NADPH in the thylakoid membranes. The Calvin cycle uses ATP and NADPH to build glucose from carbon dioxide in the stroma. "
        "Stomata are small pores in leaves that let carbon dioxide enter and oxygen leave. Respiration releases the energy stored in glucose inside mitochondria. ") * 2
(out / "notes.txt").write_text(text)
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
c = canvas.Canvas(str(out / "photosynthesis.pdf"), pagesize=A4)
y = 800
for line in textwrap.wrap(text, 90):
    c.drawString(40, y, line)
    y -= 16
c.save()
import docx
d = docx.Document()
d.add_paragraph(text)
d.save(str(out / "lesson.docx"))
(out / "fake.pdf").write_text("this is not really a pdf")
print("test files written to", out)
