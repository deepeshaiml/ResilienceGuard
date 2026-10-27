from __future__ import annotations

from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


NAVY = colors.HexColor("#14243A")
TEAL = colors.HexColor("#167C80")
PALE = colors.HexColor("#EEF4F6")


def build_report(assessment: dict[str, Any]) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=0.55 * inch, leftMargin=0.55 * inch, topMargin=0.5 * inch, bottomMargin=0.5 * inch)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="RGTitle", parent=styles["Title"], textColor=NAVY, fontSize=22, leading=26, alignment=TA_LEFT, spaceAfter=8))
    styles.add(ParagraphStyle(name="RGBody", parent=styles["BodyText"], fontSize=8.5, leading=12, spaceAfter=5))
    styles.add(ParagraphStyle(name="RGSmall", parent=styles["BodyText"], fontSize=7, leading=9))
    story = [
        Paragraph("ResilienceGuard | Recovery Readiness Assessment", styles["RGTitle"]),
        Paragraph(f"<b>Scenario:</b> {assessment['scenario']['name']} &nbsp;&nbsp; <b>Observed at:</b> {assessment['observed_at']}", styles["RGBody"]),
        Paragraph("Synthetic demo data. This report describes deterministic inventory and dependency checks plus any recorded sandbox restore. It is not a malware clearance or production recovery attestation.", styles["RGBody"]),
        Spacer(1, 5),
    ]
    metrics = assessment["metrics"]
    metric_rows = [["Services", "Unavailable", "Recoverable now", "Blocked", "Missing backups", "Integrity failures"], [str(metrics["service_count"]), str(metrics["unavailable_services"]), str(metrics["ready_to_recover"]), str(metrics["blocked_services"]), str(metrics["missing_backup_services"]), str(metrics["integrity_failures"])]]
    summary = Table(metric_rows, colWidths=[1.0 * inch] * 6)
    summary.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), NAVY), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("BACKGROUND", (0, 1), (-1, 1), PALE), ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("ALIGN", (0, 0), (-1, -1), "CENTER"), ("FONTSIZE", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7), ("TOPPADDING", (0, 0), (-1, -1), 7), ("GRID", (0, 0), (-1, -1), 0.4, colors.white)]))
    story += [summary, Spacer(1, 12), Paragraph("Service findings", styles["Heading2"])]
    service_rows = [["Service", "Current", "Recovery", "Backup / RPO gap", "Blockers"]]
    for row in assessment["services"]:
        rpo_gap = "—" if row["rpo_gap_seconds"] is None else (f"{row['rpo_gap_seconds'] / 3600:.1f}h gap" if row["rpo_gap_seconds"] else "within target")
        blockers = ", ".join(item["id"] for item in row["recovery_blockers"]) or "—"
        service_rows.append([row["name"], row["status"], row["recovery_status"], f"{row['backup_existence']} / {rpo_gap}", blockers])
    service_table = Table(service_rows, colWidths=[1.55 * inch, 0.75 * inch, 0.72 * inch, 1.2 * inch, 2.2 * inch], repeatRows=1)
    service_table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), TEAL), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 7), ("LEADING", (0, 0), (-1, -1), 8.5), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D2DCE0")), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALE]), ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5), ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    story += [service_table, Spacer(1, 12), Paragraph("Recovery sequence", styles["Heading2"])]
    for item in assessment["recovery_plan"]:
        evidence = f"; evidence {item['evidence_id']}" if item["evidence_id"] else ""
        story.append(Paragraph(f"{item['order']}. {item['service']} — {item['status']}{evidence}", styles["RGBody"]))
    story += [Spacer(1, 5), Paragraph("Evidence and limits", styles["Heading2"])]
    for note in assessment["assurance_notes"]:
        story.append(Paragraph(f"• {note}", styles["RGBody"]))
    story.append(Paragraph("Backup existence, freshness, SHA-256 integrity, malware status, and restore-test success are distinct. A hash match alone cannot establish malware cleanliness or authenticity. RTO gaps before a restore are configured estimates; observed durations are shown only after a real sandbox copy and verification.", styles["RGBody"]))
    story.append(Spacer(1, 7))
    story.append(Paragraph("Evidence register", styles["Heading2"]))
    evidence_rows = [["Evidence ID", "Type", "Subject", "Observation"]]
    for item in assessment["evidence"]:
        evidence_rows.append([item["id"], item["type"], item["subject"], item["detail"]])
    evidence_table = Table(evidence_rows, colWidths=[0.8 * inch, 0.8 * inch, 1.5 * inch, 3.3 * inch], repeatRows=1)
    evidence_table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), NAVY), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 6.5), ("LEADING", (0, 0), (-1, -1), 8), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#D2DCE0")), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALE]), ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
    story.append(evidence_table)
    doc.build(story)
    return buffer.getvalue()
