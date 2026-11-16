"""Render docs/technical-brief.md to docs/technical_brief.pdf. Body must stay within 3 pages."""

from pathlib import Path

from fpdf import FPDF

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "technical-brief.md"
TARGET = ROOT / "docs" / "technical_brief.pdf"


def plain(text: str) -> str:
    return (
        text.replace("\u2019", "'")
        .replace("\u2018", "'")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
        .replace("\u2013", "-")
        .replace("\u2014", "-")
    )


class Brief(FPDF):
    def footer(self) -> None:
        self.set_y(-12)
        self.set_font("Helvetica", size=8)
        self.cell(0, 8, str(self.page_no()), align="C")


def write_block(pdf: FPDF, text: str) -> None:
    for raw in plain(text).splitlines():
        line = raw.strip()
        if not line:
            pdf.ln(1.5)
            continue
        if line.startswith("# "):
            pdf.set_font("Helvetica", "B", 14)
            pdf.multi_cell(0, 7, line[2:])
            pdf.ln(1)
        elif line.startswith("## "):
            pdf.set_font("Helvetica", "B", 11)
            pdf.multi_cell(0, 6, line[3:])
        elif line.startswith("- "):
            pdf.set_font("Helvetica", size=10)
            pdf.multi_cell(0, 4.6, "- " + line[2:])
        else:
            pdf.set_font("Helvetica", size=10)
            pdf.multi_cell(0, 4.6, line)


def main() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    body, references = source.split("## References", 1)
    pdf = Brief(format="Letter")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_margins(16, 14, 16)
    pdf.add_page()
    write_block(pdf, body)
    body_pages = pdf.page_no()
    if body_pages > 3:
        raise SystemExit(f"brief body is {body_pages} pages; the limit is 3 excluding references")
    pdf.add_page()
    write_block(pdf, "## References\n" + references)
    pdf.output(str(TARGET))
    print(f"body_pages={body_pages} total_pages={pdf.page_no()} bytes={TARGET.stat().st_size}")


if __name__ == "__main__":
    main()
