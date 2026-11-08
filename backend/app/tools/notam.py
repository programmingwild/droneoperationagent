"""Airspace / NOTAM check.

REAL (no credentials required): METAR/TAF proxy to aviationweather.gov (NOAA), with an in-memory
TTL cache (Redis-free) and graceful offline mode.

SIMULATED (honestly labelled): the FAA NOTAM Search API requires registered credentials, so the
NOTAM layer returns a clearly-flagged simulated result (`notam_source: "simulated"`). Every simulated
entry says so, and the Streamlit UI surfaces the flag. Do NOT treat simulated NOTAMs as operational
data — wire a real NOTAM API key before production use.
"""
import threading
import time
from typing import Any

import httpx
from pydantic import BaseModel

from ..config import get_settings

_cache: dict[str, tuple[float, Any]] = {}
_lock = threading.Lock()


class AirspaceReport(BaseModel):
    status: str  # "ok" | "offline_cache" | "offline_no_cache"
    station_metar: list[dict]
    simulated_notams: list[dict]
    notam_source: str  # "simulated" — always, until a real NOTAM API key is wired in
    advisory: str
    wind_max_kt: float | None = None
    flight_category: str | None = None
    fetched_at: float


def _cache_get(key: str) -> Any | None:
    with _lock:
        hit = _cache.get(key)
        if hit and (time.time() - hit[0]) < get_settings().notam_cache_ttl_s:
            return hit[1]
    return None


def _cache_put(key: str, value: Any) -> None:
    with _lock:
        _cache[key] = (time.time(), value)


def _sim_notams(lat: float, lon: float) -> list[dict]:
    """Clearly-labelled SIMULATED advisory feed (stand-in for a keyed FAA NOTAM API)."""
    return [
        {
            "id": "SIM-NOTAM-0001",
            "type": "SIMULATED",
            "text": (
                f"Simulated advisory near ({lat:.3f}, {lon:.3f}): no active Temporary Flight "
                "Restrictions detected in the 5 NM search window (stub feed)."
            ),
            "effective": "2026-11-01T00:00:00Z",
            "expires": "2027-01-01T00:00:00Z",
            "source": "simulated",
        }
    ]


def _summarise_metar(metars: list[dict]) -> tuple[float | None, str | None]:
    wind_max: float | None = None
    best_cat: str | None = None
    for m in metars:
        try:
            wspd = m.get("wspd")
            if wspd is not None:
                w = float(wspd)
                gust = float(m.get("wgst") or 0.0)
                wind_max = max(wind_max or 0.0, w, gust)
            cat = m.get("fltcat")
            if cat:
                best_cat = cat if best_cat is None else ("LIFR" if best_cat == "VFR" and cat != "VFR" else best_cat)
        except (TypeError, ValueError):
            continue
    return wind_max, best_cat


def check_airspace(lat: float, lon: float, radius_deg: float = 0.4) -> AirspaceReport:
    """Check METAR conditions near a coordinate (bbox ±radius_deg) + simulated NOTAMs."""
    settings = get_settings()
    key = f"metar:{lat:.2f}:{lon:.2f}:{radius_deg}"
    cached = _cache_get(key)

    if cached is not None:
        metars, source = cached, "offline_cache"
    else:
        bbox = f"{lon - radius_deg},{lat - radius_deg},{lon + radius_deg},{lat + radius_deg}"
        try:
            resp = httpx.get(
                f"{settings.aviationweather_base_url}/metar",
                params={"bbox": bbox, "format": "json"},
                timeout=settings.http_timeout_s,
            )
            resp.raise_for_status()
            metars = resp.json() if resp.text.strip() else []
            if not isinstance(metars, list):
                metars = []
            _cache_put(key, metars)
            source = "ok"
        except Exception:
            return AirspaceReport(
                status="offline_no_cache",
                station_metar=[],
                simulated_notams=_sim_notams(lat, lon),
                notam_source="simulated",
                advisory=(
                    "Weather feed unreachable and no cached data. NO real-time airspace picture available. "
                    "DO NOT LAUNCH based on this output — obtain METAR/TAF and NOTAM briefing from an "
                    "authorised source (e.g., aviationweather.gov, 1800wxbrief, or LAANC provider)."
                ),
                wind_max_kt=None,
                flight_category=None,
                fetched_at=time.time(),
            )

    wind_max_kt, flight_cat = _summarise_metar(metars)
    notams = _sim_notams(lat, lon)
    advisory_parts = []
    if wind_max_kt is not None:
        advisory_parts.append(f"Max observed wind in bbox: {wind_max_kt:.0f} kt.")
    if flight_cat:
        advisory_parts.append(f"Worst flight category observed: {flight_cat}.")
    advisory_parts.append(
        "NOTAM layer is SIMULATED (no live NOTAM feed configured) — verify NOTAMs/TFRs via your "
        "authoritative source before flight."
    )
    if source == "offline_cache":
        advisory_parts.append("Serving CACHED weather (feed unreachable); treat with caution.")

    return AirspaceReport(
        status=source,
        station_metar=metars[:10],
        simulated_notams=notams,
        notam_source="simulated",
        advisory=" ".join(advisory_parts),
        wind_max_kt=wind_max_kt,
        flight_category=flight_cat,
        fetched_at=time.time(),
    )


def clear_cache() -> None:
    with _lock:
        _cache.clear()
