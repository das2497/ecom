# -*- coding: utf-8 -*-
"""A4 PDF of natal data, grahas, dasha and chat (Sinhala font)."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Flowable,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from engine.vedic_tables import GRAHA_SHORT_SI
from export.sinhala_text import ensure_shaped_font, get_shaper, has_sinhala

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_FONT = ROOT / "fonts" / "NotoSansSinhala-Regular.ttf"
FONT_NAME = "NotoSansSinhala"
# The bundled Sinhala face carries no Latin letters, so Latin runs are drawn in a
# built-in base-14 font instead of silently disappearing from the page.
LATIN_FONT = "Helvetica"

log = logging.getLogger(__name__)

ACCENT = colors.HexColor("#1e3a5f")
MUTED = colors.HexColor("#555555")

_BOLD_MD = re.compile(r"\*\*(.+?)\*\*", re.DOTALL)
_HEADING_MD = re.compile(r"^\s{0,3}(#{1,6})\s+(.*)$")
_BULLET_MD = re.compile(r"^\s*[*\-+]\s+(.*)$")


def _register_font(font_path: Path | None = None) -> str:
    """Register the shaped font. Falls back to the raw font only if generation fails."""
    if font_path is not None:
        path = Path(font_path)
        if not path.exists():
            raise FileNotFoundError(
                f"සිංහල ෆොන්ට් නැත: {path}. fonts/ හි NotoSansSinhala-Regular.ttf තබන්න."
            )
    else:
        try:
            path = ensure_shaped_font()
        except Exception:
            path = DEFAULT_FONT
            if not path.exists():
                raise
    if FONT_NAME not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(FONT_NAME, str(path)))
        # Only a regular weight ships with the app; map every style to it so
        # <b> markup keeps Sinhala glyphs instead of falling back to Helvetica.
        pdfmetrics.registerFontFamily(
            FONT_NAME, normal=FONT_NAME, bold=FONT_NAME, italic=FONT_NAME, boldItalic=FONT_NAME
        )
    return FONT_NAME


def _shape(text: str) -> str:
    """Reorder/ligate Sinhala into glyph codepoints ReportLab can draw verbatim."""
    shaper = get_shaper()
    if shaper is None or not text:
        return text
    return shaper.shape(text)


def _cell(text: str) -> str:
    """Shape a table cell. Pure ASCII (dates, numbers) needs no shaping."""
    return _shape(text) if has_sinhala(text) else text


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _coverage() -> frozenset[int]:
    try:
        return frozenset(pdfmetrics.getFont(FONT_NAME).face.charToGlyph.keys())
    except Exception:
        return frozenset()


def _latin_safe(ch: str) -> bool:
    """Helvetica is a WinAnsi font, so it covers cp1252 and nothing else."""
    try:
        ch.encode("cp1252")
    except UnicodeEncodeError:
        return False
    return True


def _classify(ch: str, covered: frozenset[int]) -> str:
    if ch in "\n\t" or ord(ch) in covered:
        return "sinhala"
    if _latin_safe(ch):
        return "latin"
    return "unsupported"


def _font_split(text: str, covered: frozenset[int]) -> str:
    """Split text by which font can draw it.

    Anything neither font covers is dropped: the model occasionally emits a
    stray word in another script, and ReportLab would paint those as .notdef
    black blocks.
    """
    if not text:
        return ""
    out: list[str] = []
    buf: list[str] = []
    buf_kind = ""
    dropped: list[str] = []

    def flush() -> None:
        if not buf:
            return
        raw = "".join(buf)
        if buf_kind == "latin":
            out.append(f'<font name="{LATIN_FONT}">{_escape(raw)}</font>')
        elif buf_kind == "sinhala":
            out.append(_escape(_shape(raw)))
        else:
            dropped.append(raw)
        buf.clear()

    for ch in text:
        kind = _classify(ch, covered)
        if buf and kind != buf_kind:
            flush()
        buf_kind = kind
        buf.append(ch)
    flush()
    if dropped:
        log.warning("Dropped unrenderable characters from PDF: %r", "".join(dropped))
    return "".join(out)


def _rich(text: str, covered: frozenset[int]) -> str:
    """Markdown bold + per-run font fallback, safe for reportlab's mini-markup."""
    pieces = re.split(r"\*\*(.+?)\*\*", text, flags=re.DOTALL)
    out: list[str] = []
    for i, piece in enumerate(pieces):
        if not piece:
            continue
        rendered = _font_split(piece, covered)
        out.append(f"<b>{rendered}</b>" if i % 2 else rendered)
    return "".join(out)


