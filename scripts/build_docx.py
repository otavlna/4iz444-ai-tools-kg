#!/usr/bin/env python3
"""Convert the assembled report (build/report.md) into the FIS Word template.

1. pandoc converts build/report.md into a temporary DOCX (build/body.docx) that already uses
   the style names of the template (heading 1-3, hyperlinks, ...).
2. The body of that DOCX is post-processed (template styles for text, lists, tables, code
   listings, captions) and spliced into report/template/fis-template.docx:
     - title page, AI declaration, abstracts and table of contents are filled from
       report/frontmatter.md,
     - the guidance text of the template and its sample chapters are removed,
     - the main text goes into the section with arabic page numbers, the appendices into the
       last section (roman page numbers), so the section breaks of the template are kept.
3. The result is written to report/report.docx.

Usage: python scripts/build_docx.py
"""
from __future__ import annotations

import copy
import re
import subprocess
import sys
import zipfile
from pathlib import Path

from lxml import etree

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "report" / "template" / "fis-template.docx"
FRONT = ROOT / "report" / "frontmatter.md"
SOURCE = ROOT / "build" / "report.md"
BODY = ROOT / "build" / "body.docx"
OUT = ROOT / "report" / "report.docx"

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PR_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
CT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
NS = {"w": W_NS, "r": R_NS}
W = f"{{{W_NS}}}"
R = f"{{{R_NS}}}"

UNNUMBERED = {"Introduction", "Conclusion", "References", "Appendices"}
BULLET_NUM_ID = "8"          # bullet list definition of the template (main text)
CODE_SIZE = "17"             # 8.5 pt for code listings
CODE_FONT = "Courier New"    # available on Windows, macOS and in LibreOffice
TABLE_TEXT_SIZE = "17"       # 8.5 pt in tables
TEXT_WIDTH = 8786            # A4 minus margins and gutter of the template (twips)


# order of child elements required by the WordprocessingML schema
PPR_ORDER = ["pStyle", "keepNext", "keepLines", "pageBreakBefore", "framePr", "widowControl",
             "numPr", "suppressLineNumbers", "pBdr", "shd", "tabs", "suppressAutoHyphens",
             "kinsoku", "wordWrap", "overflowPunct", "topLinePunct", "autoSpaceDE", "autoSpaceDN",
             "bidi", "adjustRightInd", "snapToGrid", "spacing", "ind", "contextualSpacing",
             "mirrorIndents", "suppressOverlap", "jc", "textDirection", "textAlignment",
             "textboxTightWrap", "outlineLvl", "divId", "cnfStyle", "rPr", "sectPr", "pPrChange"]
RPR_ORDER = ["rStyle", "rFonts", "b", "bCs", "i", "iCs", "caps", "smallCaps", "strike", "dstrike",
             "outline", "shadow", "emboss", "imprint", "noProof", "snapToGrid", "vanish",
             "webHidden", "color", "spacing", "w", "kern", "position", "sz", "szCs", "highlight",
             "u", "effect", "bdr", "shd", "fitText", "vertAlign", "rtl", "cs", "em", "lang",
             "eastAsianLayout", "specVanish", "oMath"]
TBLPR_ORDER = ["tblStyle", "tblpPr", "tblOverlap", "bidiVisual", "tblStyleRowBandSize",
               "tblStyleColBandSize", "tblW", "jc", "tblCellSpacing", "tblInd", "tblBorders", "shd",
               "tblLayout", "tblCellMar", "tblLook", "tblCaption", "tblDescription"]
TRPR_ORDER = ["cnfStyle", "divId", "gridBefore", "gridAfter", "wBefore", "wAfter", "cantSplit",
              "trHeight", "tblHeader", "tblCellSpacing", "jc", "hidden"]
TCPR_ORDER = ["cnfStyle", "tcW", "gridSpan", "hMerge", "vMerge", "tcBorders", "shd", "noWrap",
              "tcMar", "textDirection", "tcFitText", "vAlign", "hideMark"]


