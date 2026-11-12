"""FAA TFR provider (key-free, official FAA feed) — mocked; no network required."""
from types import SimpleNamespace

import backend.app.tools.notam as notam_mod

_SAMPLE = [
    {"notam_id": "6/7001", "type": "UAS PUBLIC GATHERING", "facility": "ZJX", "state": "FL",
     "description": "Orlando, FL, Nov 14-16", "creation_date": "11/09/2026"},
    {"notam_id": "6/7002", "type": "SECURITY", "facility": "ZDC", "state": "NC",
     "description": "NEW BERN, NC", "creation_date": "11/10/2026"},
    {"notam_id": "6/7003", "type": "HAZARDS", "facility": "ZDV", "state": "WY",
     "description": "27NM NE NEWCASTLE, WY", "creation_date": "11/11/2026"},
    {"notam_id": "6/7004", "type": "SPACE OPERATIONS", "facility": "ZHU", "state": "TX",
     "description": "STARBASE, TX", "creation_date": "11/11/2026"},
]


def _settings(**kw):
    base = dict(
        notam_cache_ttl_s=900,
        http_timeout_s=8.0,
        aviationweather_base_url="https://aviationweather.gov/api/data",
        notam_provider="faa_tfr",
        notam_api_url=None,
        notam_api_key=None,
        notam_api_key_header="Authorization",
        notam_api_key_param=None,
    )
    base.update(kw)
    return SimpleNamespace(**base)


def test_faa_tfr_maps_live_feed(monkeypatch):
    notam_mod.clear_cache()

    def fake_get(url, *a, **kw):
        class R:
            status_code = 200
            text = "[]"

            def raise_for_status(self):
                pass

            def json(self):
                if "aviationweather" in url:
                    return [{"wspd": 5, "fltcat": "VFR", "icaoId": "TEST"}]
                return list(_SAMPLE)

        return R()

    monkeypatch.setattr(notam_mod, "get_settings", lambda: _settings())
    monkeypatch.setattr(notam_mod.httpx, "get", fake_get)

    report = notam_mod.check_airspace(28.6, -81.2)
    assert report.notam_source == "faa_tfr"
    assert report.simulated_notams == []
    ids = [n["id"] for n in report.notams]
    assert "6/7001" in ids  # UAS TFR surfaced
    assert any(n["id"] == "FAA-TFR-SUMMARY" for n in report.notams)
    assert "SIMULATED" not in report.advisory


def test_faa_tfr_failure_falls_back_to_simulated(monkeypatch):
    notam_mod.clear_cache()

    def fake_get(url, *a, **kw):
        class R:
            status_code = 200
            text = "[]"

            def raise_for_status(self):
                if "tfrapi" in url:
                    raise RuntimeError("faa down")

            def json(self):
                return [{"wspd": 5, "fltcat": "VFR", "icaoId": "TEST"}] if "aviationweather" in url else []

        return R()

    monkeypatch.setattr(notam_mod, "get_settings", lambda: _settings())
    monkeypatch.setattr(notam_mod.httpx, "get", fake_get)

    report = notam_mod.check_airspace(28.6, -81.2)
    assert report.notam_source == "simulated"
    assert "SIMULATED" in report.advisory


def test_faa_tfr_not_routed_when_provider_simulated(monkeypatch):
    notam_mod.clear_cache()
    called = []

    def fake_get(url, *a, **kw):
        called.append(url)

        class R:
            status_code = 200
            text = "[]"

            def raise_for_status(self):
                pass

            def json(self):
                return [{"wspd": 5, "fltcat": "VFR", "icaoId": "TEST"}]

        return R()

    monkeypatch.setattr(notam_mod, "get_settings", lambda: _settings(notam_provider="simulated"))
    monkeypatch.setattr(notam_mod.httpx, "get", fake_get)

    report = notam_mod.check_airspace(28.6, -81.2)
    assert report.notam_source == "simulated"
    assert not any("tfrapi" in u for u in called)