def _markdown_flowables(text: str, body, heading, bullet, covered: frozenset[int]) -> list[Any]:
    """Render the model's Markdown as paragraphs, headings and bullets."""
    out: list[Any] = []
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            continue
        head = _HEADING_MD.match(line)
        if head:
            out.append(Paragraph(_font_split(_BOLD_MD.sub(r"\1", head.group(2)), covered), heading))
            continue
        item = _BULLET_MD.match(line)
        if item:
            marker = _font_split("• ", covered)
            out.append(Paragraph(f"{marker}{_rich(item.group(1), covered)}", bullet))
            continue
        out.append(Paragraph(_rich(line, covered), body))
    return out


# North Indian style kendara geometry, in a fixed 0..300 design space (matches
# the web frontend's VedicChart.jsx exactly, so PDF and web charts agree).
# Each of the 12 houses is either an un-split edge box or one of two triangles
# sharing a corner cell; house 1 sits at the top edge and the rest run
# clockwise, per the standard North Indian convention.
_HOUSE_BOXES: dict[int, tuple[float, float, float, float]] = {
    1: (100, 0, 200, 100),
    4: (200, 100, 300, 200),
    7: (100, 200, 200, 300),
    10: (0, 100, 100, 200),
}
_HOUSE_TRIANGLES: dict[int, tuple[tuple[float, float], ...]] = {
    2: ((200, 0), (300, 0), (200, 100)),
    3: ((300, 0), (300, 100), (200, 100)),
    5: ((300, 200), (300, 300), (200, 200)),
    6: ((200, 200), (200, 300), (300, 300)),
    8: ((100, 200), (100, 300), (0, 300)),
    9: ((0, 200), (0, 300), (100, 200)),
    11: ((0, 0), (0, 100), (100, 100)),
    12: ((0, 0), (100, 0), (100, 100)),
}
_HOUSE_ANCHORS: dict[int, tuple[tuple[float, float], tuple[float, float]]] = {
    1: ((107, 14), (150, 58)),
    2: ((208, 14), (235, 40)),
    3: ((285, 90), (258, 72)),
    4: ((207, 114), (250, 158)),
    5: ((285, 212), (262, 235)),
    6: ((208, 288), (232, 262)),
    7: ((107, 214), (150, 258)),
    8: ((90, 288), (62, 262)),
    9: ((12, 212), (38, 235)),
    10: ((8, 114), (50, 158)),
    11: ((12, 90), (38, 72)),
    12: ((88, 14), (65, 40)),
}
_DIAGONALS: tuple[tuple[tuple[float, float], tuple[float, float]], ...] = (
    ((0, 0), (100, 100)),
    ((300, 0), (200, 100)),
    ((200, 200), (300, 300)),
    ((100, 200), (0, 300)),
)


class NorthIndianChart(Flowable):
    """North Indian kendara: houses sit in fixed diamond positions (house 1 at
    the top, running clockwise) and signs rotate around them. Matches the web
    app's VedicChart.jsx geometry so the PDF and the browser view agree."""

    def __init__(
        self,
        occupants: dict[int, list[str]],
        center_label: str,
        font: str,
        size: float = 224.0,
    ) -> None:
        super().__init__()
        self.occupants = occupants
        self.center_label = center_label
        self.font = font
        self.size = size

    def wrap(self, availWidth, availHeight):
        return self.size, self.size

    def _pt(self, x: float, y: float) -> tuple[float, float]:
        scale = self.size / 300.0
        return x * scale, self.size - y * scale

    def draw(self) -> None:
        c = self.canv

        for house in range(1, 13):
            is_lagna = house == 1
            if house in _HOUSE_BOXES:
                x0, y0, x1, y1 = _HOUSE_BOXES[house]
                (px0, py0) = self._pt(x0, y0)
                (px1, py1) = self._pt(x1, y1)
                x, y = min(px0, px1), min(py0, py1)
                w, h = abs(px1 - px0), abs(py1 - py0)
                if is_lagna:
                    c.setFillColor(colors.HexColor("#fdf3d0"))
                    c.rect(x, y, w, h, stroke=0, fill=1)
                c.setStrokeColor(ACCENT)
                c.setLineWidth(0.9)
                c.rect(x, y, w, h, stroke=1, fill=0)
            else:
                pts = [self._pt(px, py) for px, py in _HOUSE_TRIANGLES[house]]
                path = c.beginPath()
                path.moveTo(*pts[0])
                path.lineTo(*pts[1])
                path.lineTo(*pts[2])
                path.close()
                if is_lagna:
                    c.setFillColor(colors.HexColor("#fdf3d0"))
                    c.drawPath(path, stroke=0, fill=1)

        # Outer border + inner grid + corner diagonals.
        c.setStrokeColor(ACCENT)
        c.setLineWidth(1.1)
        ox0, oy0 = self._pt(0, 0)
        ox1, oy1 = self._pt(300, 300)
        c.rect(min(ox0, ox1), min(oy0, oy1), abs(ox1 - ox0), abs(oy1 - oy0), stroke=1, fill=0)
        c.setLineWidth(0.7)
        for a, b in (((100, 0), (100, 300)), ((200, 0), (200, 300)), ((0, 100), (300, 100)), ((0, 200), (300, 200))):
            c.line(*self._pt(*a), *self._pt(*b))
        for a, b in _DIAGONALS:
            c.line(*self._pt(*a), *self._pt(*b))

        # House numbers + occupant lists.
        for house in range(1, 13):
            num_pos, text_pos = _HOUSE_ANCHORS[house]
            nx, ny = self._pt(*num_pos)
            c.setFillColor(colors.HexColor("#8a6d0b") if house == 1 else colors.HexColor("#b23b3b"))
            c.setFont(self.font, 6.2)
            c.drawString(nx, ny - 5, str(house))

            names = self.occupants.get(house, [])
            if names:
                tx, ty = self._pt(*text_pos)
                c.setFillColor(ACCENT)
                c.setFont(self.font, 6.4)
                line_y = ty
                for name in names[:4]:
                    c.drawCentredString(tx, line_y - 3, _shape(name))
                    line_y -= 7.6

        # Centre label.
        c.setFillColor(colors.black)
        c.setFont(self.font, 8.5)
        cx, cy = self._pt(150, 150)
        c.drawCentredString(cx, cy - 3.0, _shape(self.center_label))


