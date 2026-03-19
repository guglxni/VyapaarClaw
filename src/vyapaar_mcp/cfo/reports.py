"""PDF Compliance Report Generation.

Auto-generates financial governance reports with charts and tables.
Uses FPDF2 for lightweight PDF generation — no external services needed.
"""

from __future__ import annotations

import datetime as _dt
import io
import os
from typing import Any

from fpdf import FPDF


class ComplianceReport(FPDF):
    """Custom PDF report with VyapaarClaw branding."""

    def __init__(self) -> None:
        super().__init__()
        self.set_auto_page_break(auto=True, margin=25)

    def header(self) -> None:
        self.set_font("Helvetica", "B", 14)
        self.set_text_color(31, 41, 55)
        self.cell(0, 10, "VyapaarClaw — Financial Governance Report", align="C", new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "", 9)
        self.set_text_color(107, 114, 128)
        self.cell(0, 6, f"Generated: {_dt.datetime.now().strftime('%Y-%m-%d %H:%M UTC')}", align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(5)
        # Divider line
        self.set_draw_color(79, 70, 229)
        self.set_line_width(0.8)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(8)

    def footer(self) -> None:
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(156, 163, 175)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}} | VyapaarClaw AI CFO", align="C")

    def section_title(self, title: str) -> None:
        self.set_font("Helvetica", "B", 12)
        self.set_text_color(31, 41, 55)
        self.cell(0, 10, title, new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def key_value(self, key: str, value: str) -> None:
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(55, 65, 81)
        self.cell(60, 7, key)
        self.set_font("Helvetica", "", 10)
        self.set_text_color(31, 41, 55)
        self.cell(0, 7, str(value), new_x="LMARGIN", new_y="NEXT")

    def add_table(self, headers: list[str], rows: list[list[str]], col_widths: list[int] | None = None) -> None:
        widths = col_widths or [int(190 / len(headers))] * len(headers)

        # Header row
        self.set_font("Helvetica", "B", 9)
        self.set_fill_color(243, 244, 246)
        self.set_text_color(55, 65, 81)
        for i, header in enumerate(headers):
            self.cell(widths[i], 8, header, border=1, fill=True)
        self.ln()

        # Data rows
        self.set_font("Helvetica", "", 9)
        self.set_text_color(31, 41, 55)
        for row in rows:
            for i, cell in enumerate(row):
                self.cell(widths[i], 7, str(cell)[:30], border=1)
            self.ln()
        self.ln(3)

    def status_badge(self, status: str) -> None:
        colors = {
            "healthy": (16, 185, 129),
            "critical": (239, 68, 68),
            "warning": (245, 158, 11),
            "monitor": (59, 130, 246),
        }
        r, g, b = colors.get(status.lower(), (107, 114, 128))
        self.set_text_color(r, g, b)
        self.set_font("Helvetica", "B", 10)
        self.cell(0, 7, f"Status: {status.upper()}", new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(31, 41, 55)


def generate_governance_report(
    summary: dict[str, Any],
    output_path: str | None = None,
) -> str:
    """Generate a PDF compliance report.

    Args:
        summary: Dict with keys like budget_summary, risk_summary,
                 recent_transactions, forecast, etc.
        output_path: Where to save the PDF. Defaults to /tmp/.

    Returns:
        Path to the generated PDF file.
    """
    pdf = ComplianceReport()
    pdf.alias_nb_pages()
    pdf.add_page()

    # 1. Executive Summary
    pdf.section_title("1. Executive Summary")
    budget = summary.get("budget_summary", {})
    pdf.key_value("Total Budget (INR)", f"₹{budget.get('total_budget_paise', 0) / 100:,.2f}")
    pdf.key_value("Budget Utilized", f"₹{budget.get('utilized_paise', 0) / 100:,.2f}")
    pdf.key_value("Budget Remaining", f"₹{budget.get('remaining_paise', 0) / 100:,.2f}")
    utilization = budget.get("utilization_percent", 0)
    pdf.key_value("Utilization", f"{utilization}%")
    pdf.ln(3)

    # Severity badge
    forecast = summary.get("forecast", {})
    severity = forecast.get("severity", "healthy")
    pdf.status_badge(severity)
    if forecast.get("runway_days"):
        pdf.key_value("Budget Runway", f"{forecast['runway_days']} days")
    pdf.ln(5)

    # 2. Risk Summary
    pdf.section_title("2. Risk & Anomaly Summary")
    risk = summary.get("risk_summary", {})
    pdf.key_value("Transactions Reviewed", str(risk.get("total_reviewed", 0)))
    pdf.key_value("Anomalies Detected", str(risk.get("anomalies_detected", 0)))
    pdf.key_value("Payouts Held", str(risk.get("payouts_held", 0)))
    pdf.key_value("Payouts Rejected", str(risk.get("payouts_rejected", 0)))
    pdf.ln(5)

    # 3. Recent Transactions Table
    transactions = summary.get("recent_transactions", [])
    if transactions:
        pdf.section_title("3. Recent Transactions")
        headers = ["Date", "Vendor", "Amount (INR)", "Category", "Status"]
        rows = [
            [
                txn.get("date", ""),
                txn.get("vendor", "")[:20],
                f"₹{txn.get('amount_paise', 0) / 100:,.2f}",
                txn.get("category", "misc"),
                txn.get("status", ""),
            ]
            for txn in transactions[:10]
        ]
        pdf.add_table(headers, rows, col_widths=[30, 45, 40, 35, 40])

    # 4. GST Compliance
    gst = summary.get("gst_compliance", {})
    if gst:
        pdf.section_title("4. GST Compliance Status")
        pdf.key_value("GSTINs Validated", str(gst.get("validated", 0)))
        pdf.key_value("Invalid GSTINs", str(gst.get("invalid", 0)))
        pdf.key_value("Total GST Collected (INR)", f"₹{gst.get('total_gst_paise', 0) / 100:,.2f}")
        pdf.ln(5)

    # 5. Fraud Detection
    fraud = summary.get("fraud_detection", {})
    if fraud:
        pdf.section_title("5. Fraud Network Analysis")
        pdf.key_value("Patterns Found", str(fraud.get("patterns_found", 0)))
        pdf.key_value("Risk Level", fraud.get("risk_level", "low").upper())
        findings = fraud.get("findings", [])
        if findings:
            headers = ["Type", "Severity", "Description"]
            rows = [
                [f["type"], f["severity"], f["description"][:50]]
                for f in findings[:5]
            ]
            pdf.add_table(headers, rows, col_widths=[50, 30, 110])

    # Save
    if not output_path:
        output_path = f"/tmp/vyapaarclaw_report_{_dt.datetime.now().strftime('%Y%m%d_%H%M')}.pdf"

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    pdf.output(output_path)
    return output_path
