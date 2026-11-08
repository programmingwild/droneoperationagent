"""Real (keyed HTTP) NOTAM provider wiring — mocked; no network/keys required."""
from types import SimpleNamespace

import backend.app.tools.notam as notam_mod


def _settings(**kw):
    base = dict(
        notam_cache_ttl_s=900,
        http_timeout_s=8.0,
        aviationweather_base_url="https://aviationweather.gov/api/data",
        notam_provider="http",
        notam_api_url="https://notam.example.test/v1/search",
        notam_api_key="secret-key",
        notam_api_key_header="Authorization",
        notam_api_key_param=None,
    )
    base.update(kw)
    return SimpleNamespace(**base)


def test_real_notam_provider_maps_response(monkeypatch):
    notam_mod.clear_cache()

    def fake_get(url, *a, **kw):
        class R:
            status_code = 200
            text = "{}"
            def raise_for_status(self): pass
            def json(self):
                if "aviationweather" in url:
                    return [{"wspd": 5, "fltcat": "VFR", "icaoId": "TEST"}]
                # NOTAM provider
                assert kw["headers"].get("Authorization") == "Bearer secret-key"
                return {"notams": [{"id": "N1", "text": "TFR active", "type": "TFR"}]}
        return R()

    monkeypatch.setattr(notam_mod, "get_settings", lambda: _settings())
    monkeypatch.setattr(notam_mod.httpx, "get", fake_get)

    report = notam_mod.check_airspace(10.0, 20.0)
    assert report.notam_source == "http:notam.example.test"
    assert report.notams[0]["id"] == "N1"
    assert "TFR active" in report.notams[0]["text"]
    assert report.simulated_notams == []
    assert "SIMULATED" not in report.advisory


def test_real_notam_failure_falls_back_to_simulated(monkeypatch):
    notam_mod.clear_cache()

    def fake_get(url, *a, **kw):
        class R:
            status_code = 200
            text = "[]"
            def raise_for_status(self):
                if "aviationweather" not in url:
                    raise RuntimeError("provider down")
            def json(self): return []
        return R()

    monkeypatch.setattr(notam_mod, "get_settings", lambda: _settings())
    monkeypatch.setattr(notam_mod.httpx, "get", fake_get)

    report = notam_mod.check_airspace(10.0, 20.0)
    assert report.notam_source == "simulated"
    assert report.simulated_notams[0]["type"] == "SIMULATED"
    assert "SIMULATED" in report.advisory
