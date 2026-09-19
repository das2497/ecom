# -*- coding: utf-8 -*-
"""Vedic reference tables: Sinhala names, nakshatras, dignities, dasha periods."""

from __future__ import annotations

SIGNS_EN: tuple[str, ...] = (
    "Aries",
    "Taurus",
    "Gemini",
    "Cancer",
    "Leo",
    "Virgo",
    "Libra",
    "Scorpio",
    "Sagittarius",
    "Capricorn",
    "Aquarius",
    "Pisces",
)

SIGNS_SI: tuple[str, ...] = (
    "මේෂ",
    "වෘෂභ",
    "මිථුන",
    "කටක",
    "සිංහ",
    "කන්‍යා",
    "තුලා",
    "වෘශ්චික",
    "ධනු",
    "මකර",
    "කුම්භ",
    "මීන",
)

SIGN_LORDS: tuple[str, ...] = (
    "Mars",
    "Venus",
    "Mercury",
    "Moon",
    "Sun",
    "Mercury",
    "Venus",
    "Mars",
    "Jupiter",
    "Saturn",
    "Saturn",
    "Jupiter",
)

GRAHA_SI: dict[str, str] = {
    "Sun": "රවි",
    "Moon": "චන්ද්‍ර",
    "Mercury": "බුධ",
    "Venus": "ශුක්‍ර",
    "Mars": "කුජ",
    "Jupiter": "ගුරු",
    "Saturn": "ශනි",
    "Rahu": "රාහු",
    "Ketu": "කේතු",
}

# Vimshottari dasha lord order and period lengths (total 120 years).
DASHA_ORDER: tuple[str, ...] = (
    "Ketu",
    "Venus",
    "Sun",
    "Moon",
    "Mars",
    "Rahu",
    "Jupiter",
    "Saturn",
    "Mercury",
)

DASHA_YEARS: dict[str, float] = {
    "Ketu": 7.0,
    "Venus": 20.0,
    "Sun": 6.0,
    "Moon": 10.0,
    "Mars": 7.0,
    "Rahu": 18.0,
    "Jupiter": 16.0,
    "Saturn": 19.0,
    "Mercury": 17.0,
}

DASHA_TOTAL_YEARS = 120.0

# A Vimshottari "year" is a solar year of 365.25 days.
DAYS_PER_YEAR = 365.25

NAKSHATRA_SPAN = 360.0 / 27.0  # 13°20'
PADA_SPAN = NAKSHATRA_SPAN / 4.0  # 3°20'
NAVAMSA_SPAN = 30.0 / 9.0  # 3°20' — one navamsa

# Short Sinhala labels for the chart squares.
GRAHA_SHORT_SI: dict[str, str] = {
    "Sun": "රවි",
    "Moon": "චන්",
    "Mercury": "බුධ",
    "Venus": "ශුක්",
    "Mars": "කුජ",
    "Jupiter": "ගුරු",
    "Saturn": "ශනි",
    "Rahu": "රාහු",
    "Ketu": "කේතු",
}

SIGNS_SHORT_SI: tuple[str, ...] = (
    "මේෂ",
    "වෘෂ",
    "මිථු",
    "කට",
    "සිංහ",
    "කන්‍යා",
    "තුලා",
    "වෘශ්",
    "ධනු",
    "මකර",
    "කුම්",
    "මීන",
)

# South Indian square chart: signs sit in fixed cells, Aries top row second column,
# running clockwise. Values are (row, column) in a 4x4 grid.
SOUTH_INDIAN_CELLS: tuple[tuple[int, int], ...] = (
    (0, 1),  # Aries
    (0, 2),  # Taurus
    (0, 3),  # Gemini
    (1, 3),  # Cancer
    (2, 3),  # Leo
    (3, 3),  # Virgo
    (3, 2),  # Libra
    (3, 1),  # Scorpio
    (3, 0),  # Sagittarius
    (2, 0),  # Capricorn
    (1, 0),  # Aquarius
    (0, 0),  # Pisces
)

# (English, Sinhala) in zodiacal order from 0° sidereal Aries.
NAKSHATRAS: tuple[tuple[str, str], ...] = (
    ("Ashwini", "අස්විද"),
    ("Bharani", "බෙරණ"),
    ("Krittika", "කැති"),
    ("Rohini", "රෙහෙණ"),
    ("Mrigashira", "මුවසිරස"),
    ("Ardra", "අද"),
    ("Punarvasu", "පුනාවස"),
    ("Pushya", "පුෂ"),
    ("Ashlesha", "අස්ලිස"),
    ("Magha", "මා"),
    ("Purva Phalguni", "පුවපල්"),
    ("Uttara Phalguni", "උත්‍රපල්"),
    ("Hasta", "හත"),
    ("Chitra", "සිත"),
    ("Swati", "සා"),
    ("Vishakha", "විසා"),
    ("Anuradha", "අනුර"),
    ("Jyeshtha", "දෙට"),
    ("Mula", "මුල"),
    ("Purva Ashadha", "පුවසල"),
    ("Uttara Ashadha", "උත්‍රසල"),
    ("Shravana", "සුවණ"),
    ("Dhanishta", "දෙනට"),
    ("Shatabhisha", "සියාවස"),
    ("Purva Bhadrapada", "පුවපුටුප"),
    ("Uttara Bhadrapada", "උත්‍රපුටුප"),
    ("Revati", "රේවතී"),
)

# Sign index where each graha is exalted; debilitation is the opposite sign.
EXALTATION_SIGN: dict[str, int] = {
    "Sun": 0,       # Aries
    "Moon": 1,      # Taurus
    "Mars": 9,      # Capricorn
    "Mercury": 5,   # Virgo
    "Jupiter": 3,   # Cancer
    "Venus": 11,    # Pisces
    "Saturn": 6,    # Libra
}

OWN_SIGNS: dict[str, tuple[int, ...]] = {
    "Sun": (4,),
    "Moon": (3,),
    "Mars": (0, 7),
    "Mercury": (2, 5),
    "Jupiter": (8, 11),
    "Venus": (1, 6),
    "Saturn": (9, 10),
}

DIGNITY_SI: dict[str, str] = {
    "exalted": "උච්ච",
    "debilitated": "නීච",
    "own": "ස්වක්ෂේත්‍ර",
    "neutral": "සම",
}


def nakshatra_of(longitude: float) -> dict[str, object]:
    """Nakshatra, pada (1-4) and ruling graha for a sidereal longitude."""
    lon = longitude % 360.0
    index = int(lon // NAKSHATRA_SPAN) % 27
    offset = lon - index * NAKSHATRA_SPAN
    pada = int(offset // PADA_SPAN) + 1
    en, si = NAKSHATRAS[index]
    return {
        "index": index + 1,
        "name": en,
        "name_si": si,
        "pada": pada,
        "lord": DASHA_ORDER[index % 9],
    }


def navamsa_index(longitude: float) -> int:
    """Navamsa (D9) sign index. Counting navamsas straight from 0° Aries reproduces the
    classical movable/fixed/dual starting signs. Multiply before dividing: dividing by
    30/9 lands 30° on 8.999... and drops a whole sign."""
    return int((longitude % 360.0) * 9.0 / 30.0) % 12


def dignity_of(graha: str, sign_index: int) -> str:
    """Sign-level dignity: exalted, debilitated, own or neutral."""
    exalt = EXALTATION_SIGN.get(graha)
    if exalt is not None:
        if sign_index == exalt:
            return "exalted"
        if sign_index == (exalt + 6) % 12:
            return "debilitated"
    if sign_index in OWN_SIGNS.get(graha, ()):
        return "own"
    return "neutral"
