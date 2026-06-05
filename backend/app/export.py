"""Render a drafted whitepaper (markdown) to a clean, single-column scientific-paper PDF.

Pure-Python (markdown + xhtml2pdf) — no system libraries or headless browser, so it
runs the same locally and on Lambda.
"""
from __future__ import annotations

import io

import markdown as md
from xhtml2pdf import pisa

_CSS = """
@page {
    size: a4;
    margin: 2.2cm 2cm 2.4cm 2cm;
    @frame footer { -pdf-frame-content: footerContent; bottom: 1.1cm; margin-left: 2cm; margin-right: 2cm; height: 1cm; }
}
body { font-family: "Times New Roman", Times, serif; font-size: 10.5pt; line-height: 1.45; text-align: justify; color: #111; }
.doc-title { font-size: 17pt; font-weight: bold; text-align: center; margin: 0 0 12pt 0; line-height: 1.2; }
h1 { font-size: 17pt; font-weight: bold; text-align: center; margin: 0 0 12pt 0; }
h2 { font-size: 12pt; font-weight: bold; margin: 13pt 0 4pt 0; }
h3 { font-size: 11pt; font-weight: bold; margin: 10pt 0 3pt 0; }
p { margin: 0 0 6pt 0; }
a { color: #1a4f8b; text-decoration: none; }
ol, ul { margin: 2pt 0 6pt 16pt; }
li { margin: 0 0 3pt 0; }
hr { border: 0; border-top: 0.5pt solid #ccc; margin: 8pt 0; }
code { font-family: "Courier New", monospace; font-size: 9.5pt; }
"""

_FOOTER = (
    '<div id="footerContent" style="text-align:center; font-size:8pt; color:#888;">'
    'Mentis · page <pdf:pagenumber/></div>'
)


def _extract_title(text: str) -> str | None:
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("# "):
            return s[2:].strip()
    return None


def build_pdf(markdown_text: str, title: str | None = None) -> bytes:
    """Convert markdown to a styled scientific-paper PDF and return the bytes."""
    body_html = md.markdown(markdown_text or "", extensions=["extra", "sane_lists"])
    has_h1 = "<h1" in body_html
    head_title = ""
    if title:
        head_title = f'<div class="doc-title">{title}</div>'
    elif not has_h1:
        head_title = '<div class="doc-title">Mentis Whitepaper</div>'

    html = (
        f'<html><head><meta charset="utf-8"><style>{_CSS}</style></head>'
        f"<body>{_FOOTER}{head_title}{body_html}</body></html>"
    )

    out = io.BytesIO()
    result = pisa.CreatePDF(src=html, dest=out, encoding="utf-8")
    if result.err:
        raise RuntimeError("PDF generation failed")
    return out.getvalue()
