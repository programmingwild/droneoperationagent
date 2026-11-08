"""Flight-log CSV parser + anomaly scoring for multi-rotor UAS.

Expected CSV columns (header row required):
  t_s, voltage_v, total_current_a,
  m1_a .. m6_a, vibration_ms2,
  m1_rpm .. m6_rpm, m1_temp_c .. m6_temp_c, alt_m

Scoring (0–100, higher = healthier is NOT used; instead anomaly_score 0–100, higher = worse):
  - current imbalance > 20% of the 6-motor mean  → up to 35 pts
  - vibration above 15 m/s²                       → up to 25 pts
  - late-flight voltage sag > 4 V vs fresh-pack   → up to 25 pts
  - any motor temp > 80 °C                        → up to 15 pts
Verdicts: < 20 PASS · 20–49 MONITOR · >= 50 GROUND (do not fly until inspected)
"""
import csv
import math
from dataclasses import dataclass, field
from pathlib import Path

REQUIRED_COLUMNS = [
    "t_s", "voltage_v", "total_current_a",
    "m1_a", "m2_a", "m3_a", "m4_a", "m5_a", "m6_a",
    "vibration_ms2",
    "m1_rpm", "m2_rpm", "m3_rpm", "m4_rpm", "m5_rpm", "m6_rpm",
    "m1_temp_c", "m2_temp_c", "m3_temp_c", "m4_temp_c", "m5_temp_c", "m6_temp_c",
    "alt_m",
]
MOTOR_CURRENTS = [f"m{i}_a" for i in range(1, 7)]
MOTOR_TEMPS = [f"m{i}_temp_c" for i in range(1, 7)]

VIBRATION_LIMIT = 15.0
CURRENT_IMBALANCE_LIMIT = 0.20
MOTOR_TEMP_LIMIT = 80.0


@dataclass
class Anomaly:
    type: str
    severity: str  # CRITICAL | HIGH | MEDIUM | LOW
    description: str
    evidence: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"type": self.type, "severity": self.severity,
                "description": self.description, "evidence": self.evidence}


@dataclass
class LogAnalysis:
    rows: int
    duration_s: float
    motor_current_mean: list[float]
    motor_current_imbalance_pct: list[float]
    max_vibration_ms2: float
    vibration_rms_ms2: float
    voltage_min_v: float
    voltage_sag_v: float
    motor_temp_max_c: float
    anomalies: list[Anomaly]
    anomaly_score: int
    verdict: str  # PASS | MONITOR | GROUND

    def to_dict(self) -> dict:
        return {
            "rows": self.rows,
            "duration_s": self.duration_s,
            "motor_current_mean": self.motor_current_mean,
            "motor_current_imbalance_pct": self.motor_current_imbalance_pct,
            "max_vibration_ms2": self.max_vibration_ms2,
            "vibration_rms_ms2": self.vibration_rms_ms2,
            "voltage_min_v": self.voltage_min_v,
            "voltage_sag_v": self.voltage_sag_v,
            "motor_temp_max_c": self.motor_temp_max_c,
            "anomalies": [a.to_dict() for a in self.anomalies],
            "anomaly_score": self.anomaly_score,
            "verdict": self.verdict,
        }