def order_children(node, order: list[str]) -> None:
    rank = {name: i for i, name in enumerate(order)}
    kids = list(node)
    seen = {}
    for k in kids:  # drop duplicates, keep the last occurrence (latest setting wins)
        seen[etree.QName(k).localname] = k
    kids = [k for k in kids if seen.get(etree.QName(k).localname) is k]
    kids.sort(key=lambda k: rank.get(etree.QName(k).localname, len(order)))
    for k in list(node):
        node.remove(k)
    for k in kids:
        node.append(k)


def normalise(root) -> None:
    for tag, order in (("pPr", PPR_ORDER), ("rPr", RPR_ORDER), ("tblPr", TBLPR_ORDER),
                       ("trPr", TRPR_ORDER), ("tcPr", TCPR_ORDER)):
        for node in root.iter(W + tag):
            order_children(node, order)


# --------------------------------------------------------------------------- helpers
def el(tag: str, attrib: dict | None = None, children: list | None = None):
    prefix, name = tag.split(":")
    e = etree.Element(f"{{{NS[prefix]}}}{name}")
    for k, v in (attrib or {}).items():
        p, n = k.split(":")
        e.set(f"{{{NS[p]}}}{n}", v)
    for c in children or []:
        e.append(c)
    return e


def text_of(p) -> str:
    return "".join(p.itertext()).strip()


def style_of(p) -> str | None:
    s = p.find("w:pPr/w:pStyle", NS)
    return s.get(W + "val") if s is not None else None


def set_style(p, style: str | None) -> None:
    ppr = p.find("w:pPr", NS)
    if ppr is None:
        ppr = el("w:pPr")
        p.insert(0, ppr)
    s = ppr.find("w:pStyle", NS)
    if style is None:
        if s is not None:
            ppr.remove(s)
        return
    if s is None:
        s = el("w:pStyle")
        ppr.insert(0, s)
    s.set(W + "val", style)


def runs_from_markup(text: str, base_rpr=None) -> list:
    """Create runs from text with **bold** and *italic* markup."""
    runs = []
    for part in re.split(r"(\*\*[^*]+\*\*|\*[^*]+\*)", text):
        if not part:
            continue
        rpr = copy.deepcopy(base_rpr) if base_rpr is not None else el("w:rPr")
        if part.startswith("**"):
            rpr.append(el("w:b"))
            part = part[2:-2]
        elif part.startswith("*"):
            rpr.append(el("w:i"))
            part = part[1:-1]
        t = el("w:t")
        t.text = part
        t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
        r = el("w:r", children=[rpr, t]) if len(rpr) else el("w:r", children=[t])
        runs.append(r)
    return runs


def replace_text(p, text: str) -> None:
    """Replace the content of paragraph p, keeping pPr and the rPr of its first run."""
    first = p.find(".//w:r/w:rPr", NS)
    base = copy.deepcopy(first) if first is not None else None
    if base is not None:
        for tag in ("w:b", "w:bCs", "w:i", "w:iCs"):
            for x in base.findall(tag, NS):
                base.remove(x)
    for child in list(p):
        if child.tag != W + "pPr":
            p.remove(child)
    for r in runs_from_markup(text, base):
        p.append(r)


def new_para_like(src, text: str):
    p = el("w:p")
    ppr = src.find("w:pPr", NS)
    if ppr is not None:
        p.append(copy.deepcopy(ppr))
    first = src.find(".//w:r/w:rPr", NS)
    base = copy.deepcopy(first) if first is not None else None
    if base is not None:
        for tag in ("w:b", "w:bCs", "w:i", "w:iCs"):
            for x in base.findall(tag, NS):
                base.remove(x)
    for r in runs_from_markup(text, base):
        p.append(r)
    return p


def parse_frontmatter() -> dict[str, str]:
    text = re.sub(r"<!--.*?-->", "", FRONT.read_text(), flags=re.S)
    parts = re.split(r"^## (\S+)\s*$", text, flags=re.M)
    return {parts[i]: parts[i + 1].strip() for i in range(1, len(parts), 2)}


def paragraphs_of(block: str) -> list[str]:
    return [" ".join(x.split()) for x in re.split(r"\n\s*\n", block) if x.strip()]


