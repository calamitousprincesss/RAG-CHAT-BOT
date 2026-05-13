"""Convert the docs markdown files to professional PDFs using reportlab."""
from __future__ import annotations
import re
import sys
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor, white
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Preformatted, Table, TableStyle,
    PageBreak, KeepTogether, Image
)
from reportlab.lib import colors


PRIMARY = HexColor("#1A73E8")
SURFACE_2 = HexColor("#F1F3F4")
BORDER = HexColor("#DADCE0")
MUTED = HexColor("#5F6368")
TEXT = HexColor("#202124")


def make_styles():
    styles = getSampleStyleSheet()
    base = "Helvetica"
    mono = "Courier"

    return {
        "title": ParagraphStyle(
            "title", parent=styles["Title"], fontName=f"{base}-Bold",
            fontSize=22, textColor=PRIMARY, spaceAfter=14, leading=26,
        ),
        "h1": ParagraphStyle(
            "h1", parent=styles["Heading1"], fontName=f"{base}-Bold",
            fontSize=18, textColor=TEXT, spaceBefore=18, spaceAfter=10, leading=22,
        ),
        "h2": ParagraphStyle(
            "h2", parent=styles["Heading2"], fontName=f"{base}-Bold",
            fontSize=14, textColor=TEXT, spaceBefore=14, spaceAfter=8, leading=18,
        ),
        "h3": ParagraphStyle(
            "h3", parent=styles["Heading3"], fontName=f"{base}-Bold",
            fontSize=12, textColor=TEXT, spaceBefore=10, spaceAfter=6, leading=15,
        ),
        "h4": ParagraphStyle(
            "h4", parent=styles["Heading4"], fontName=f"{base}-Bold",
            fontSize=11, textColor=TEXT, spaceBefore=8, spaceAfter=4, leading=14,
        ),
        "body": ParagraphStyle(
            "body", parent=styles["BodyText"], fontName=base,
            fontSize=10, textColor=TEXT, spaceAfter=6, leading=14, alignment=TA_LEFT,
        ),
        "muted": ParagraphStyle(
            "muted", parent=styles["BodyText"], fontName=base,
            fontSize=9, textColor=MUTED, leading=12,
        ),
        "code": ParagraphStyle(
            "code", parent=styles["Code"], fontName=mono,
            fontSize=8.5, textColor=TEXT, backColor=SURFACE_2,
            leftIndent=8, rightIndent=8, spaceBefore=4, spaceAfter=8, leading=11,
            borderWidth=0.5, borderColor=BORDER, borderPadding=6,
        ),
        "li": ParagraphStyle(
            "li", parent=styles["BodyText"], fontName=base,
            fontSize=10, leftIndent=16, bulletIndent=4, spaceAfter=3, leading=13,
        ),
    }


INLINE_CODE_RE = re.compile(r"`([^`]+)`")
BOLD_RE = re.compile(r"\*\*([^*]+)\*\*")
EM_RE = re.compile(r"(?<!\*)\*([^*\n]+)\*(?!\*)")
LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
IMG_RE = re.compile(r"^!\[([^\]]*)\]\(([^)]+)\)\s*$")


UNICODE_FALLBACK = {
    "—": "&mdash;", "–": "&ndash;",
    "‘": "'", "’": "'", "“": '"', "”": '"',
    "…": "...", "·": "·",
}


def safe_text(text: str) -> str:
    for k, v in UNICODE_FALLBACK.items():
        text = text.replace(k, v)
    return text


def inline_md(text: str) -> str:
    text = safe_text(text)
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = text.replace("&amp;mdash;", "&mdash;").replace("&amp;ndash;", "&ndash;")
    text = BOLD_RE.sub(r"<b>\1</b>", text)
    text = EM_RE.sub(r"<i>\1</i>", text)
    text = INLINE_CODE_RE.sub(
        r'<font face="Courier" backColor="#F1F3F4">&nbsp;\1&nbsp;</font>', text
    )
    text = LINK_RE.sub(r'<link href="\2" color="#1A73E8">\1</link>', text)
    return text


def split_table_row(line: str) -> list[str]:
    parts = line.strip().strip("|").split("|")
    return [p.strip() for p in parts]


def build_table_flowable(header: list[str], rows: list[list[str]], styles) -> Table:
    cell_style = ParagraphStyle(
        "cell", parent=styles["body"], fontSize=8.5, leading=11, spaceAfter=0
    )
    head_style = ParagraphStyle(
        "head", parent=cell_style, fontName="Helvetica-Bold", textColor=white
    )

    def wrap(cells, st):
        return [Paragraph(inline_md(c), st) for c in cells]

    data = [wrap(header, head_style)] + [wrap(r, cell_style) for r in rows]
    n_cols = max(len(r) for r in data)
    data = [r + [Paragraph("", cell_style)] * (n_cols - len(r)) for r in data]

    page_width = A4[0] - 4 * cm
    col_width = page_width / n_cols
    tbl = Table(data, colWidths=[col_width] * n_cols, repeatRows=1, hAlign="LEFT")
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
        ("TEXTCOLOR", (0, 0), (-1, 0), white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.4, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, SURFACE_2]),
    ]))
    return tbl


