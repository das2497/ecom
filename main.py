# -*- coding: utf-8 -*-
"""FastAPI astrology microservice.

Endpoints:
- GET  /health -> Passenger smoke test (kept from Step 1).
- POST /echo   -> Passenger smoke test (kept from Step 1).
- POST /chart  -> real Vedic chart calculation (Step 3), ported from the
                  desktop app's engine/astrology_engine.py unchanged.
- POST /pdf    -> birth chart PDF (Step 6), ported from export/pdf_export.py.
"""

import tempfile
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

from data.cities import default_city, get_city
from engine.astrology_engine import AstrologyEngine
from export.pdf_export import build_pdf

app = FastAPI(title="Vedic Astrology API")
_engine = AstrologyEngine()


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


class EchoRequest(BaseModel):
    message: str


@app.post("/echo")
def echo(payload: EchoRequest) -> dict:
    return {"received": payload.message}


class ChartRequest(BaseModel):
    name: str = ""
    birth_date: str = Field(..., description="YYYY/MM/DD")
    birth_time: str = Field(..., description="HH:MM (24h)")
    tz: str = "+05:30"
    city: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None


@app.post("/chart")
def chart(payload: ChartRequest) -> dict:
    if payload.lat is not None and payload.lon is not None:
        lat, lon = payload.lat, payload.lon
    else:
        try:
            place = get_city(payload.city) if payload.city else default_city()
        except KeyError:
            raise HTTPException(status_code=400, detail=f"Unknown city: {payload.city}")
        lat, lon = place["lat"], place["lon"]

    try:
        return _engine.build_chart(
            {
                "name": payload.name,
                "birth_date": payload.birth_date,
                "birth_time": payload.birth_time,
                "tz": payload.tz,
                "lat": lat,
                "lon": lon,
            }
        )
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


class ChatMessage(BaseModel):
    role: str
    content: str


class PdfRequest(BaseModel):
    form: dict[str, Any]
    chart: Optional[dict[str, Any]] = None
    messages: list[ChatMessage] = Field(default_factory=list)


@app.post("/pdf")
def pdf(payload: PdfRequest) -> Response:
    with tempfile.TemporaryDirectory() as tmp:
        out_path = Path(tmp) / "chart.pdf"
        try:
            build_pdf(
                payload.form,
                payload.chart,
                [m.model_dump() for m in payload.messages],
                out_path,
            )
        except FileNotFoundError as exc:
            raise HTTPException(status_code=500, detail=str(exc))
        pdf_bytes = out_path.read_bytes()

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="vedic-chart.pdf"'},
    )