def bullets_of(block: str) -> list[str]:
    return [l[2:].strip() for l in block.splitlines() if l.startswith("- ")]


# --------------------------------------------------------------------------- pandoc
def run_pandoc() -> None:
    subprocess.run([
        "pandoc", str(SOURCE), "-o", str(BODY), "--from", "markdown-implicit_figures",
        f"--reference-doc={TEMPLATE}", "--resource-path", str(ROOT / "report"),
        "--syntax-highlighting=none",
    ], check=True)


# --------------------------------------------------------------------------- body transformation
def make_caption(num: str, title: str) -> list:
    out = []
    for text, fmt in ((num, "w:b"), (title, "w:i")):
        p = el("w:p", children=[el("w:pPr", children=[
            el("w:pStyle", {"w:val": "Titulek"}), el("w:keepNext"),
            el("w:spacing", {"w:before": "120" if fmt == "w:b" else "0",
                             "w:after": "0" if fmt == "w:b" else "120"}),
            el("w:jc", {"w:val": "left"})])])
        rpr = el("w:rPr", children=[el(fmt)])
        t = el("w:t")
        t.text = text
        p.append(el("w:r", children=[rpr, t]))
        out.append(p)
    return out


def make_note(text: str):
    p = el("w:p", children=[el("w:pPr", children=[
        el("w:spacing", {"w:before": "60", "w:after": "240"}),
        el("w:jc", {"w:val": "left"})])])
    m = re.match(r"(Note:)\s*(.*)", text, re.S)
    head, rest = (m.group(1), m.group(2)) if m else ("", text)
    for s, italic in ((head, True), ((" " if head else "") + rest, False)):
        if not s:
            continue
        rpr = el("w:rPr", children=([el("w:i")] if italic else []) + [el("w:sz", {"w:val": "18"})])
        t = el("w:t")
        t.text = s
        t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
        p.append(el("w:r", children=[rpr, t]))
    return p


