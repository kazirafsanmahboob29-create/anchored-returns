"""Typeset the working paper from its maintained Markdown manuscript."""

import re
from pathlib import Path

from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "paper" / "output"


def add_text(paragraph, text):
    """Keep the reference URLs clickable in the editable version."""
    for part in re.split(r"(https?://\S+)", text):
        if not part.startswith(("https://", "http://")):
            paragraph.add_run(part)
            continue
        url = part.rstrip(".,;")
        rel = paragraph.part.relate_to(
            url,
            "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink",
            is_external=True,
        )
        link = OxmlElement("w:hyperlink")
        link.set(qn("r:id"), rel)
        run = OxmlElement("w:r")
        properties = OxmlElement("w:rPr")
        color = OxmlElement("w:color")
        color.set(qn("w:val"), "222222")
        properties.append(color)
        run.append(properties)
        value = OxmlElement("w:t")
        value.text = url
        run.append(value)
        link.append(run)
        paragraph._p.append(link)
        paragraph.add_run(part[len(url) :])


def table(document, lines, keep_note=False):
    rows = [[c.strip() for c in line.strip().strip("|").split("|")] for line in lines]
    rows.pop(1)
    count = len(rows[0])
    widths = {
        2: [4.8, 1.7],
        3: [2.7, 1.7, 2.1],
        4: [2.8, 1.1, 1.5, 1.1],
        5: [2.1, 1.1, 1.1, 1.1, 1.1],
    }[count]
    if rows[0][0] == "Sample":
        widths = [2.2, 3.5, 0.8]
    elif rows[0][0] == "Utility and order year":
        widths = [2.8, 1.2, 1.3, 1.2]
    elif rows[0][0] == "Model and sample":
        widths = [3.0, 0.7, 1.3, 1.5]
    grid = document.add_table(rows=0, cols=count)
    grid.alignment = WD_TABLE_ALIGNMENT.CENTER
    grid.autofit = False
    for column, width in zip(grid.columns, widths):
        column.width = Inches(width)
    for i, row in enumerate(rows):
        cells = grid.add_row().cells
        for j, value in enumerate(row):
            cell = cells[j]
            cell.width = Inches(widths[j])
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            p = cell.paragraphs[0]
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.line_spacing = 1.05
            p.paragraph_format.keep_with_next = i < len(rows) - 1 or keep_note
            prose_column = j == 0 or rows[0][j] == "What it is used for"
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT if prose_column else WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run(value.replace("<br>", "\n"))
            run.font.size = Pt(9.5 if count == 5 else 10)
            run.bold = i == 0
            props = cell._tc.get_or_add_tcPr()
            borders = OxmlElement("w:tcBorders")
            for edge in ("top", "left", "bottom", "right"):
                border = OxmlElement("w:" + edge)
                for key, val in (("val", "single"), ("sz", "4"), ("color", "D9D9D9")):
                    border.set(qn("w:" + key), val)
                borders.append(border)
            props.append(borders)
            margins = OxmlElement("w:tcMar")
            for edge in ("top", "left", "bottom", "right"):
                margin = OxmlElement("w:" + edge)
                margin.set(qn("w:w"), "85")
                margin.set(qn("w:type"), "dxa")
                margins.append(margin)
            props.append(margins)
            if i == 0:
                shading = OxmlElement("w:shd")
                shading.set(qn("w:fill"), "F2F2F2")
                props.append(shading)
        no_split = OxmlElement("w:cantSplit")
        grid.rows[-1]._tr.get_or_add_trPr().append(no_split)
        if i == 0:
            repeat = OxmlElement("w:tblHeader")
            grid.rows[-1]._tr.get_or_add_trPr().append(repeat)


