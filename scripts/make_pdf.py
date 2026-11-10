#!/usr/bin/env python3
"""Render report/report.docx to report/report.pdf with LibreOffice and fill in the table of
contents.

LibreOffice does not update the table of contents during a headless conversion, so the page
numbers are computed here: the document is rendered, the page on which every heading appears is
read from the PDF (including the printed page number in the footer), the entries are written into
the TOC field of the DOCX, and the document is rendered again. This repeats until the page
numbers are stable (the TOC itself may push the following pages). Word can still update the
field normally (the document asks for it when it is opened).

The fonts of the template (Georgia, Open Sans) are copied into a private LibreOffice profile so
that the PDF uses the same fonts as Word.

Usage: python scripts/make_pdf.py
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

import pypdfium2 as pdfium
from lxml import etree

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_docx import NS, W, el, normalise, style_of, text_of  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DOCX = ROOT / "report" / "report.docx"
PDF = ROOT / "report" / "report.pdf"
SOFFICE = os.environ.get("SOFFICE", "/Applications/LibreOffice.app/Contents/MacOS/soffice")
FONT_DIRS = [Path("/System/Library/Fonts/Supplemental"), Path.home() / "Library/Fonts",
             Path("/Library/Fonts"), Path("C:/Windows/Fonts")]
FONT_PATTERNS = ("Georgia", "OpenSans", "Open Sans", "Courier New")

LEVEL = {"Nadpis1": 1, "Nadpis1neslovan": 1, "Nadpis2": 2, "Nadpis2plohy": 2, "Nadpis3": 3}


def headings(doc) -> list[tuple[int, str, str]]:
    """(level, number, title) of all headings of the main text and the appendices."""
    out, chapter, section, appendix = [], 0, 0, 0
    body = doc.find("w:body", NS)
    started = False
    for p in body.iter(W + "p"):
        st = style_of(p)
        if st not in LEVEL:
            continue
        title = text_of(p)
        if st == "Nadpis1neslovan" and title == "Introduction":
            started = True
        if not started:
            continue
        if st == "Nadpis1":
            chapter, section = chapter + 1, 0
            num = str(chapter)
        elif st == "Nadpis2":
            section += 1
            num = f"{chapter}.{section}"
        elif st == "Nadpis2plohy":
            appendix += 1
            num = f"Appendix {chr(64 + appendix)}:"
        else:
            num = ""
        out.append((LEVEL[st], num, title))
    return out


def page_labels(pdf) -> list[tuple[str, str]]:
    """(normalised text, printed page number) for every page."""
    pages = []
    for i in range(len(pdf)):
        text = pdf[i].get_textpage().get_text_range()
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        # the printed page number (footer) is extracted either as the first or the last line
        label = next((l for l in (lines[:1] + lines[-1:]) if re.fullmatch(r"[0-9]+|[IVXLC]+", l)), "")
        pages.append((re.sub(r"\s+", "", text), label))
    return pages


def locate(entries, pages, toc_page: int) -> list[str]:
    current = toc_page + 1
    while current < len(pages) and "........" in pages[current][0]:
        current += 1  # skip continuation pages of the table of contents
    numbers = []
    for level, num, title in entries:
        key = re.sub(r"\s+", "", title)
        for j in range(current, len(pages)):
            if key in pages[j][0]:
                numbers.append(pages[j][1])
                current = j
                break
        else:
            numbers.append("")
    return numbers


def write_toc(entries, numbers) -> None:
    z = zipfile.ZipFile(DOCX)
    files = {n: z.read(n) for n in z.namelist()}
    z.close()
    doc = etree.fromstring(files["word/document.xml"])
    sdt = next(s for s in doc.iter(W + "sdt")
               if any(style_of(p) == "Nadpisobsahu" for p in s.iter(W + "p")))
    content = sdt.find("w:sdtContent", NS)
    for p in list(content):
        if style_of(p) != "Nadpisobsahu":
            content.remove(p)

    def run(text=None, fld=None, instr=None, tab=False):
        r = el("w:r")
        if fld:
            r.append(el("w:fldChar", {"w:fldCharType": fld}))
        elif instr:
            t = el("w:instrText")
            t.text = instr
            t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
            r.append(t)
        elif tab:
            r.append(el("w:tab"))
        else:
            t = el("w:t")
            t.text = text
            t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
            r.append(t)
        return r

    for i, ((level, num, title), page) in enumerate(zip(entries, numbers)):
        p = el("w:p", children=[el("w:pPr", children=[
            el("w:pStyle", {"w:val": f"Obsah{level}"}),
            el("w:tabs", children=[el("w:tab", {"w:val": "right", "w:leader": "dot",
                                                "w:pos": "8778"})])])])
        if i == 0:
            p.append(run(fld="begin"))
            p.append(run(instr=' TOC \\o "1-3" \\h \\z \\u '))
            p.append(run(fld="separate"))
        p.append(run(f"{num} {title}".strip()))
        p.append(run(tab=True))
        p.append(run(page))
        if i == len(entries) - 1:
            p.append(run(fld="end"))
        content.append(p)
    normalise(doc.find("w:body", NS))
    files["word/document.xml"] = etree.tostring(doc, xml_declaration=True, encoding="UTF-8",
                                                standalone=True)
    with zipfile.ZipFile(DOCX, "w", zipfile.ZIP_DEFLATED) as out:
        for n in ["[Content_Types].xml"] + [n for n in files if n != "[Content_Types].xml"]:
            out.writestr(n, files[n])


def render(profile: Path, outdir: Path) -> Path:
    subprocess.run([SOFFICE, "--headless", f"-env:UserInstallation=file://{profile}",
                    "--convert-to", "pdf", "--outdir", str(outdir), str(DOCX)],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return outdir / "report.pdf"


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="report-pdf-"))
    profile = tmp / "profile"
    fonts = profile / "user" / "fonts"
    fonts.mkdir(parents=True)
    for d in FONT_DIRS:
        if d.is_dir():
            for f in d.iterdir():
                if f.suffix.lower() in (".ttf", ".otf") and f.name.startswith(FONT_PATTERNS):
                    shutil.copy(f, fonts / f.name)

    doc = etree.fromstring(zipfile.ZipFile(DOCX).read("word/document.xml"))
    entries = headings(doc)
    previous = None
    for attempt in range(4):
        pdf_path = render(profile, tmp)
        pdf = pdfium.PdfDocument(str(pdf_path))
        pages = page_labels(pdf)
        toc_page = next(i for i, (t, _) in enumerate(pages) if t.startswith("Contents"))
        numbers = locate(entries, pages, toc_page)
        pdf.close()
        missing = [e[2] for e, n in zip(entries, numbers) if not n]
        if missing:
            print(f"warning: page not found for {missing}", file=sys.stderr)
        if numbers == previous:
            break
        write_toc(entries, numbers)
        previous = numbers
    shutil.copy(pdf_path, PDF)
    print(f"wrote {PDF.relative_to(ROOT)} ({len(pages)} pages, TOC after {attempt + 1} passes)")
    shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