def style_table(tbl) -> None:
    tblpr = tbl.find("w:tblPr", NS)
    for child in list(tblpr):
        if child.tag in (W + "tblStyle", W + "tblBorders", W + "tblLook", W + "tblCellMar"):
            tblpr.remove(child)
    tblpr.insert(0, el("w:tblStyle", {"w:val": "Normlntabulka"}))
    borders = el("w:tblBorders", children=[
        el("w:top", {"w:val": "single", "w:sz": "12", "w:space": "0", "w:color": "000000"}),
        el("w:bottom", {"w:val": "single", "w:sz": "12", "w:space": "0", "w:color": "000000"}),
        el("w:insideH", {"w:val": "single", "w:sz": "4", "w:space": "0", "w:color": "BFBFBF"}),
    ])
    tblpr.append(borders)
    tblpr.append(el("w:tblCellMar", children=[
        el("w:left", {"w:w": "85", "w:type": "dxa"}), el("w:right", {"w:w": "85", "w:type": "dxa"})]))
    rows = tbl.findall("w:tr", NS)
    # column widths proportional to the length of the content (pandoc gives equal widths)
    ncols = max(len(tr.findall("w:tc", NS)) for tr in rows)
    longest = [1] * ncols   # longest unbreakable token -> minimal width
    total = [0.0] * ncols   # average text length -> share of the remaining width
    for ri, tr in enumerate(rows):
        for j, tc in enumerate(tr.findall("w:tc", NS)):
            text = text_of(tc)
            is_code = tc.find(".//w:rFonts", NS) is not None
            factor = 1.25 if is_code else 1.0   # monospace characters are wider
            if ri == 0:
                factor *= 1.3                   # bold header
            tokens = re.split(r"[\s/\-]+", text)
            longest[j] = max(longest[j], int(max((len(t) for t in tokens), default=1) * factor))
            total[j] += len(text) * factor
    char = 100                                  # twips per character at 8.5 pt (bold headers)
    minimum = [min(l * char + 200, TEXT_WIDTH * 0.45) for l in longest]
    if sum(minimum) > TEXT_WIDTH:
        minimum = [m * TEXT_WIDTH / sum(minimum) for m in minimum]
    rest = TEXT_WIDTH - sum(minimum)
    avg = [max(t / len(rows), 1) for t in total]
    widths = [int(minimum[j] + rest * avg[j] / sum(avg)) for j in range(ncols)]
    for child in list(tblpr):
        if child.tag in (W + "tblW", W + "tblLayout"):
            tblpr.remove(child)
    tblpr.append(el("w:tblW", {"w:w": str(TEXT_WIDTH), "w:type": "dxa"}))
    tblpr.append(el("w:tblLayout", {"w:type": "fixed"}))
    grid = tbl.find("w:tblGrid", NS)
    for g in list(grid):
        grid.remove(g)
    for wdt in widths:
        grid.append(el("w:gridCol", {"w:w": str(wdt)}))
    for tr in rows:
        for j, tc in enumerate(tr.findall("w:tc", NS)):
            tcpr = tc.find("w:tcPr", NS)
            if tcpr is None:
                tcpr = el("w:tcPr")
                tc.insert(0, tcpr)
            for x in tcpr.findall("w:tcW", NS):
                tcpr.remove(x)
            tcpr.insert(0, el("w:tcW", {"w:w": str(widths[j]), "w:type": "dxa"}))
    for i, tr in enumerate(rows):
        header = i == 0
        trpr = tr.find("w:trPr", NS)
        if trpr is None:
            trpr = el("w:trPr")
            tr.insert(0, trpr)
        if trpr.find("w:cantSplit", NS) is None:
            trpr.append(el("w:cantSplit"))
        if header and trpr.find("w:tblHeader", NS) is None:
            trpr.append(el("w:tblHeader"))
        for tc in tr.findall("w:tc", NS):
            if header:
                tcpr = tc.find("w:tcPr", NS)
                if tcpr is None:
                    tcpr = el("w:tcPr")
                    tc.insert(0, tcpr)
                tcpr.append(el("w:tcBorders", children=[
                    el("w:bottom", {"w:val": "single", "w:sz": "8", "w:space": "0", "w:color": "000000"})]))
            for p in tc.findall("w:p", NS):
                set_style(p, "Textvtabulce")
                for r in p.findall(".//w:r", NS):
                    rpr = r.find("w:rPr", NS)
                    if rpr is None:
                        rpr = el("w:rPr")
                        r.insert(0, rpr)
                    if header:
                        rpr.append(el("w:b"))
                    for sz in rpr.findall("w:sz", NS):
                        rpr.remove(sz)
                    rpr.append(el("w:sz", {"w:val": TABLE_TEXT_SIZE}))


def fix_runs(root, in_code: bool = False) -> None:
    """Replace pandoc character styles by direct formatting available in the template."""
    for r in root.iter(W + "r"):
        rpr = r.find("w:rPr", NS)
        if rpr is None:
            continue
        rs = rpr.find("w:rStyle", NS)
        if rs is None:
            continue
        val = rs.get(W + "val")
        if val == "VerbatimChar":
            rpr.remove(rs)
            if not in_code:
                rpr.insert(0, el("w:rFonts", {"w:ascii": CODE_FONT, "w:hAnsi": CODE_FONT,
                                              "w:cs": CODE_FONT}))
        elif val == "Hyperlink":
            rs.set(W + "val", "Hypertextovodkaz")


