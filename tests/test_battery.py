import pytest

from backend.app.tools.battery import BatteryInput, estimate_battery_range


def test_default_vx6_pack_is_go():
    est = estimate_battery_range(BatteryInput())
    assert est.verdict == "GO"
    assert 15.0 < est.endurance_min < 30.0  # VX-6 manual: ~18 min best case, 12 min max AUW
    assert est.range_km > 8.0
    assert est.reserve_fraction == pytest.approx(0.20)
    assert est.hover_c_rate == pytest.approx(38.0 / 22.0, abs=0.01)


def test_headwind_reduces_groundspeed_and_range():
    calm = estimate_battery_range(BatteryInput(headwind_kmh=0.0))
    windy = estimate_battery_range(BatteryInput(headwind_kmh=30.0))
    assert windy.groundspeed_kmh < calm.groundspeed_kmh
    assert windy.range_km < calm.range_km
    assert any("Headwind" in w for w in windy.warnings) or windy.verdict in ("MARGINAL", "NO-GO")


def test_gusts_above_abort_limit_trigger_nogo():
    est = estimate_battery_range(BatteryInput(gust_ms=16.0))
    assert est.verdict == "NO-GO"
    assert any("gust" in w.lower() for w in est.warnings)


def test_low_reserve_warns():
    est = estimate_battery_range(BatteryInput(reserve_fraction=0.10))
    assert any("reserve" in w.lower() for w in est.warnings)
    assert est.verdict == "MARGINAL"


def test_high_sag_warns():
    est = estimate_battery_range(BatteryInput(pack_resistance_mohm=120.0))
    assert est.hover_voltage_sag_v > 4.0
    assert est.verdict == "MARGINAL"


def test_invalid_current_ordering_rejected():
    with pytest.raises(Exception):
        BatteryInput(hover_current_a=100.0, full_throttle_current_a=50.0)
