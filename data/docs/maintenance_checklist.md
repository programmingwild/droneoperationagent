---
title: VX-6 Hexacopter — Maintenance Checklist
doc_type: checklist
regulation: null
source: Internal engineering document — VX-6 maintenance checklist v2.1
accessed: 2026-11-08
---
# VX-6 Hexacopter — Maintenance Checklist

## Pre-flight (every flight)
- [ ] Airframe: no cracks in arms/center plate, landing gear intact, fasteners torqued (M3: 0.6 N·m, M4: 1.2 N·m, M5: 2.0 N·m).
- [ ] Propellers: balanced, nick-free, correct clockwise/counter-clockwise assignment, torque 2.0 N·m.
- [ ] Motors: no vibration play, bearings silent at run-up, housings < 60 °C post-flight.
- [ ] ESCs: firmware matched, telemetry logging, no brownout reboots in the last 5 flights.
- [ ] Battery: cell balance ≤ 0.02 V, no puffing, IR logged, cycle count recorded.
- [ ] Flight controller: IMU/compass calibrated within 90 days, firmware up to date.
- [ ] GPS/GNSS: ≥ 8 satellites, HDOP < 2.0 before arming.
- [ ] Control links: RC, telemetry, and data links verified; failsafe tested within last 30 days.
- [ ] Payload: CG within limits, wiring secured, record media armed.

## 50-hour / 100-flight inspection
- [ ] Replace propellers; torque-check arm bolts; check frame for hairline cracks under magnification.
- [ ] Motor KV and current draw re-measured on a test stand; document in log.
- [ ] ESC temperature rise at hover < 25 °C over ambient.
- [ ] Battery impedance check on all packs; retire packs > 50 % IR growth.
- [ ] Firmware/log audit: verify no unexplained EKF failsafes or GPS glitches.
- [ ] Calibrate vibration: IMU clipping events must be zero at hover.

## 200-hour / 400-flight inspection
- [ ] Motor bearing replacement (or on condition by measured play).
- [ ] ESC replacement if FET RDS(on) drift > 15 %.
- [ ] Full radio-link latency and failsafe timing verification.
- [ ] Structural hardpoint NDI (dye penetrant) on center plate.

## Anomaly thresholds (from flight-log review)
- Battery: hover sag > 4.0 V on a healthy 22 Ah pack; per-cell deviation > 0.15 V under load.
- Vibration: sustained > 15 m/s² RMS on accelerometer; any single IMU clipping event.
- Motor current: any motor deviating > 20 % from the 6-motor mean for > 10 s (propeller/bearing/ESC fault).
- Temperature: motor > 80 °C, ESC > 85 °C, battery > 60 °C — ground until inspected.
- Attitude: uncommanded roll/pitch > 10° at hover indicates CG, motor, or gain issue.

## Corrective actions
Any threshold breach → ground the aircraft, open a maintenance ticket, inspect per the applicable
section, and re-fly only after sign-off by a licensed/qualified technician.
