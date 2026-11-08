import csv

import pytest

from backend.app.tools.flight_logs import parse_flight_log


def test_sample_log_flags_motor3_and_grounds(sample_log_path):
    analysis = parse_flight_log(sample_log_path)
    assert analysis.rows == 240
    assert abs(analysis.motor_current_imbalance_pct[2]) > 20.0  # motor 3 injected fault
    assert analysis.max_vibration_ms2 > 15.0
    assert analysis.anomaly_score >= 50
    assert analysis.verdict == "GROUND"
    types = {a.type for a in analysis.anomalies}
    assert "MOTOR_CURRENT_IMBALANCE" in types
    assert "VIBRATION_EXCESSIVE" in types


def test_clean_log_passes(tmp_path):
    header = ["t_s", "voltage_v", "total_current_a",
              "m1_a", "m2_a", "m3_a", "m4_a", "m5_a", "m6_a",
              "vibration_ms2",
              "m1_rpm", "m2_rpm", "m3_rpm", "m4_rpm", "m5_rpm", "m6_rpm",
              "m1_temp_c", "m2_temp_c", "m3_temp_c", "m4_temp_c", "m5_temp_c", "m6_temp_c",
              "alt_m"]
    rows = []
    for i in range(120):
        rows.append([i * 0.5, 48.0 - i * 0.005, 38.0,
                     6.3, 6.3, 6.4, 6.3, 6.3, 6.4,
                     6.0,
                     5200, 5200, 5210, 5200, 5200, 5210,
                     45.0, 45.0, 45.1, 45.0, 45.0, 45.1,
                     1650.0])
    path = tmp_path / "clean.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    analysis = parse_flight_log(path)
    assert analysis.verdict == "PASS"
    assert analysis.anomaly_score < 20
    assert analysis.anomalies == []


def test_missing_file_raises(sample_log_path, tmp_path):
    with pytest.raises(FileNotFoundError):
        parse_flight_log(tmp_path / "nope.csv")


def test_missing_columns_raise(tmp_path):
    path = tmp_path / "bad.csv"
    path.write_text("t_s,voltage_v\n0,48.0\n", encoding="utf-8")
    with pytest.raises(ValueError):
        parse_flight_log(path)