def render_markdown(md: str, styles, *, json_truncate_lines: int = 0,
                    base_dir: Path | None = None) -> list:
    flow = []
    lines = md.splitlines()
    i = 0
    in_code = False
    code_buf: list[str] = []
    table_buf: list[str] = []

    def flush_table():
        nonlocal table_buf
        if len(table_buf) >= 2:
            header = split_table_row(table_buf[0])
            rows = [split_table_row(r) for r in table_buf[2:]]
            flow.append(build_table_flowable(header, rows, styles))
            flow.append(Spacer(1, 6))
        table_buf = []

    json_emitted_lines = 0
    in_json_truncate = False

    while i < len(lines):
        line = lines[i]

        if line.strip().startswith("```"):
            if in_code:
                code_text = safe_text("\n".join(code_buf)) or " "
                code_text = code_text.replace("&mdash;", "—").replace("&ndash;", "–")
                flow.append(Preformatted(code_text.replace("—", "-").replace("–", "-"), styles["code"]))
                code_buf = []
                in_code = False
                in_json_truncate = False
                json_emitted_lines = 0
            else:
                in_code = True
                lang = line.strip().lstrip("`").strip()
                if json_truncate_lines and lang.lower() == "json":
                    in_json_truncate = True
            i += 1
            continue

        if in_code:
            if in_json_truncate and json_emitted_lines >= json_truncate_lines:
                if json_emitted_lines == json_truncate_lines:
                    code_buf.append(f"... [truncated — see retrieval_benchmark.json for full JSON]")
                    json_emitted_lines += 1
            else:
                code_buf.append(line)
                json_emitted_lines += 1
            i += 1
            continue

        if line.strip().startswith("|") and "|" in line.strip()[1:]:
            table_buf.append(line)
            i += 1
            continue
        else:
            if table_buf:
                flush_table()

        img_m = IMG_RE.match(line)
        if img_m and base_dir:
            img_path = (base_dir / img_m.group(2)).resolve()
            if img_path.exists():
                from reportlab.lib.units import cm as _cm
                try:
                    img = Image(str(img_path), width=17 * _cm, height=6.5 * _cm,
                                kind="proportional")
                    flow.append(img)
                    flow.append(Spacer(1, 8))
                except Exception:
                    flow.append(Paragraph(f"<i>[image: {img_m.group(2)}]</i>", styles["muted"]))
                i += 1
                continue

        m = re.match(r"^(#{1,6})\s+(.*)", line)
        if m:
            level = len(m.group(1))
            text = inline_md(m.group(2).strip())
            key = "title" if level == 1 and not flow else f"h{min(level, 4)}"
            flow.append(Paragraph(text, styles[key]))
            i += 1
            continue

        if not line.strip():
            flow.append(Spacer(1, 4))
            i += 1
            continue

        bullet_m = re.match(r"^\s*[-*]\s+(.*)", line)
        num_m = re.match(r"^\s*(\d+)\.\s+(.*)", line)
        if bullet_m:
            flow.append(Paragraph(f"&bull;&nbsp;&nbsp;{inline_md(bullet_m.group(1))}", styles["li"]))
            i += 1
            continue
        if num_m:
            flow.append(Paragraph(f"{num_m.group(1)}.&nbsp;&nbsp;{inline_md(num_m.group(2))}", styles["li"]))
            i += 1
            continue

        flow.append(Paragraph(inline_md(line), styles["body"]))
        i += 1

    if table_buf:
        flush_table()
    if in_code and code_buf:
        code_text = safe_text("\n".join(code_buf)).replace("—", "-").replace("–", "-")
        flow.append(Preformatted(code_text, styles["code"]))

    return flow


def md_to_pdf(md_path: Path, pdf_path: Path, *, title: str | None = None,
              json_truncate_lines: int = 0):
    md = md_path.read_text(encoding="utf-8")
    styles = make_styles()
    doc = SimpleDocTemplate(
        str(pdf_path), pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=2 * cm, bottomMargin=2 * cm,
        title=title or md_path.stem,
        author="RAGChatbot",
    )
    flow = render_markdown(md, styles, json_truncate_lines=json_truncate_lines,
                            base_dir=md_path.parent)
    doc.build(flow)
    print(f"[OK] wrote {pdf_path}")


def main():
    root = Path(__file__).resolve().parents[1]
    docs = root / "docs"

    md_to_pdf(
        docs / "retrieval_benchmark.md",
        docs / "retrieval_benchmark.pdf",
        title="Retrieval Benchmark — Strategy A vs Strategy B",
        json_truncate_lines=120,
    )
    md_to_pdf(
        docs / "ARCHITECTURE.md",
        docs / "ARCHITECTURE.pdf",
        title="Architecture — Cosine vs Euclidean & Vertex AI Migration",
    )


if __name__ == "__main__":
    main()
