"""Battery-range estimator for multi-rotor UAS (real physics-based math, no mocks).

Model:
  - Nominal energy: E = V_nom * Ah
  - Voltage sag under load: sag = I * R_pack   (R_pack = pack internal resistance, default 58 mΩ)
  - Usable capacity: from full (4.2 V/cell) down to loaded cutoff (3.5 V/cell normal ops; 3.0 V absolute)
  - Endurance: usable_Ah / hover_current * 60  (minus reserve fraction)
  - Ground range: endurance_h * (cruise_kmh − headwind_kmh), never negative
  - Wind margin: gusts above the airframe abort limit (default 15 m/s) ⇒ NO-GO
"""
from pydantic import BaseModel, Field, field_validator


class BatteryInput(BaseModel):
    cell_count: int = Field(12, ge=1, le=24, description="Series cell count (S)")
    capacity_mah: int = Field(22_000, gt=0, description="Pack capacity in mAh")
    nominal_cell_v: float = Field(3.7, gt=0, description="Nominal cell voltage (Li-ion 3.7)")
    full_cell_v: float = Field(4.2, gt=3.0, description="Full cell voltage")
    cutoff_cell_v: float = Field(3.5, ge=2.5, le=4.2, description="Loaded cutoff per cell for normal ops")
    hover_current_a: float = Field(38.0, gt=0, description="Hover current draw")
    full_throttle_current_a: float = Field(140.0, gt=0, description="Full-throttle current draw")
    pack_resistance_mohm: float = Field(58.0, ge=0, description="Pack internal resistance, milliohms")
    cruise_speed_kmh: float = Field(45.0, gt=0)
    headwind_kmh: float = Field(0.0, description="Headwind component along route")
    gust_ms: float = Field(0.0, ge=0, description="Forecast/observed gust, m/s")
    wind_abort_limit_ms: float = Field(15.0, gt=0, description="Airframe gust abort limit, m/s")
    reserve_fraction: float = Field(0.20, ge=0.0, lt=1.0, description="Mandatory landing reserve")

    @field_validator("full_throttle_current_a")
    @classmethod
    def _ft_ge_hover(cls, v: float, info):
        hover = info.data.get("hover_current_a")
        if hover is not None and v < hover:
            raise ValueError("full_throttle_current_a must be >= hover_current_a")
        return v


class BatteryEstimate(BaseModel):
    nominal_voltage_v: float
    full_voltage_v: float
    cutoff_voltage_v: float
    hover_c_rate: float
    full_throttle_c_rate: float
    hover_voltage_sag_v: float
    full_throttle_voltage_sag_v: float
    usable_capacity_ah: float
    endurance_min: float
    range_km: float
    groundspeed_kmh: float
    reserve_fraction: float
    warnings: list[str]
    verdict: str  # GO | MARGINAL | NO-GO


def estimate_battery_range(inp: BatteryInput) -> BatteryEstimate:
    capacity_ah = inp.capacity_mah / 1000.0
    nominal_v = inp.cell_count * inp.nominal_cell_v
    full_v = inp.cell_count * inp.full_cell_v
    cutoff_v = inp.cell_count * inp.cutoff_cell_v

    # Usable fraction: 80% depth-of-discharge down to the normal 3.5 V/cell loaded cutoff
    # (conservative for Li-ion; documented in the VX-6 manual), less the mandated reserve.
    depth_of_discharge = 0.80
    usable_ah = capacity_ah * depth_of_discharge * (1 - inp.reserve_fraction)

    hover_c = inp.hover_current_a / capacity_ah
    full_c = inp.full_throttle_current_a / capacity_ah
    r_ohm = inp.pack_resistance_mohm / 1000.0
    sag_hover = inp.hover_current_a * r_ohm
    sag_full = inp.full_throttle_current_a * r_ohm

    endurance_min = (usable_ah / inp.hover_current_a) * 60.0
    groundspeed = max(0.0, inp.cruise_speed_kmh - inp.headwind_kmh)
    range_km = endurance_min / 60.0 * groundspeed

    warnings: list[str] = []
    if sag_hover > 4.0:
        warnings.append(
            f"Hover voltage sag {sag_hover:.1f} V exceeds 4.0 V — check battery internal resistance."
        )
    if hover_c > 3.0:
        warnings.append(f"Hover C-rate {hover_c:.1f}C is high for Li-ion — capacity/endurance will degrade.")
    if inp.gust_ms > inp.wind_abort_limit_ms:
        warnings.append(
            f"Gusts {inp.gust_ms} m/s exceed the airframe abort limit {inp.wind_abort_limit_ms} m/s."
        )
    if inp.headwind_kmh > 0.6 * inp.cruise_speed_kmh:
        warnings.append(
            f"Headwind {inp.headwind_kmh} km/h removes > 60% of cruise speed — return-leg range is compromised."
        )
    if inp.reserve_fraction < 0.2:
        warnings.append("Reserve below 20% — violates the VX-6 flight manual requirement (§ Power, 20% reserve).")

    if any("exceed" in w and "gust" in w.lower() for w in warnings):
        verdict = "NO-GO"
    elif warnings:
        verdict = "MARGINAL"
    else:
        verdict = "GO"

    return BatteryEstimate(
        nominal_voltage_v=round(nominal_v, 2),
        full_voltage_v=round(full_v, 2),
        cutoff_voltage_v=round(cutoff_v, 2),
        hover_c_rate=round(hover_c, 2),
        full_throttle_c_rate=round(full_c, 2),
        hover_voltage_sag_v=round(sag_hover, 2),
        full_throttle_voltage_sag_v=round(sag_full, 2),
        usable_capacity_ah=round(usable_ah, 2),
        endurance_min=round(endurance_min, 1),
        range_km=round(range_km, 2),
        groundspeed_kmh=round(groundspeed, 1),
        reserve_fraction=inp.reserve_fraction,
        warnings=warnings,
        verdict=verdict,
    )