def transform_body(elements: list) -> list:
    out = []
    in_appendices = False
    for e in elements:
        if (out and out[-1].tag == W + "tbl" and e.tag == W + "p"
                and not text_of(e).startswith("[[")):
            ppr = e.find("w:pPr", NS)
            if ppr is None:
                ppr = el("w:pPr")
                e.insert(0, ppr)
            ppr.append(el("w:spacing", {"w:before": "240"}))
        if e.tag == W + "tbl":
            style_table(e)
            fix_runs(e)
            out.append(e)
            continue
        if e.tag != W + "p":
            out.append(e)
            continue
        txt = text_of(e)
        st = style_of(e)
        m = re.match(r"^\[\[CAPTION\|([^|]+)\|(.*)\]\]$", txt, re.S)
        if m:
            out.extend(make_caption(m.group(1), m.group(2)))
            continue
        m = re.match(r"^\[\[NOTE\|(.*)\]\]$", txt, re.S)
        if m:
            out.append(make_note(m.group(1)))
            continue
        if st == "Nadpis1":
            if txt in UNNUMBERED:
                set_style(e, "Nadpis1neslovan")
            in_appendices = txt == "Appendices"
        elif st == "Nadpis2" and in_appendices:
            set_style(e, "Nadpis2plohy")
        elif st == "SourceCode":
            set_style(e, "Textprogramovhokdu")
            fix_runs(e, in_code=True)
            ppr = e.find("w:pPr", NS)
            ppr.append(el("w:spacing", {"w:before": "60", "w:after": "200", "w:line": "240",
                                        "w:lineRule": "auto"}))
            for r in e.findall(".//w:r", NS):
                rpr = r.find("w:rPr", NS)
                if rpr is None:
                    rpr = el("w:rPr")
                    r.insert(0, rpr)
                rpr.append(el("w:rFonts", {"w:ascii": CODE_FONT, "w:hAnsi": CODE_FONT,
                                           "w:cs": CODE_FONT}))
                rpr.append(el("w:w", {"w:val": "100"}))
                rpr.append(el("w:sz", {"w:val": CODE_SIZE}))
            out.append(e)
            continue
        elif e.find("w:pPr/w:numPr", NS) is not None:
            set_style(e, "Odstavecseseznamem")
            e.find("w:pPr/w:numPr/w:numId", NS).set(W + "val", BULLET_NUM_ID)
        elif e.find(".//w:drawing", NS) is not None:
            set_style(e, None)
            ppr = e.find("w:pPr", NS)
            ppr.append(el("w:keepNext"))
            ppr.append(el("w:jc", {"w:val": "center"}))
        elif st in ("BodyText", "FirstParagraph", "Compact", None):
            set_style(e, None)
        fix_runs(e)
        out.append(e)
    return out


# --------------------------------------------------------------------------- relationships
def merge_relationships(body_zip, body_rels, tpl_rels, files: dict, elements: list) -> None:
    """Copy relationships (images, hyperlinks) used by the body into the template."""
    rel_by_id = {r.get("Id"): r for r in body_rels}
    existing = {r.get("Id") for r in tpl_rels}
    n = 1000
    mapping = {}
    for e in elements:
        for node in e.iter():
            for attr in (R + "id", R + "embed", R + "link"):
                rid = node.get(attr)
                if rid is None or rid not in rel_by_id:
                    continue
                if rid not in mapping:
                    n += 1
                    while f"rId{n}" in existing:
                        n += 1
                    new_id = f"rId{n}"
                    rel = copy.deepcopy(rel_by_id[rid])
                    rel.set("Id", new_id)
                    if rel.get("Type").endswith("/image"):
                        target = rel.get("Target")
                        new_target = f"media/report_{n}{Path(target).suffix}"
                        files[f"word/{new_target}"] = body_zip.read(f"word/{target}")
                        rel.set("Target", new_target)
                    tpl_rels.append(rel)
                    existing.add(new_id)
                    mapping[rid] = new_id
                node.set(attr, mapping[rid])


