"""
ReportAgent – generates a beautiful PDF/HTML report from a DailyReport object
and emails it to the configured recipient.

Pipeline:
  1. Render Jinja2 HTML template with report data
  2. Convert HTML → PDF using WeasyPrint
  3. Save PDF to local disk (REPORT_DOWNLOAD_DIR)
  4. Email PDF + HTML via aiosmtplib
"""
from __future__ import annotations

import asyncio
from datetime import datetime
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import aiosmtplib
from jinja2 import Environment, FileSystemLoader, select_autoescape

from config.settings import settings
from core.logger import logger
from core.models import DailyReport


# ─────────────────────────────────────────────────────────────────────────────
# Jinja2 environment
# ─────────────────────────────────────────────────────────────────────────────

TEMPLATE_DIR = Path(__file__).parent.parent / "templates"

jinja_env = Environment(
    loader=FileSystemLoader(str(TEMPLATE_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
)

# Custom Jinja2 filters
def _inr(value: float) -> str:
    """Format number as Indian Rupee string."""
    if value >= 1_00_00_000:
        return f"₹{value/1_00_00_000:.2f} Cr"
    elif value >= 1_00_000:
        return f"₹{value/1_00_000:.2f} L"
    elif value >= 1_000:
        return f"₹{value/1_000:.1f}K"
    return f"₹{value:,.0f}"

jinja_env.filters["inr"] = _inr
jinja_env.filters["pct"] = lambda v: f"{v:.1f}%"
jinja_env.filters["stars"] = lambda v: "★" * round(v) + "☆" * (5 - round(v))


# ─────────────────────────────────────────────────────────────────────────────
# ReportAgent
# ─────────────────────────────────────────────────────────────────────────────

class ReportAgent:
    def __init__(self) -> None:
        self.download_dir = settings.report_download_dir

    # ── Render HTML ───────────────────────────────────────────────────────────

    def render_html(self, report: DailyReport) -> str:
        template = jinja_env.get_template("report.html.j2")
        return template.render(
            report=report,
            generated_at=datetime.now().strftime("%d %b %Y, %I:%M %p IST"),
        )

    # ── Convert to PDF ────────────────────────────────────────────────────────

    def _html_to_pdf(self, html: str, output_path: Path) -> None:
        try:
            from weasyprint import HTML as WeasyprintHTML
            WeasyprintHTML(string=html).write_pdf(str(output_path))
            logger.info(f"PDF saved: {output_path}")
        except ImportError:
            logger.warning("WeasyPrint not available; falling back to reportlab basic PDF.")
            self._fallback_pdf(output_path)

    def _fallback_pdf(self, output_path: Path) -> None:
        """Very basic ReportLab fallback if WeasyPrint has system deps issues."""
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        c = canvas.Canvas(str(output_path), pagesize=A4)
        c.setFont("Helvetica-Bold", 18)
        c.drawString(50, 800, "Meesho Daily Business Report")
        c.setFont("Helvetica", 12)
        c.drawString(50, 770, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M IST')}")
        c.drawString(50, 740, "(Full HTML report attached separately)")
        c.save()

    # ── Save locally ──────────────────────────────────────────────────────────

    def save_report(self, report: DailyReport) -> tuple[Path, Path]:
        """Returns (html_path, pdf_path)."""
        date_str = report.report_date or datetime.now().strftime("%Y-%m-%d")
        base_name = f"meesho_report_{date_str}"

        html_path = self.download_dir / f"{base_name}.html"
        pdf_path = self.download_dir / f"{base_name}.pdf"

        html_content = self.render_html(report)
        html_path.write_text(html_content, encoding="utf-8")
        logger.info(f"HTML report saved: {html_path}")

        self._html_to_pdf(html_content, pdf_path)
        return html_path, pdf_path

    # ── Email ──────────────────────────────────────────────────────────────────

    async def send_email(self, report: DailyReport, html_path: Path, pdf_path: Path) -> None:
        logger.info(f"Sending report email to {settings.report_recipient_email}…")

        msg = MIMEMultipart("mixed")
        msg["Subject"] = (
            f"📊 Meesho Daily Business Report – {report.report_date} | "
            f"Revenue ₹{report.order_metrics.revenue_30d:,.0f} (30d)"
        )
        msg["From"] = settings.smtp_username
        msg["To"] = settings.report_recipient_email
        if settings.cc_list:
            msg["Cc"] = ", ".join(settings.cc_list)

        # HTML body
        html_body = self.render_html(report)
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        # PDF attachment
        if pdf_path.exists():
            with open(pdf_path, "rb") as f:
                pdf_part = MIMEApplication(f.read(), _subtype="pdf")
                pdf_part.add_header(
                    "Content-Disposition", "attachment", filename=pdf_path.name
                )
                msg.attach(pdf_part)

        recipients = [settings.report_recipient_email] + settings.cc_list

        await aiosmtplib.send(
            msg,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_username,
            password=settings.smtp_password,
            start_tls=True,
            recipients=recipients,
        )
        logger.info("Email sent successfully ✓")

    # ── Main entry point ──────────────────────────────────────────────────────

    async def run(self, report: DailyReport) -> tuple[Path, Path]:
        html_path, pdf_path = self.save_report(report)
        await self.send_email(report, html_path, pdf_path)
        return html_path, pdf_path
