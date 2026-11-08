"""Airspace / NOTAM check.

REAL (no credentials required): METAR/TAF proxy to aviationweather.gov (NOAA), with an in-memory
TTL cache (Redis-free) and graceful offline mode.

NOTAMs (pluggable, honest):
  - NOTAM_PROVIDER=simulated (default): clearly-flagged simulated result (no live NOTAM feed).
  - NOTAM_PROVIDER=http: real fetch from a keyed NOTAM HTTP endpoint when NOTAM_API_URL and
    NOTAM_API_KEY are configured. The response is mapped best-effort into our schema and
    `notam_source` is set to "http:<host>" (truthful). On any failure it falls back to a
    clearly-labelled simulated advisory — never silent.

NOTE: FAA's official NOTAM systems require registered access; many operators use a commercial
provider. Configure NOTAM_API_URL/NOTAM_API_KEY for your provider, or keep simulated for demos.
Do NOT treat simulated NOTAMs as operational data.
"""
import threading
import time
from typing import Any
from urllib.parse import urlparse

import httpx
from pydantic import BaseModel

from ..config import get_settings

_cache: dict[str, tuple[float, Any]] = {}
_lock = threading.Lock()


class AirspaceReport(BaseModel):
    status: str  # "ok" | "offline_cache" | "offline_no_cache"
    station_metar: list[dict]
    notams: list[dict]
    notam_source: str  # "simulated" | "http:<host>"
    advisory: str
    wind_max_kt: float | None = None
    flight_category: str | None = None
    fetched_at: float
    # Back-compat: older callers/UI expect `simulated_notams`.
    simulated_notams: list[dict] = []


def _cache_get(key: str) -> Any | None:
    with _lock:
        hit = _cache.get(key)
        if hit and (time.time() - hit[0]) < get_settings().notam_cache_ttl_s:
            return hit[1]
    return None


def _cache_put(key: str, value: Any) -> None:
    with _lock:
        _cache[key] = (time.time(), value)


def _sim_notams(lat: float, lon: float, reason: str | None = None) -> list[dict]:
    """Clearly-labelled SIMULATED advisory (fallback / demo). Never operational."""
    text = (
        f"Simulated advisory near ({lat:.3f}, {lon:.3f}): no active Temporary Flight "
        "Restrictions detected in the 5 NM search window (stub feed)."
    )
    if reason:
        text += f" ({reason})"
    return [{
        "id": "SIM-NOTAM-0001",
        "type": "SIMULATED",
        "text": text,
        "effective": "2026-11-01T00:00:00Z",
        "expires": "2027-01-01T00:00:00Z",
        "source": "simulated",
    }]


def _fetch_real_notams(lat: float, lon: float, radius_deg: float) -> tuple[list[dict], str] | None:
    """Fetch NOTAMs from a configured keyed HTTP endpoint. Returns (notams, source) or None."""
    settings = get_settings()
    provider = (settings.notam_provider or "simulated").lower().strip()
    url = settings.notam_api_url
    key = settings.notam_api_key
    if provider != "http" or not url or not key:
        return None
    headers = {"Accept": "application/json"}
    params: dict[str, Any] = {"lat": lat, "lon": lon, "radius_deg": radius_deg}
    if settings.notam_api_key_param:
        params[settings.notam_api_key_param] = key
    else:
        headers[settings.notam_api_key_header or "Authorization"] = f"Bearer {key}"
    resp = httpx.get(url, headers=headers, params=params, timeout=settings.http_timeout_s)
    resp.raise_for_status()
    data = resp.json() if resp.text.strip() else []
    if isinstance(data, dict):
        for k in ("notams", "data", "items", "results", "features"):
            if isinstance(data.get(k), list):
                data = data[k]
                break
        else:
            data = [data]
    if not isinstance(data, list):
        data = []
    source = f"http:{urlparse(url).hostname or 'provider'}"
    notams = []
    for i, item in enumerate(data[:25], 1):
        if not isinstance(item, dict):
            notams.append({"id": f"NTM-{i}", "type": "NOTAM", "text": str(item), "source": source})
            continue
        notams.append({
            "id": item.get("id") or item.get("notam_id") or item.get("number") or f"NTM-{i}",
            "type": item.get("type") or "NOTAM",
            "text": item.get("text") or item.get("raw") or item.get("all") or item.get("message") or str(item),
            "effective": item.get("effective") or item.get("start") or item.get("startdate"),
            "expires": item.get("expires") or item.get("end") or item.get("enddate"),
            "source": source,
        })
    if not notams:
        notams = [{
            "id": "NTM-NONE",
            "type": "NOTAM",
            "text": f"No NOTAMs returned by {source} for the queried area (verify with an authoritative briefing).",
            "source": source,
        }]
    return notams, source


def _resolve_notams(lat: float, lon: float, radius_deg: float) -> tuple[list[dict], str, str]:
    """(notams, source, advisory_note). Always truthful; falls back to simulated."""
    try:
        result = _fetch_real_notams(lat, lon, radius_deg)
        if result:
            notams, source = result
            return notams, source, f"NOTAMs fetched from configured provider ({source}). Verify with an authoritative briefing before flight."
    except Exception as exc:
        return (
            _sim_notams(lat, lon, reason=f"real NOTAM fetch failed: {exc}"),
            "simulated",
            "Configured NOTAM provider unavailable; showing SIMULATED NOTAM advisory — verify NOTAMs/TFRs via an authoritative source.",
        )
    return (
        _sim_notams(lat, lon),
        "simulated",
        "NOTAM layer is SIMULATED (no live NOTAM feed configured) — verify NOTAMs/TFRs via an authoritative source before flight.",
    )


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
    """Check METAR conditions near a coordinate (bbox ±radius_deg) + NOTAMs (real if configured)."""
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
            notams, nsource, nadv = _resolve_notams(lat, lon, radius_deg)
            return AirspaceReport(
                status="offline_no_cache",
                station_metar=[],
                notams=notams,
                notam_source=nsource,
                simulated_notams=notams if nsource == "simulated" else [],
                advisory=(
                    "Weather feed unreachable and no cached data. NO real-time airspace picture available. "
                    "DO NOT LAUNCH based on this output — obtain METAR/TAF and NOTAM briefing from an "
                    "authorised source (e.g., aviationweather.gov, 1800wxbrief, or LAANC provider). " + nadv
                ),
                wind_max_kt=None,
                flight_category=None,
                fetched_at=time.time(),
            )

    wind_max_kt, flight_cat = _summarise_metar(metars)
    notams, nsource, nadv = _resolve_notams(lat, lon, radius_deg)
    advisory_parts = []
    if wind_max_kt is not None:
        advisory_parts.append(f"Max observed wind in bbox: {wind_max_kt:.0f} kt.")
    if flight_cat:
        advisory_parts.append(f"Worst flight category observed: {flight_cat}.")
    advisory_parts.append(nadv)
    if source == "offline_cache":
        advisory_parts.append("Serving CACHED weather (feed unreachable); treat with caution.")

    return AirspaceReport(
        status=source,
        station_metar=metars[:10],
        notams=notams,
        notam_source=nsource,
        simulated_notams=notams if nsource == "simulated" else [],
        advisory=" ".join(advisory_parts),
        wind_max_kt=wind_max_kt,
        flight_category=flight_cat,
        fetched_at=time.time(),
    )


def clear_cache() -> None:
    with _lock:
        _cache.clear()