# --------------------------------------------------------------------------- front matter
def fill_front_matter(body, fm: dict) -> None:
    def find(style: str, contains: str | None = None):
        for p in body.iter(W + "p"):
            if style_of(p) == style and (contains is None or contains in text_of(p)):
                return p
        raise KeyError(f"{style} {contains}")

    replace_text(find("Vysokkola"), fm["university"])
    replace_text(find("Fakulta"), fm["faculty"])
    replace_text(find("NzevBP"), fm["title"])
    replace_text(find("TypprceBP"), fm["type"])
    replace_text(find("Studijnprogram", "Studijní program"), fm["course"])
    replace_text(find("Studijnprogram", "Specializace"), "")
    replace_text(find("Autor"), fm["authors"])
    replace_text(find("VedoucBP", "Vedoucí"), "")
    replace_text(find("VedoucBP", "Konzultant"), "")
    replace_text(find("Kdeakdyodevzdno"), fm["place-date"])

    # --- AI declaration
    head = find("Nadpisnzvyjin", "Prohlášení")
    replace_text(head, fm["ai-heading"])
    paras = []
    p = head.getnext()
    while p is not None and not (p.tag == W + "p" and "Poděkování" in text_of(p)):
        paras.append(p)
        p = p.getnext()
    ack_heading = p
    item_src = next(x for x in paras if style_of(x) == "Odstavecseseznamem")
    plain_src = next(x for x in paras if text_of(x).startswith("2)"))
    note_src = next(x for x in paras if text_of(x).startswith("Každé použití"))
    confirm_src = next(x for x in paras if text_of(x).startswith("Potvrzuji, že:"))
    confirm_item_src = next(x for x in paras if text_of(x).startswith("má práce"))
    new = [new_para_like(plain_src, fm["ai-intro"])]
    new += [new_para_like(item_src, b) for b in bullets_of(fm["ai-uses"])]
    new += [new_para_like(note_src, fm["ai-note"]), new_para_like(confirm_src, fm["ai-confirm"])]
    new += [new_para_like(confirm_item_src, b) for b in bullets_of(fm["ai-confirm-items"])]
    for x in paras:
        body.remove(x)
    anchor = head
    for x in new:
        anchor.addnext(x)
        anchor = x
    # numbered "1)" style of the declaration is replaced by plain paragraphs
    for x in new:
        if text_of(x).startswith("We confirm that artificial"):
            np_ = x.find("w:pPr/w:numPr", NS)
            if np_ is not None:
                np_.getparent().remove(np_)

    # --- acknowledgement is not part of a semestral project: drop heading and text
    nxt = ack_heading.getnext()
    body.remove(ack_heading)
    while nxt is not None and nxt.find(".//w:sectPr", NS) is None:
        after = nxt.getnext()
        body.remove(nxt)
        nxt = after

    # --- abstracts
    def fill_abstract(heading_text: str, key: str, kw_heading: str, kw_key: str, new_heading: str,
                      new_kw_heading: str):
        h = find("Nadpisnzvyjin", heading_text)
        replace_text(h, new_heading)
        texts = []
        p = h.getnext()
        while style_of(p) != "Klovslova":
            texts.append(p)
            p = p.getnext()
        kw_h = p
        replace_text(kw_h, new_kw_heading)
        src = texts[0]
        anchor = h
        for t in paragraphs_of(fm[key]):
            x = new_para_like(src, t)
            anchor.addnext(x)
            anchor = x
        for t in texts:
            body.remove(t)
        replace_text(kw_h.getnext(), fm[kw_key])

    fill_abstract("Abstrakt", "abstract-cs", "Klíčová slova", "keywords-cs",
                  fm["abstract-cs-heading"], fm["keywords-cs-heading"])
    fill_abstract("Abstract", "abstract-en", "Keywords", "keywords-en",
                  fm["abstract-en-heading"], fm["keywords-en-heading"])

    # --- table of contents: new TOC field, updated by Word / LibreOffice
    toc_head = find("Nadpisobsahu")
    replace_text(toc_head, fm["toc-heading"])
    sdt_content = toc_head.getparent()
    for p in list(sdt_content):
        if p is not toc_head:
            sdt_content.remove(p)

    def fld(kind):
        return el("w:r", children=[el("w:fldChar", {"w:fldCharType": kind})])

    instr = el("w:instrText")
    instr.text = ' TOC \\o "1-3" \\h \\z \\u '
    instr.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    placeholder = el("w:t")
    placeholder.text = "Update the table of contents (F9)."
    toc_p = el("w:p", children=[el("w:pPr", children=[el("w:pStyle", {"w:val": "Obsah1"})]),
                                fld("begin"), el("w:r", children=[instr]), fld("separate"),
                                el("w:r", children=[placeholder]), fld("end")])
    sdt_content.append(toc_p)


