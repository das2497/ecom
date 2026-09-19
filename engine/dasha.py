# -*- coding: utf-8 -*-
"""Vimshottari dasha: mahadasha and antardasha timeline from the Moon's nakshatra."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from engine.vedic_tables import (
    DASHA_ORDER,
    DASHA_TOTAL_YEARS,
    DASHA_YEARS,
    DAYS_PER_YEAR,
    GRAHA_SI,
    NAKSHATRA_SPAN,
)


def _years(n: float) -> timedelta:
    return timedelta(days=n * DAYS_PER_YEAR)


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d")


def _sequence_from(lord: str) -> list[str]:
    start = DASHA_ORDER.index(lord)
    return [DASHA_ORDER[(start + i) % 9] for i in range(9)]


def _antardashas(maha_lord: str, maha_start: datetime, maha_years: float) -> list[dict[str, Any]]:
    """Sub-periods of a mahadasha, proportional to each lord's share of 120 years."""
    out: list[dict[str, Any]] = []
    cursor = maha_start
    for sub in _sequence_from(maha_lord):
        span = maha_years * DASHA_YEARS[sub] / DASHA_TOTAL_YEARS
        end = cursor + _years(span)
        out.append(
            {
                "lord": sub,
                "lord_si": GRAHA_SI[sub],
                "start": _iso(cursor),
                "end": _iso(end),
            }
        )
        cursor = end
    return out


def vimshottari(
    moon_longitude: float,
    birth_dt: datetime,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Full 120-year mahadasha timeline with antardashas and the currently running period.

    The first mahadasha starts before birth; only its unexpired balance is lived.
    """
    lon = moon_longitude % 360.0
    nak_index = int(lon // NAKSHATRA_SPAN) % 27
    first_lord = DASHA_ORDER[nak_index % 9]
    elapsed_fraction = (lon - nak_index * NAKSHATRA_SPAN) / NAKSHATRA_SPAN

    first_years = DASHA_YEARS[first_lord]
    balance_years = first_years * (1.0 - elapsed_fraction)
    # Back-date the notional start so the remaining balance lands exactly on the birth moment.
    cursor = birth_dt - _years(first_years * elapsed_fraction)

    mahadashas: list[dict[str, Any]] = []
    for lord in _sequence_from(first_lord):
        span = DASHA_YEARS[lord]
        end = cursor + _years(span)
        mahadashas.append(
            {
                "lord": lord,
                "lord_si": GRAHA_SI[lord],
                "start": _iso(cursor),
                "end": _iso(end),
                "years": span,
                "antardasha": _antardashas(lord, cursor, span),
            }
        )
        cursor = end

    reference = now or datetime.now()
    today = _iso(reference)
    current: dict[str, Any] | None = None
    for maha in mahadashas:
        if maha["start"] <= today < maha["end"]:
            antar = next(
                (a for a in maha["antardasha"] if a["start"] <= today < a["end"]),
                None,
            )
            current = {
                "mahadasha": maha["lord"],
                "mahadasha_si": maha["lord_si"],
                "mahadasha_start": maha["start"],
                "mahadasha_end": maha["end"],
                "antardasha": antar["lord"] if antar else None,
                "antardasha_si": antar["lord_si"] if antar else None,
                "antardasha_start": antar["start"] if antar else None,
                "antardasha_end": antar["end"] if antar else None,
            }
            break

    return {
        "system": "vimshottari",
        "as_of": today,
        "birth_balance": {
            "lord": first_lord,
            "lord_si": GRAHA_SI[first_lord],
            "years_remaining": round(balance_years, 4),
        },
        "current": current,
        "mahadasha": mahadashas,
    }


def parse_birth_datetime(birth_date: str, birth_time: str) -> datetime:
    """Parse 'YYYY/MM/DD' + 'HH:MM[:SS]' into a naive datetime."""
    time_part = birth_time.strip()
    if len(time_part) == 5:
        time_part += ":00"
    return datetime.strptime(f"{birth_date.strip()} {time_part}", "%Y/%m/%d %H:%M:%S")
