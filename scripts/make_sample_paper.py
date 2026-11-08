"""Generate data/docs/pdf/hexacopter_uav_design_paper.pdf — a sample research paper PDF.

The real user-supplied paper can simply be dropped into data/docs/pdf/ and re-ingested;
this sample keeps the end-to-end PDF path demoable out of the box.
"""
import sys
from pathlib import Path

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas
except ImportError:
    sys.exit("reportlab not installed")

SECTIONS = [
    ("1. Abstract", [
        "This paper presents the design, analysis and flight validation of a six-rotor unmanned",
        "aerial vehicle (UAV) for infrastructure inspection. The airframe achieves a maximum takeoff",
        "mass of 8.5 kg with a 1.5 kg payload and 18 minutes of endurance on a 12S 22 Ah Li-ion",
        "battery. A companion finite-element study of the carbon-fibre center plate and folding",
        "propeller hubs is reported, together with tethered thrust-stand characterisation of the",
        "power system and open-loop and closed-loop flight trials.",
    ]),
    ("2. Airframe and Structural Design", [
        "The hexacopter uses a 680 mm wheelbase carbon-fibre tube frame with a 4 mm CFRP center",
        "plate, 10 mm arms clamped to arm-root blocks, and a magnesium motor mount. The center",
        "plate was optimised to carry a 1.5 g per g limit-load factor at takeoff with a 25% margin.",
        "Finite-element analysis at 1.25x design load predicted a peak stress of 190 MPa at the",
        "arm-root fillet, below the 3.2 GPa compressive strength of T300 fabric with 0.4 knock-down.",
        "Propeller hubs were analysed for a worst-case 1,000 g tip-over impact; the retained folding",
        "mechanism maintained geometry within 0.5 mm.",
    ]),
    ("3. Power System Sizing", [
        "Hover power for the 8.5 kg (83.4 N) aircraft with 6 rotors of 18-inch diameter was",
        "predicted at 1.62 kW; measured hover current on a fresh 12S 22 Ah pack was 38 A at 44.2 V",
        "(1.68 kW). Full-throttle static thrust measured 21 kgf total, giving a thrust-to-weight ratio",
        "of 2.5 at takeoff. C-rate at hover was 1.7C and at maximum throttle 6.4C. Voltage sag of",
        "2.2 V was measured at hover on new packs; packs with greater than 4 V sag were flagged for",
        "internal-resistance growth and retired from operations.",
    ]),
    ("4. Flight Controller and Estimation", [
        "A Cube Orange+ autopilot with Here4 GNSS ran an extended Kalman filter fusing",
        "accelerometer, gyroscope, magnetometer and dual GNSS receivers. Position-hold drift over",
        "10 minutes was 0.8 m RMS, well within inspection tolerances. Failsafe behaviour (loss of",
        "RC link triggering RTL within 2 s, loss of GNSS triggering attitude-hold land) was verified",
        "in 40 tethered test flights.",
    ]),
    ("5. Flight Test Results", [
        "Twenty-two flights (total 6.1 h) were flown at an indoor gymnasium and a rural test site.",
        "Endurance averaged 18.4 minutes at 7.8 kg AUW with 20% reserve landing voltage of 3.7",
        "V/cell. Vibration at the IMU averaged 6.1 m/s^2 RMS; two flights exceeded the 15 m/s^2",
        "abort threshold due to propeller imbalance and were landed under pilot command. A single",
        "motor-current deviation of 38% from the 6-motor mean was logged in flight 17; post-flight",
        "inspection found a nicked propeller. No airframe defects were found.",
    ]),
    ("6. Conclusions and Future Work", [
        "The VX-6 hexacopter met its design goals: 18-minute endurance, IP43 splash resistance, and",
        "a 1.5 kg payload with full autonomous RTL failsafes. Future work includes dual-redundant",
        "power distribution, direct-drive motors to reduce vibration, and structured HITL evaluation",
        "for BVLOS waiver applications.",
    ]),
]


def main() -> None:
    out = Path(__file__).resolve().parents[1] / "data" / "docs" / "pdf" / "hexacopter_uav_design_paper.pdf"
    out.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(out), pagesize=A4)
    width, height = A4
    c.setFont("Helvetica-Bold", 16)
    c.drawString(20 * mm, height - 25 * mm, "Design and Flight Validation of the VX-6 Hexacopter UAV")
    c.setFont("Helvetica", 10)
    c.drawString(20 * mm, height - 33 * mm, "Sample research paper — generated for the Drone Ops Agent training corpus")
    y = height - 45 * mm
    for title, paragraphs in SECTIONS:
        c.setFont("Helvetica-Bold", 12)
        c.drawString(20 * mm, y, title)
        y -= 7 * mm
        c.setFont("Helvetica", 10)
        for p in paragraphs:
            c.drawString(22 * mm, y, p)
            y -= 5.2 * mm
            if y < 20 * mm:
                c.showPage()
                y = height - 20 * mm
                c.setFont("Helvetica", 10)
        y -= 4 * mm
    c.save()
    print("wrote", out)


if __name__ == "__main__":
    main()