# --------------------------------------------------------------------------- main
def main() -> int:
    run_pandoc()
    tz = zipfile.ZipFile(TEMPLATE)
    bz = zipfile.ZipFile(BODY)
    files = {n: tz.read(n) for n in tz.namelist()
             if not n.endswith("/") and not n.startswith("[trash]")}

    doc = etree.fromstring(files["word/document.xml"])
    body = doc.find("w:body", NS)
    bdoc = etree.fromstring(bz.read("word/document.xml"))
    bbody = bdoc.find("w:body", NS)
    body_elements = [e for e in bbody if e.tag != W + "sectPr"]

    # relationships
    tpl_rels = etree.fromstring(files["word/_rels/document.xml.rels"])
    body_rels = etree.fromstring(bz.read("word/_rels/document.xml.rels"))
    merge_relationships(bz, body_rels, tpl_rels, files, body_elements)
    files["word/_rels/document.xml.rels"] = etree.tostring(
        tpl_rels, xml_declaration=True, encoding="UTF-8", standalone=True)

    content = transform_body(body_elements)
    split = next(i for i, e in enumerate(content)
                 if e.tag == W + "p" and style_of(e) == "Nadpis1neslovan" and text_of(e) == "Appendices")
    main_part, appendix_part = content[:split], content[split:]

    fill_front_matter(body, parse_frontmatter())

    children = list(body)

    def index_of(pred, start=0):
        return next(i for i in range(start, len(children)) if pred(children[i]))

    def is_sect_para(e):
        return e.tag == W + "p" and e.find("w:pPr/w:sectPr", NS) is not None

    toc_sdt = index_of(lambda e: e.tag == W + "sdt" and any(
        style_of(p) == "Nadpisobsahu" for p in e.iter(W + "p")))
    toc_end = index_of(is_sect_para, toc_sdt)
    intro = index_of(lambda e: e.tag == W + "p" and style_of(e) == "Nadpis1neslovan"
                     and text_of(e) == "Úvod", toc_end)
    refs_end = index_of(is_sect_para, intro)
    appx = index_of(lambda e: e.tag == W + "p" and text_of(e) == "Přílohy", refs_end)
    final_sect = len(children) - 1  # body-level sectPr

    # remove template guidance (between TOC section and "Úvod") and sample chapters
    for e in children[toc_end + 1:intro] + children[intro:refs_end] + children[appx:final_sect]:
        body.remove(e)
    sect_para = children[refs_end]
    for e in main_part:
        sect_para.addprevious(e)
    final = children[final_sect]
    for e in appendix_part:
        final.addprevious(e)

    normalise(body)
    files["word/document.xml"] = etree.tostring(doc, xml_declaration=True, encoding="UTF-8",
                                                standalone=True)

    # appendix numbering "Příloha A:" -> "Appendix A:"
    files["word/numbering.xml"] = files["word/numbering.xml"].replace(
        "Příloha %1:".encode(), b"Appendix %1:")
    # document language: English
    styles = files["word/styles.xml"].decode()
    styles = styles.replace('<w:lang w:val="cs-CZ" w:eastAsia="en-US"', '<w:lang w:val="en-GB" w:eastAsia="en-US"')
    files["word/styles.xml"] = styles.encode()
    # ask Word to update fields (table of contents) when the document is opened
    settings = files["word/settings.xml"].decode()
    if "w:updateFields" not in settings:
        # CT_Settings is an ordered sequence: updateFields precedes hdrShapeDefaults,
        # footnotePr, endnotePr and compat
        m = re.search(r"<w:(hdrShapeDefaults|footnotePr|endnotePr|compat)[ >/]", settings)
        settings = settings[:m.start()] + '<w:updateFields w:val="true"/>' + settings[m.start():]
    files["word/settings.xml"] = settings.encode()
    # content type for PNG images
    ct = files["[Content_Types].xml"].decode()
    if 'Extension="png"' not in ct:
        ct = ct.replace("<Default ", '<Default Extension="png" ContentType="image/png"/><Default ', 1)
    files["[Content_Types].xml"] = ct.encode()

    OUT.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
        order = ["[Content_Types].xml"] + [n for n in files if n != "[Content_Types].xml"]
        for n in order:
            z.writestr(n, files[n])
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