def _occupants(chart_json: dict[str, Any], navamsa: bool) -> dict[int, list[str]]:
    """Group planets by house. D1 houses come straight from the engine; D9
    houses are derived with the same whole-sign formula, applied to
    navamsa_sign_index relative to the navamsa lagna (mirrors the web
    frontend's VedicChart occupant computation)."""
    asc = chart_json.get("ascendant") or {}
    asc_navamsa_index = int(asc.get("navamsa_sign_index") or 0)

    out: dict[int, list[str]] = {}
    for p in chart_json.get("planets") or []:
        if navamsa:
            sign_index = p.get("navamsa_sign_index")
            if not isinstance(sign_index, int):
                continue
            house = (sign_index - asc_navamsa_index) % 12 + 1
        else:
            house = p.get("house")
            if not isinstance(house, int):
                continue

        label = GRAHA_SHORT_SI.get(str(p.get("name")), str(p.get("name_si") or ""))
        if p.get("retrograde"):
            label += " (ව)"
        out.setdefault(house, []).append(label)
    return out


def _chart_column(flowable: Flowable, caption: str, font: str) -> Table:
    """A chart with its title caption stacked underneath, matching the web
    frontend's chart-pair-caption layout."""
    style = ParagraphStyle(
        "ChartCaption", fontName=font, fontSize=7.5, alignment=1, textColor=MUTED, spaceBefore=4
    )
    inner = Table([[flowable], [Paragraph(_shape(caption), style)]], colWidths=[224])
    inner.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return inner


def _charts_row(chart_json: dict[str, Any], font: str) -> Table:
    rasi = NorthIndianChart(_occupants(chart_json, False), "ලග්නය", font)
    navamsa = NorthIndianChart(_occupants(chart_json, True), "නවාංශකය", font)
    table = Table(
        [[_chart_column(rasi, "රාශි චක්‍රය (D1)", font), _chart_column(navamsa, "නවාංශකය (D9)", font)]],
        colWidths=[236, 236],
    )
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return table


def _page_furniture(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFillColor(MUTED)
    canvas.setFont(LATIN_FONT, 8)
    canvas.drawString(18 * mm, 10 * mm, "Vedic Astrology AI")
    canvas.setFont(FONT_NAME, 8)
    canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, _shape(f"පිටුව {doc.page}"))
    canvas.setStrokeColor(colors.HexColor("#cccccc"))
    canvas.line(18 * mm, 13 * mm, A4[0] - 18 * mm, 13 * mm)
    canvas.restoreState()