def build():
    manuscript = ROOT / "paper/manuscript.md"
    text = manuscript.read_text()
    if "\u2014" in text:
        raise ValueError("An em dash remains in the manuscript")
    document = Document()
    section = document.sections[0]
    section.page_width, section.page_height = Inches(8.5), Inches(11)
    section.top_margin = section.bottom_margin = Inches(0.85)
    section.left_margin = section.right_margin = Inches(1)
    normal = document.styles["Normal"]
    normal.font.name = "Times New Roman"
    normal.font.size = Pt(11)
    normal.font.color.rgb = RGBColor(0, 0, 0)
    normal.paragraph_format.line_spacing = 1.12
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.widow_control = True
    for name, size in (("Title", 17), ("Heading 1", 12), ("Heading 2", 11)):
        style = document.styles[name]
        style.font.name = "Times New Roman"
        style.font.size = Pt(size)
        style.font.color.rgb = RGBColor(0, 0, 0)
        style.font.bold = True
        style.paragraph_format.space_before = Pt(12 if name == "Heading 1" else 0)
        style.paragraph_format.space_after = Pt(6)
        style.paragraph_format.keep_with_next = True
    # The bundled Word template carries theme fonts and a title rule. Remove both.
    for name in ("Normal", "Title", "Heading 1", "Heading 2"):
        element = document.styles[name].element
        for border in element.findall(".//" + qn("w:pBdr")):
            border.getparent().remove(border)
        fonts = element.get_or_add_rPr().get_or_add_rFonts()
        for key in list(fonts.attrib):
            if "theme" in key.lower():
                del fonts.attrib[key]
        for key in ("ascii", "hAnsi", "eastAsia", "cs"):
            fonts.set(qn("w:" + key), "Times New Roman")
    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    field = OxmlElement("w:fldSimple")
    field.set(qn("w:instr"), "PAGE")
    footer._p.append(field)
    document.core_properties.author = "Kazi Rafsan Mahboob"
    document.core_properties.title = text.splitlines()[0].removeprefix("# ")
    document.core_properties.subject = "Independent research on regulated electric utility returns"
    lines, index, references = text.splitlines(), 0, False
    after_table = False
    while index < len(lines):
        line = lines[index].strip()
        if not line:
            index += 1
            continue
        if line.startswith("# "):
            title = line[2:].replace(" for US Electric Utilities", "\nfor US Electric Utilities")
            p = document.add_paragraph(title, "Title")
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        elif line.startswith("### "):
            document.add_paragraph(line[4:], "Heading 2")
        elif line.startswith("## "):
            heading = line[3:]
            references = heading in ("References", "Research materials and assistance")
            p = document.add_paragraph(heading, "Heading 1")
            if heading == "References" or heading.startswith("Appendix "):
                p.paragraph_format.page_break_before = True
        elif line.startswith("|"):
            end = index
            while end < len(lines) and lines[end].strip().startswith("|"):
                end += 1
            following = next((s.strip() for s in lines[end:] if s.strip()), "")
            table(document, lines[index:end], keep_note=following.startswith("Note:"))
            index = end
            after_table = True
            continue
        elif line.startswith("!["):
            match = re.match(r"!\[(.*?)\]\((.*?)\)", line)
            p = document.add_paragraph()
            p.paragraph_format.keep_with_next = True
            picture = p.add_run().add_picture(
                str((manuscript.parent / match[2]).resolve()), width=Inches(6.5)
            )
            picture._inline.docPr.set("descr", match[1])
        else:
            p = document.add_paragraph()
            if after_table:
                p.paragraph_format.space_before = Pt(6)
                after_table = False
            add_text(p, line)
            if re.match(r"(?:Table|Figure) [A-Z]?\d+ [A-Z]", line):
                p.paragraph_format.keep_with_next = True
                for run in p.runs:
                    run.bold = True
                    run.font.size = Pt(10.5)
            elif line.startswith("Note:") or references:
                for run in p.runs:
                    run.font.size = Pt(10)
                p.paragraph_format.line_spacing = 1.05
                p.paragraph_format.space_before = Pt(5)
                if line.startswith("Note:"):
                    p.paragraph_format.keep_together = True
            elif index < 8:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p.paragraph_format.space_after = Pt(3)
                if index == 2:
                    for run in p.runs:
                        run.italic = True
        index += 1
    OUT.mkdir(exist_ok=True)
    path = OUT / "Mahboob_Utility_Returns_Working_Paper.docx"
    document.save(path)
    print(path)


if __name__ == "__main__":
    build()
