---
title: VX-6 Hexacopter — Flight Manual (illustrative, for training corpus)
doc_type: manual
regulation: null
source: Internal engineering document — VX-6 hexacopter flight manual v1.4
accessed: 2026-11-08
---
# VX-6 Hexacopter — Flight Manual (condensed)

Illustrative condensed manual for the six-rotor VX-6 UAV (MTOM 8.5 kg, payload 1.5 kg). This document
is part of the training corpus, not a substitute for the manufacturer manual.

## Aircraft specifications
MTOM 8.5 kg. Frame wheelbase 680 mm. Motors 6×, brushless 6215 KV350. Propellers 6× 18-inch carbon
folding. ESC 6× 40A BLHeli_32. Battery 12S Li-ion 22 Ah, 88.8 V nominal. Flight controller: Cube
Orange+ with Here4 GNSS. Flight time 18 min nominal, 22 min best case, 12 min at max takeoff weight
with 20% reserve.

## Operating envelope
- Max wind: 12 m/s steady, gusts to 15 m/s abort criterion.
- Max operating temperature: 40 °C. Minimum −10 °C with reduced endurance.
- Rain: do not operate in precipitation unless the airframe is rain-rated (IP43 or better).
- Max takeoff altitude density altitude: 3,000 m. Above 2,000 m, derate payload by 10% per 1,000 m.

## Power system and C-rate
Nominal full pack 50.4 V (12S Li-ion, 4.2 V/cell). Empty 36.0 V (3.0 V/cell cutoff, do not discharge
below 40.8 V under load in normal operations). Full-throttle current draw ≈ 140 A (~6.4 C on 22 Ah).
Hover current ≈ 38 A (1.7 C). Voltage sag at hover ≈ 2.2 V with fresh pack; > 4 V sag at hover on a
22 Ah pack indicates elevated internal resistance — investigate before flight.

## Pre-flight checks (aircraft)
1. Propellers: no cracks, correct tightening torque (2.0 ± 0.2 N·m), correct rotation direction.
2. ESC/motor wiring: bullet connectors seated, no chafe.
3. Battery: voltage per cell within 0.02 V balance; no swelling; capacity logged in the battery
   manager.
4. Flight controller: IMU calibrated, green AHRS, GPS lock ≥ 8 sats, HDOP < 2.0.
5. Control links: RC link, telemetry link, and (if fitted) video link all nominal at 100 m range test.
6. Failsafes: RC loss → return-to-launch within 2 s; GNSS loss → attitude mode with land.
7. Payload: secured, CG within ±20 mm longitudinal of the design datum.

## Flight modes
Altitude hold, Position (GNSS) hold, Return-to-Launch (RTL), Loiter, Auto mission. VX-6 is NOT
automatically failsafe-armed for beyond-visual-line-of-sight (BVLOS); BVLOS requires a waiver
(FAA § 107.200), EASA specific-category authorization, or DGCA authorization as applicable.

## Abort/RTL criteria
Return to launch immediately if: wind gusts > 15 m/s, voltage sag below 3.5 V/cell under hover load,
vibration levels exceed 15 m/s² sustained, any motor current deviation > 20% from mean, or battery
temp > 60 °C.

## Battery handling
Charge at ≤ 1C (22 A) until balance, store at 3.80 V/cell ± 0.05 V. Discard after 500 cycles or when
internal resistance rises > 50% above new. Never charge a puffed pack; isolate and dispose per local
li-ion rules.
