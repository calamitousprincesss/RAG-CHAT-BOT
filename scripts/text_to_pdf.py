"""Render plain-text result files (pytest output, API smoke logs) as PDF."""
from __future__ import annotations
import re
import sys
from pathlib import Path
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Preformatted
)

PRIMARY = HexColor("#1A73E8")
SURFACE_2 = HexColor("#F1F3F4")
BORDER = HexColor("#DADCE0")
MUTED = HexColor("#5F6368")
TEXT = HexColor("#202124")
SUCCESS = HexColor("#137333")
DANGER = HexColor("#D93025")

ANSI = re.compile(r"\x1b\[[0-9;]*m")

UNI = {"—": "-", "–": "-", "✓": "[OK]", "✗": "[X]", "→": "->", "·": "."}


def clean(text: str) -> str:
    text = ANSI.sub("", text)
    for k, v in UNI.items():
        text = text.replace(k, v)
    return text


def make_styles():
    body = "Helvetica"
    return {
        "title": ParagraphStyle("title", fontName=f"{body}-Bold", fontSize=20,
                                textColor=PRIMARY, spaceAfter=14, leading=24),
        "sub": ParagraphStyle("sub", fontName=body, fontSize=10, textColor=MUTED,
                              spaceAfter=12, leading=14),
        "h2": ParagraphStyle("h2", fontName=f"{body}-Bold", fontSize=13,
                             textColor=TEXT, spaceBefore=12, spaceAfter=6, leading=16),
        "pass": ParagraphStyle("pass", fontName=f"{body}-Bold", fontSize=12,
                               textColor=SUCCESS, spaceAfter=8),
        "fail": ParagraphStyle("fail", fontName=f"{body}-Bold", fontSize=12,
                               textColor=DANGER, spaceAfter=8),
        "pre": ParagraphStyle("pre", fontName="Courier", fontSize=8,
                              textColor=TEXT, backColor=SURFACE_2,
                              leftIndent=4, rightIndent=4,
                              spaceBefore=2, spaceAfter=4, leading=10,
                              borderWidth=0.5, borderColor=BORDER, borderPadding=6),
    }


def render_text_to_pdf(input_path: Path, output_path: Path, *, title: str,
                       subtitle: str | None = None):
    content = clean(input_path.read_text(encoding="utf-8", errors="replace"))
    styles = make_styles()
    doc = SimpleDocTemplate(
        str(output_path), pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=2 * cm, bottomMargin=2 * cm,
        title=title, author="RAGChatbot",
    )
    flow = [Paragraph(title, styles["title"])]
    sub = subtitle or f"Generated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    flow.append(Paragraph(sub, styles["sub"]))

    if "passed" in content.lower() or "failed" in content.lower():
        m = re.search(r"(\d+)\s+passed(?:,\s+(\d+)\s+failed)?", content)
        if m:
            passed = m.group(1)
            failed = m.group(2) or "0"
            style = styles["pass"] if failed == "0" else styles["fail"]
            flow.append(Paragraph(f"Result: {passed} passed, {failed} failed", style))

    flow.append(Spacer(1, 6))
    flow.append(Preformatted(content, styles["pre"]))
    doc.build(flow)
    print(f"[OK] wrote {output_path}")


def main():
    root = Path(__file__).resolve().parents[1]
    docs = root / "docs"

    render_text_to_pdf(
        docs / "test_results.txt",
        docs / "test_results.pdf",
        title="Pytest Results",
        subtitle="Verbose output of all unit + integration tests with mocked Vertex SDK",
    )
    render_text_to_pdf(
        docs / "api_smoke_test.txt",
        docs / "api_smoke_test.pdf",
        title="API Smoke Test - Live Claude API",
        subtitle="3 queries x Strategy A vs B against the running Flask server",
    )


if __name__ == "__main__":
    main()