def parse_flight_log(path: str | Path) -> LogAnalysis:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"flight log not found: {path}")
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        missing = [c for c in REQUIRED_COLUMNS if c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"flight log missing required columns: {missing}")
        rows = list(reader)
    if not rows:
        raise ValueError("flight log has no data rows")

    t = [float(r["t_s"]) for r in rows]
    volts = [float(r["voltage_v"]) for r in rows]
    vib = [float(r["vibration_ms2"]) for r in rows]
    currents = [[float(r[c]) for c in MOTOR_CURRENTS] for r in rows]
    temps = [[float(r[c]) for c in MOTOR_TEMPS] for r in rows]

    n = len(rows)
    motor_mean = [sum(row[i] for row in currents) / n for i in range(6)]
    overall_mean = sum(motor_mean) / 6.0
    imbalance_pct = [round(100.0 * (m - overall_mean) / overall_mean, 1) for m in motor_mean]

    max_dev_pct = max(abs(p) for p in imbalance_pct)
    sustain_rows = sum(
        1 for row in currents
        if max(abs((c - (sum(row) / 6.0)) / (sum(row) / 6.0)) for c in row) > CURRENT_IMBALANCE_LIMIT
    )
    sample_hz = (n - 1) / max(t[-1] - t[0], 1e-9)
    sustain_s = sustain_rows / sample_hz if sample_hz > 0 else 0.0

    vib_max = max(vib)
    vib_rms = math.sqrt(sum(v * v for v in vib) / n)
    time_over_vib_s = sum(1 for v in vib if v > VIBRATION_LIMIT) / sample_hz

    fresh_v = sum(volts[: min(10, n)]) / min(10, n)
    volts_min = min(volts)
    sag = fresh_v - volts_min

    temp_max = max(max(row) for row in temps)
    per_motor_max = [max(row[i] for row in temps) for i in range(6)]
    hot_motor = per_motor_max.index(temp_max) + 1

    anomalies: list[Anomaly] = []
    score = 0

    if max_dev_pct > 20.0:
        dev_motor = max(range(6), key=lambda i: abs(imbalance_pct[i])) + 1
        sev = "HIGH" if sustain_s > 10 else "MEDIUM"
        anomalies.append(Anomaly(
            type="MOTOR_CURRENT_IMBALANCE",
            severity=sev,
            description=(
                f"Motor {dev_motor} deviates {abs(imbalance_pct[dev_motor - 1]):.1f}% from the 6-motor mean "
                f"for ≈{sustain_s:.0f}s (limit 20% / 10 s). Propeller, bearing or ESC fault likely."
            ),
            evidence={"motor": dev_motor, "imbalance_pct": imbalance_pct,
                      "sustained_s": round(sustain_s, 1)},
        ))
        score += 35 if sev == "HIGH" else 20

    if vib_max > VIBRATION_LIMIT:
        anomalies.append(Anomaly(
            type="VIBRATION_EXCESSIVE",
            severity="HIGH" if time_over_vib_s > 10 else "MEDIUM",
            description=(
                f"Vibration peaked at {vib_max:.1f} m/s² (limit {VIBRATION_LIMIT}); "
                f"{time_over_vib_s:.0f}s above limit; RMS {vib_rms:.1f} m/s²."
            ),
            evidence={"max_ms2": round(vib_max, 2), "rms_ms2": round(vib_rms, 2),
                      "seconds_over": round(time_over_vib_s, 1)},
        ))
        score += 25

    if sag > 4.0:
        anomalies.append(Anomaly(
            type="BATTERY_VOLTAGE_SAG",
            severity="HIGH",
            description=(
                f"Pack voltage sagged {sag:.1f} V from fresh baseline {fresh_v:.1f} V to "
                f"{volts_min:.1f} V (healthy limit ≈ 4.0 V). Check internal resistance."
            ),
            evidence={"baseline_v": round(fresh_v, 2), "min_v": round(volts_min, 2),
                      "sag_v": round(sag, 2)},
        ))
        score += 25

    if temp_max > MOTOR_TEMP_LIMIT:
        anomalies.append(Anomaly(
            type="MOTOR_OVERHEAT",
            severity="HIGH",
            description=f"Motor {hot_motor} reached {temp_max:.1f} °C (limit {MOTOR_TEMP_LIMIT} °C).",
            evidence={"motor": hot_motor, "max_c": round(temp_max, 1)},
        ))
        score += 15

    score = min(100, score)
    verdict = "PASS" if score < 20 else ("MONITOR" if score < 50 else "GROUND")

    return LogAnalysis(
        rows=n,
        duration_s=round(t[-1] - t[0], 1),
        motor_current_mean=[round(m, 2) for m in motor_mean],
        motor_current_imbalance_pct=imbalance_pct,
        max_vibration_ms2=round(vib_max, 2),
        vibration_rms_ms2=round(vib_rms, 2),
        voltage_min_v=round(volts_min, 2),
        voltage_sag_v=round(sag, 2),
        motor_temp_max_c=round(temp_max, 1),
        anomalies=anomalies,
        anomaly_score=score,
        verdict=verdict,
    )
