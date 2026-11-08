from backend.app.tools.flight_logs import parse_flight_log
from backend.app.tools.report import export_ticket_pdf
from backend.app.tools.ticket import (
    create_ticket,
    create_ticket_from_analysis,
    get_ticket,
    list_tickets,
)


def test_create_and_fetch_ticket():
    t = create_ticket("Test ticket", "HIGH", [{"type": "X", "severity": "HIGH",
                                               "description": "d", "evidence": {"a": 1}}],
                      "Inspect before flight", log_file="x.csv")
    assert t["id"].startswith("MT-")
    fetched = get_ticket(t["id"])
    assert fetched["severity"] == "HIGH"
    assert fetched["findings"][0]["evidence"] == {"a": 1}
    assert t["id"] in [x["id"] for x in list_tickets(limit=5)]


def test_ticket_from_analysis(sample_log_path):
    analysis = parse_flight_log(sample_log_path)
    t = create_ticket_from_analysis(analysis, log_file=str(sample_log_path))
    assert t["severity"] in ("HIGH", "CRITICAL")
    assert t["source"] == "flight_log_analysis"
    assert t["findings"]


def test_export_report_pdf(sample_log_path):
    analysis = parse_flight_log(sample_log_path)
    t = create_ticket_from_analysis(analysis, log_file=str(sample_log_path))
    pdf = export_ticket_pdf(t["id"])
    assert pdf.exists()
    assert pdf.read_bytes().startswith(b"%PDF")


def test_unknown_ticket_pdf():
    try:
        export_ticket_pdf("MT-DOESNOTEXIST")
        assert False, "expected ValueError"
    except ValueError:
        pass
