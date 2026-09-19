# -*- coding: utf-8 -*-
"""Sinhala text shaping for ReportLab.

ReportLab draws one glyph per character in logical order. Sinhala needs a real
OpenType shaper: the vowel signs ෙ ේ ො ෝ ෛ are written *before* the consonant
they follow in memory, and sequences like ්‍ර / ්‍ය form single ligature glyphs.
Without shaping "මෙය" comes out as "මයෙ" and the ZWJ is drawn as a visible box.

So text is shaped with HarfBuzz first, then handed to ReportLab as one codepoint
per output glyph. Those codepoints live in the Private Use Area of a generated
copy of the font, which also repairs a defect in the bundled Noto Sans Sinhala:
fifteen spacing vowel signs are tagged GDEF class 3 (MARK), so HarfBuzz zeroes
their advance and they stack on top of the preceding letter.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

log = logging.getLogger(__name__)

_WHITESPACE = re.compile(r"(\s+)")

ROOT = Path(__file__).resolve().parent.parent
SOURCE_FONT = ROOT / "fonts" / "NotoSansSinhala-Regular.ttf"
GENERATED_DIR = ROOT / "fonts" / "generated"
SHAPED_FONT = GENERATED_DIR / "NotoSansSinhala-Shaped.ttf"

PUA_BASE = 0xE000
PUA_LAST = 0xF8FF
# Bump when the generation logic changes so cached fonts are rebuilt.
BUILD_VERSION = 1
STAMP = GENERATED_DIR / "build.stamp"

SINHALA_START = 0x0D80
SINHALA_END = 0x0DFF


def _build_shaped_font(source: Path, target: Path) -> None:
    """Repair GDEF classes and add a PUA codepoint for every glyph."""
    from fontTools.ttLib import TTFont

    font = TTFont(str(source))
    metrics = font["hmtx"]

    repaired = 0
    gdef = font.get("GDEF")
    class_def = getattr(getattr(gdef, "table", None), "GlyphClassDef", None)
    if class_def is not None:
        for name, klass in list(class_def.classDefs.items()):
            # A glyph that advances the pen is a spacing glyph, not a mark.
            if klass == 3 and metrics[name][0] > 0:
                class_def.classDefs[name] = 1
                repaired += 1

    glyph_order = font.getGlyphOrder()
    unicode_tables = [t for t in font["cmap"].tables if t.isUnicode()]
    added = 0
    for gid, name in enumerate(glyph_order):
        if gid == 0:
            continue
        codepoint = PUA_BASE + gid
        if codepoint > PUA_LAST:
            log.warning("Font has more glyphs than PUA slots; %s not addressable", name)
            break
        for table in unicode_tables:
            if codepoint not in table.cmap:
                table.cmap[codepoint] = name
                added += 1

    target.parent.mkdir(parents=True, exist_ok=True)
    font.save(str(target))
    log.info("Built shaped font: %d GDEF fixes, %d PUA entries", repaired, added)


def ensure_shaped_font() -> Path:
    """Generate the shaped font once, refreshing it if the source font changes."""
    if not SOURCE_FONT.exists():
        raise FileNotFoundError(
            f"සිංහල ෆොන්ට් නැත: {SOURCE_FONT}. "
            "fonts/ හි NotoSansSinhala-Regular.ttf තබන්න."
        )
    stamp = f"{BUILD_VERSION}:{SOURCE_FONT.stat().st_mtime_ns}"
    if SHAPED_FONT.exists() and STAMP.exists():
        try:
            if STAMP.read_text(encoding="utf-8").strip() == stamp:
                return SHAPED_FONT
        except OSError:
            pass
    _build_shaped_font(SOURCE_FONT, SHAPED_FONT)
    try:
        STAMP.write_text(stamp, encoding="utf-8")
    except OSError:
        log.warning("Could not write font build stamp")
    return SHAPED_FONT


class SinhalaShaper:
    """Shapes runs of text into PUA codepoints addressing the font's glyphs."""

    def __init__(self, font_path: Path) -> None:
        import uharfbuzz as hb

        self._hb = hb
        blob = hb.Blob.from_file_path(str(font_path))
        self._face = hb.Face(blob)
        self._font = hb.Font(self._face)
        self._cache: dict[str, str] = {}

    def _shape_word(self, word: str) -> str:
        cached = self._cache.get(word)
        if cached is not None:
            return cached
        buf = self._hb.Buffer()
        buf.add_str(word)
        buf.guess_segment_properties()
        self._hb.shape(self._font, buf)
        glyphs = [info.codepoint for info in buf.glyph_infos]
        if any(g == 0 for g in glyphs):
            # The font has no glyph for something here; leave it for the caller's
            # Latin fallback rather than emitting an unmapped codepoint.
            shaped = word
        else:
            shaped = "".join(chr(PUA_BASE + g) for g in glyphs)
        self._cache[word] = shaped
        return shaped

    def shape(self, text: str) -> str:
        """Shape word by word, passing whitespace through untouched.

        Whitespace must survive verbatim: ReportLab needs real spaces to wrap
        lines, and a newline inside a shaped run would shape to .notdef.
        """
        if not text:
            return ""
        return "".join(
            part if _WHITESPACE.fullmatch(part) else self._shape_word(part)
            for part in _WHITESPACE.split(text)
            if part
        )


_shaper: SinhalaShaper | None = None


def get_shaper() -> SinhalaShaper | None:
    """The shared shaper, or None if shaping is unavailable."""
    global _shaper
    if _shaper is None:
        try:
            _shaper = SinhalaShaper(ensure_shaped_font())
        except Exception:
            log.exception("Sinhala shaping unavailable; text may render incorrectly")
            return None
    return _shaper


def has_sinhala(text: str) -> bool:
    return any(SINHALA_START <= ord(ch) <= SINHALA_END for ch in text)