def _planet_table(chart_json: dict[str, Any], font: str) -> Table:
    rows = [["ග්‍රහයා", "රාශිය", "භාවය", "අංශක", "නැකත", "පාද", "නවාංශකය", "බලය"]]
    dignity_si = {
        "exalted": "උච්ච",
        "debilitated": "නීච",
        "own": "ස්වක්ෂේත්‍ර",
        "neutral": "",
    }
    for p in chart_json.get("planets") or []:
        marks = dignity_si.get(str(p.get("dignity")), "")
        if p.get("retrograde"):
            marks = f"{marks} වක්‍ර".strip()
        rows.append(
            [
                p.get("name_si") or p.get("name", ""),
                p.get("sign_si") or p.get("sign", ""),
                str(p.get("house", "")),
                # No degree sign: the bundled Sinhala face has no U+00B0 glyph.
                f"{float(p.get('degree') or 0):.2f}",
                p.get("nakshatra_si") or "",
                str(p.get("nakshatra_pada") or ""),
                p.get("navamsa_sign_si") or "",
                marks,
            ]
        )
    rows = [[_cell(str(cell)) for cell in row] for row in rows]
    table = Table(rows, colWidths=[48, 54, 32, 42, 70, 26, 56, 64], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), font),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f6f9")]),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return table


def _panchanga_table(chart_json: dict[str, Any], font: str, covered: frozenset[int]) -> Table:
    asc = chart_json.get("ascendant") or {}
    moon_nak = chart_json.get("moon_nakshatra") or {}
    panch = chart_json.get("panchanga") or {}
    tithi = panch.get("tithi") or {}
    yoga = panch.get("yoga") or {}
    karana = panch.get("karana") or {}

    lagna = (
        f"{asc.get('sign_si') or asc.get('sign')} {float(asc.get('degree') or 0):.2f}°"
    )
    nakshatra = (
        f"{moon_nak.get('name_si') or '—'} · පාද {moon_nak.get('pada') or '—'}"
    )
    pairs = [
        ("ලග්නය", lagna),
        ("ලග්නාධිපති", str(asc.get("lord") or "—")),
        ("ජන්ම නැකත", nakshatra),
        ("නැකත් අධිපති", str(moon_nak.get("lord") or "—")),
        ("වාරය", str((panch.get("vara") or {}).get("name_si") or "—")),
        ("තිථිය", str(tithi.get("name_si") or "—")),
        ("ගණය", str((panch.get("gana") or {}).get("name_si") or "—")),
        ("යෝගය", str(yoga.get("name") or "—")),
        ("කරණය", str(karana.get("name") or "—")),
        ("නවාංශක ලග්නය", str(asc.get("navamsa_sign_si") or "—")),
    ]

    label_style = ParagraphStyle(
        "PanchLabel", fontName=font, fontSize=8, leading=11, textColor=MUTED
    )
    value_style = ParagraphStyle("PanchValue", fontName=font, fontSize=8.5, leading=11)

    rows = []
    for i in range(0, len(pairs), 2):
        row = []
        for label, value in pairs[i : i + 2]:
            row.append(Paragraph(_font_split(label, covered), label_style))
            row.append(Paragraph(_font_split(value, covered), value_style))
        while len(row) < 4:
            row.append("")
        rows.append(row)

    table = Table(rows, colWidths=[70, 156, 88, 158])
    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), font),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#c9d3e0")),
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eef2f7")),
                ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#eef2f7")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return table


