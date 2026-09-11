"""
app/faculty/services/reports_service.py

Reports (Section 12). Each `generate_*_report()` function returns
plain Python data (list of dicts + a title) — the three `to_*()`
exporters are format-agnostic over that same shape, so adding a 6th
report type later never means writing 3 more export functions.

Format choices (Part 3's free/low-cost principle): CSV via the
standard library (zero dependencies); Excel via openpyxl (free,
BSD-licensed, no external service); PDF via reportlab (free, BSD-
licensed) rendering a simple, readable title+table layout — not a
styled institutional template, which is out of scope for a student
project but genuinely produces a real, valid PDF a faculty member can
open and print.
"""

import csv
import io

from openpyxl import Workbook
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

from app.models import User, Quiz
from app.utils.constants import ROLE_STUDENT
from app.faculty.services import student_management, class_analytics
from app.analytics.services import performance_scorer


# --- Report builders (return {"title": str, "columns": [...], "rows": [[...], ...]}) ---

def generate_student_progress_report(student_id: int) -> dict:
    detail = student_management.get_student_detail(student_id)
    if detail is None:
        raise ValueError("Student not found.")

    rows = [[t["topic_name"], f'{t["mastery_score"]:.1f}'] for t in detail["progress"]["tracked_topics"]]
    return {
        "title": f"Progress Report — {detail['profile']['name']}",
        "columns": ["Topic", "Mastery %"],
        "rows": rows,
    }


def generate_class_performance_report() -> dict:
    data = class_analytics.topic_wise_class_performance()
    rows = [[t["topic_name"], f'{t["average_mastery"]:.1f}', t["student_count"]] for t in data]
    return {"title": "Class Performance Report", "columns": ["Topic", "Average Mastery %", "Students Tracking"], "rows": rows}


def generate_quiz_report(quiz_id: int) -> dict:
    from app.faculty.services.quiz_management import get_quiz_results

    results = get_quiz_results(quiz_id)
    if results is None:
        raise ValueError("Quiz not found.")
    rows = [[r["student_name"], r["student_email"], f'{r["score_percent"]:.1f}' if r["score_percent"] is not None else "—", r["completed_at"] or "—"]
            for r in results["results"]]
    return {
        "title": f"Quiz Report — {results['quiz_title']} ({results['topic_name']})",
        "columns": ["Student", "Email", "Score %", "Completed At"],
        "rows": rows,
    }


def generate_topic_mastery_report() -> dict:
    data = class_analytics.topic_completion_rates()
    rows = [[t["topic_name"], f'{t["completion_rate_percent"]:.1f}', t["tracking_student_count"]] for t in data]
    return {"title": "Topic Mastery Report", "columns": ["Topic", "Completion Rate % (75%+ mastery)", "Students Tracking"], "rows": rows}


def generate_faculty_summary_report() -> dict:
    students = User.query.filter_by(role=ROLE_STUDENT).all()
    rows = []
    for s in students:
        scores = performance_scorer.compute_all_scores(s.id)
        rows.append([
            s.name, s.email,
            f'{scores["overall_learning_score"]:.1f}' if scores["overall_learning_score"] is not None else "—",
            scores["completed_topic_count"],
        ])
    return {"title": "Faculty Summary Report — All Students", "columns": ["Name", "Email", "Overall Score", "Topics Completed"], "rows": rows}


# --- Exporters (format-agnostic over the {title, columns, rows} shape) ---

def to_csv(report: dict) -> io.BytesIO:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([report["title"]])
    writer.writerow(report["columns"])
    writer.writerows(report["rows"])
    out = io.BytesIO(buf.getvalue().encode("utf-8"))
    out.seek(0)
    return out


def to_excel(report: dict) -> io.BytesIO:
    wb = Workbook()
    ws = wb.active
    ws.title = "Report"
    ws.append([report["title"]])
    ws.append(report["columns"])
    for row in report["rows"]:
        ws.append(row)
    for col_cells in ws.columns:
        max_len = max((len(str(c.value)) for c in col_cells if c.value is not None), default=10)
        ws.column_dimensions[col_cells[0].column_letter].width = min(max_len + 2, 40)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


def to_pdf(report: dict) -> io.BytesIO:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = [Paragraph(report["title"], styles["Title"]), Spacer(1, 12)]

    table_data = [report["columns"]] + [[str(c) for c in row] for row in report["rows"]]
    table = Table(table_data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2E2A24")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F0E8")]),
    ]))
    elements.append(table)
    doc.build(elements)
    buf.seek(0)
    return buf
