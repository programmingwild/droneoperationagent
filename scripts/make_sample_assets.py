"""Generate data/sample_logs/flight_log_sample.csv with injected anomalies.

Deterministic (seeded) so the demo and tests are reproducible. Injected faults:
  - Motor 3 current drifts ~45% high mid-flight (bearing/propeller fault signature)
  - Vibration ramps above the 15 m/s^2 threshold in the last third
  - Voltage sag deeper than healthy baseline in the final minutes
"""
import csv
import math
import random
from pathlib import Path

random.seed(42)

rows = []
t = 0.0
for i in range(240):
    t = i * 0.5  # 2 Hz sampling, 120 s flight
    hover = 38.0 + 2.0 * math.sin(i / 12.0)
    motor_currents = [hover / 6 * random.uniform(0.94, 1.06) for _ in range(6)]
    if 80 <= i < 210:
        motor_currents[2] *= 1.55 + 0.05 * random.uniform(-1, 1)  # motor 3 (index 2), sustained fault
    voltage = 48.5 - i * 0.022 - (2.2 if i < 150 else 3.6) + random.uniform(-0.15, 0.15)
    vibration = 6.0 + random.uniform(-1.0, 1.0) + (max(0.0, (i - 140) * 0.13))
    rpm = [5200 + random.uniform(-60, 60) for _ in range(6)]
    rpm[2] = int(rpm[2] * (1.18 if 80 <= i < 210 else 1.0))
    motor_temps = [45 + i * 0.03 + random.uniform(-0.5, 0.5) for _ in range(6)]
    motor_temps[2] = 45 + i * 0.09
    rows.append(
        [
            round(t, 1),
            round(voltage, 2),
            round(sum(motor_currents), 2),
            *[round(c, 2) for c in motor_currents],
            round(vibration, 2),
            *rpm,
            *[round(x, 1) for x in motor_temps],
            round(1650 + 2.0 * math.sin(i / 20) + random.uniform(-0.4, 0.4), 2),  # baro alt m
        ]
    )

header = [
    "t_s", "voltage_v", "total_current_a",
    "m1_a", "m2_a", "m3_a", "m4_a", "m5_a", "m6_a",
    "vibration_ms2",
    "m1_rpm", "m2_rpm", "m3_rpm", "m4_rpm", "m5_rpm", "m6_rpm",
    "m1_temp_c", "m2_temp_c", "m3_temp_c", "m4_temp_c", "m5_temp_c", "m6_temp_c",
    "alt_m",
]

out = Path(__file__).resolve().parents[1] / "data" / "sample_logs" / "flight_log_sample.csv"
out.parent.mkdir(parents=True, exist_ok=True)
with out.open("w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(header)
    w.writerows(rows)
print("wrote", out, len(rows), "rows")