def _dasha_table(dasha: dict[str, Any], font: str) -> Table:
    current = (dasha.get("current") or {}).get("mahadasha")
    rows = [["මහ දශාව", "ආරම්භය", "අවසානය", "වර්ෂ"]]
    highlight: list[int] = []
    for i, maha in enumerate(dasha.get("mahadasha") or [], start=1):
        if maha.get("lord") == current:
            highlight.append(i)
        rows.append(
            [
                maha.get("lord_si") or maha.get("lord", ""),
                str(maha.get("start", "")),
                str(maha.get("end", "")),
                f"{float(maha.get('years') or 0):.0f}",
            ]
        )
    style = [
        ("FONTNAME", (0, 0), (-1, -1), font),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    for row in highlight:
        style.append(("BACKGROUND", (0, row), (-1, row), colors.HexColor("#ffeaa7")))
    rows = [[_cell(str(cell)) for cell in row] for row in rows]
    table = Table(rows, colWidths=[80, 90, 90, 50], repeatRows=1)
    table.setStyle(TableStyle(style))
    return table


def build_pdf(
    form: dict[str, Any],
    chart_json: dict[str, Any] | None,
    messages: list[dict[str, Any]],
    out_path: str | Path,
    font_path: Path | None = None,
) -> Path:
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    font = _register_font(font_path)
    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "SiTitle", parent=styles["Title"], fontName=font, fontSize=16, leading=22
    )
    h = ParagraphStyle(
        "SiH",
        parent=styles["Heading2"],
        fontName=font,
        fontSize=12.5,
        leading=17,
        textColor=ACCENT,
        spaceBefore=8,
    )
    sub_h = ParagraphStyle(
        "SiSubH", parent=h, fontSize=11, leading=15, textColor=colors.HexColor("#2c4a70")
    )
    body = ParagraphStyle(
        "SiBody", parent=styles["Normal"], fontName=font, fontSize=9.5, leading=14
    )
    bullet = ParagraphStyle("SiBullet", parent=body, leftIndent=12)

    doc = SimpleDocTemplate(
        str(out),
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=18 * mm,
        title="Vedic Astrology AI",
        author="Vedic Astrology AI",
    )
    covered = _coverage()
    story: list[Any] = []
    story.append(Paragraph(_font_split("Vedic Astrology AI — කේන්දර කියවීම", covered), title))
    story.append(Spacer(1, 8))

    story.append(Paragraph(_shape("උපන් දත්ත"), h))
    story.append(
        Paragraph(
            _font_split(
                f"නම: {form.get('name') or '—'}\n"
                f"දිනය: {form.get('birth_date') or '—'}   වේලාව: {form.get('birth_time') or '—'} "
                f"({form.get('tz') or '+05:30'})\n"
                f"ස්ථානය: {form.get('city') or '—'} "
                f"(lat {form.get('lat')}, lon {form.get('lon')})",
                covered,
            ).replace("\n", "<br/>"),
            body,
        )
    )

    if chart_json:
        settings = chart_json.get("settings") or {}

        story.append(Paragraph(_font_split("ලග්නය සහ පංචාංගය", covered), h))
        story.append(_panchanga_table(chart_json, font, covered))

        story.append(Spacer(1, 10))
        story.append(_charts_row(chart_json, font))
        story.append(Spacer(1, 4))
        story.append(
            Paragraph(
                _font_split(
                    "රතු අංකය = භාවය · ලග්නය (1 වන භාවය) කහ පැහැයෙන් සලකුණු කර ඇත · (ව) = වක්‍ර", covered
                ),
                ParagraphStyle("SiCap", parent=body, fontSize=7.5, textColor=MUTED),
            )
        )

        story.append(Paragraph(_font_split("ග්‍රහ ස්ථාන (Lahiri · Whole Sign)", covered), h))
        story.append(_planet_table(chart_json, font))
        story.append(Spacer(1, 4))
        story.append(
            Paragraph(
                _font_split(
                    f"අයනාංශ: Lahiri {float(settings.get('ayanamsa_degree') or 0):.4f}°",
                    covered,
                ),
                ParagraphStyle("SiCap2", parent=body, fontSize=7.5, textColor=MUTED),
            )
        )

        dasha = chart_json.get("dasha") or {}
        if dasha.get("mahadasha"):
            block: list[Any] = [Paragraph(_shape("විංශෝත්තරී දශා"), h)]
            current = dasha.get("current") or {}
            if current.get("mahadasha_si"):
                block.append(
                    Paragraph(
                        _font_split(
                            f"වත්මන් දශාව ({dasha.get('as_of')}): "
                            f"{current.get('mahadasha_si')} මහ දශාව / "
                            f"{current.get('antardasha_si') or '—'} අන්තර් දශාව "
                            f"({current.get('antardasha_start')} — {current.get('antardasha_end')})",
                            covered,
                        ),
                        body,
                    )
                )
            block.append(Spacer(1, 6))
            block.append(_dasha_table(dasha, font))
            story.append(KeepTogether(block))

    transcript = [
        m
        for m in messages
        if m.get("role") in ("user", "assistant")
        and not str(m.get("content") or "").startswith("පහත කේන්දර JSON")
    ]
    if transcript:
        story.append(Paragraph(_shape("සංවාදය"), h))
        for m in transcript:
            who = "ඔබ" if m.get("role") == "user" else "ආචාර්ය"
            story.append(Paragraph(_shape(who), sub_h))
            story.extend(
                _markdown_flowables(
                    str(m.get("content") or ""), body, sub_h, bullet, covered
                )
            )
            story.append(Spacer(1, 6))

    story.append(Spacer(1, 14))
    story.append(
        Paragraph(
            _font_split(
                "මෙය ජ්‍යෝතිෂ්‍ය මගපෙන්වීමකි. "
                "වෛද්‍ය හෝ මූල්‍ය උපදෙස්වලට ආදේශකයක් නොවේ.",
                covered,
            ),
            ParagraphStyle("SiFoot", parent=body, textColor=MUTED, fontSize=8.5),
        )
    )
    doc.build(story, onFirstPage=_page_furniture, onLaterPages=_page_furniture)
    return out
