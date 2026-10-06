from datetime import datetime
from io import BytesIO
from pathlib import Path
import sqlite3, re, os

from flask import Flask, jsonify, render_template, request, send_file
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import HRFlowable, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.lib import colors

from google import genai as google_genai

BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "petitions.db"
app = Flask(__name__)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS petitions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                title       TEXT NOT NULL,
                background  TEXT NOT NULL,
                grievance   TEXT NOT NULL,
                request     TEXT NOT NULL,
                evidence    TEXT,
                petitioner  TEXT NOT NULL,
                student_id  TEXT NOT NULL,
                faculty     TEXT NOT NULL,
                email       TEXT NOT NULL,
                level       TEXT,
                created_at  TEXT NOT NULL
            )
        """)


def esc(v):
    return (v or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br/>")


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/api/petitions")
def save_petition():
    d = request.get_json(silent=True) or {}
    required = ["title", "background", "grievance", "request", "petitioner", "student_id", "faculty", "email"]
    missing = [f for f in required if not str(d.get(f, "")).strip()]
    if missing:
        return jsonify({"error": "Please complete all required fields.", "fields": missing}), 400
    now = datetime.now().isoformat(timespec="seconds")
    with get_db() as conn:
        cur = conn.execute("""
            INSERT INTO petitions
            (title, background, grievance, request, evidence, petitioner, student_id, faculty, email, level, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, (
            d["title"].strip(), d["background"].strip(), d["grievance"].strip(),
            d["request"].strip(), d.get("evidence", "").strip(),
            d["petitioner"].strip(), d["student_id"].strip(), d["faculty"].strip(),
            d["email"].strip(), d.get("level", "").strip(), now,
        ))
    return jsonify({"id": cur.lastrowid}), 201


@app.get("/petition/<int:pid>/pdf")
def download_pdf(pid):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM petitions WHERE id = ?", (pid,)).fetchone()
    if not row:
        return jsonify({"error": "Not found."}), 404
    p = dict(row)

    W, H = A4
    MARGIN_X = 25.4 * mm
    MARGIN_Y = 25.4 * mm

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=MARGIN_X, rightMargin=MARGIN_X,
        topMargin=MARGIN_Y, bottomMargin=MARGIN_Y,
    )

    C_INK   = colors.black
    C_MUTED = colors.HexColor("#333333")
    C_LINE  = colors.HexColor("#999999")

    s_ref   = ParagraphStyle("ref",  fontName="Times-Roman", fontSize=11, leading=15, textColor=C_INK)
    s_addr  = ParagraphStyle("addr", fontName="Times-Roman", fontSize=11, leading=15, textColor=C_INK)
    s_addr_b= ParagraphStyle("addrb",fontName="Times-Bold",  fontSize=11, leading=15, textColor=C_INK)
    s_salut = ParagraphStyle("sal",  fontName="Times-Roman", fontSize=11, leading=15, textColor=C_INK, spaceBefore=12)
    s_ptitle= ParagraphStyle("pt",   fontName="Times-Bold",  fontSize=12, leading=16, textColor=C_INK, spaceBefore=14, spaceAfter=8, alignment=TA_CENTER)
    s_body  = ParagraphStyle("body", fontName="Times-Roman", fontSize=11, leading=16, textColor=C_INK, alignment=TA_JUSTIFY, spaceAfter=8)
    s_h     = ParagraphStyle("h",    fontName="Times-Bold",  fontSize=11, leading=15, textColor=C_INK, spaceBefore=14, spaceAfter=4)
    s_close = ParagraphStyle("cl",   fontName="Times-Roman", fontSize=11, leading=15, textColor=C_INK, spaceBefore=12)
    s_small = ParagraphStyle("sm",   fontName="Times-Italic",fontSize=9,  leading=12, textColor=C_MUTED)
    s_sig_l = ParagraphStyle("sigl", fontName="Times-Roman", fontSize=10, leading=14, textColor=C_INK)

    def draw_footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Times-Roman", 10)
        canvas.setFillColor(C_MUTED)
        canvas.drawRightString(W - MARGIN_X, MARGIN_Y / 2, f"Page {doc.page}  |  {p['created_at'][:10]}")
        canvas.restoreState()

    ref_date = p["created_at"][:10]

    story = [
        Paragraph(f"Date: {ref_date}", ParagraphStyle("ref_right", parent=s_ref, alignment=TA_LEFT)),
        Spacer(1, 16),
        Paragraph("The Dean,", s_addr),
        Paragraph("<b>Student Affairs,</b>", s_addr),
        Paragraph("Veritas University,", s_addr),
        Paragraph("Bwari Area Council, F.C.T., Abuja.", s_addr),
        Spacer(1, 12),
        Paragraph("<i>Through: The Senate President,</i>", s_addr),
        Paragraph("<i>Student Delegatory Parliament, Veritas University.</i>", s_addr),
        Spacer(1, 16),
        Paragraph("RE: " + esc(p["title"]).upper(), s_ptitle),
        HRFlowable(width="100%", thickness=1, color=C_INK, spaceAfter=14),
        Paragraph("Dear Sir/Ma,", s_salut),
        Spacer(1, 8),
        Paragraph("1.  Background", s_h),
        Paragraph(esc(p["background"]), s_body),
        Paragraph("2.  Statement of Grievance", s_h),
        Paragraph(esc(p["grievance"]), s_body),
        Paragraph("3.  Prayer / Request", s_h),
        Paragraph(esc(p["request"]), s_body),
    ]

    if p["evidence"]:
        story += [
            Paragraph("4.  Supporting Evidence", s_h),
            Paragraph(esc(p["evidence"]), s_body),
        ]

    story += [
        Spacer(1, 12),
        Paragraph(
            "We trust that this matter will receive your prompt and favourable attention. "
            "We remain committed to the welfare of all students of this institution.",
            s_body
        ),
        Spacer(1, 12),
        Paragraph("Yours faithfully,", s_close),
        Spacer(1, 40),
        HRFlowable(width="45%", thickness=1, color=C_INK, spaceAfter=4),
        Paragraph(f"<b>{esc(p['petitioner'])}</b>", s_addr_b),
        Paragraph(f"{esc(p['student_id'])}  |  {esc(p['faculty'])}", s_addr),
        Paragraph(f"Level: {esc(p['level']) or 'N/A'}  |  Email: {esc(p['email'])}", s_addr),
        Spacer(1, 35),
        HRFlowable(width="100%", thickness=1, color=C_INK, spaceAfter=12),
        Table(
            [[
                [Spacer(1, 36),
                 HRFlowable(width="100%", thickness=1, color=C_INK),
                 Spacer(1, 4),
                 Paragraph("Senate President's Signature & Stamp", s_sig_l),
                 Paragraph("Student Delegatory Parliament", s_sig_l)],
                [],
                [Spacer(1, 36),
                 HRFlowable(width="100%", thickness=1, color=C_INK),
                 Spacer(1, 4),
                 Paragraph("Received by (Student Affairs)", s_sig_l),
                 Paragraph("Date: ________________________", s_sig_l)],
            ]],
            colWidths=["45%", "10%", "45%"],
            style=TableStyle([
                ("VALIGN",        (0, 0), (-1, -1), "BOTTOM"),
                ("LEFTPADDING",   (0, 0), (-1, -1), 0),
                ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
                ("TOPPADDING",    (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ])
        ),
        Spacer(1, 25),
        HRFlowable(width="100%", thickness=0.5, color=C_LINE),
        Spacer(1, 4),
        Paragraph(
            "Print, sign, and submit the original copy to the Student Delegatory Parliament Secretariat for onward transmission.",
            s_small
        ),
    ]

    doc.build(story, onFirstPage=draw_footer, onLaterPages=draw_footer)
    buf.seek(0)
    filename = re.sub(r"[^\w\-_\.]", "_", p["title"])[:40]
    return send_file(buf, as_attachment=True, download_name=f"Petition_{filename}.pdf", mimetype="application/pdf")


@app.post("/api/suggest-title")
def suggest_title():
    d = request.get_json(silent=True) or {}
    background = d.get("background", "").strip()
    grievance  = d.get("grievance", "").strip()
    text = (background + " " + grievance).strip()
    if len(text) < 15:
        return jsonify({"error": "Add more detail first."}), 400

    if GEMINI_API_KEY:
        try:
            client = google_genai.Client(api_key=GEMINI_API_KEY)
            prompt = (
                "You are helping a university student write a formal petition to their Student Affairs Unit. "
                "Based on the following context, suggest exactly 3 concise, formal petition titles. "
                "Return only a JSON array of 3 strings, nothing else.\n\n"
                f"Background: {background}\nGrievance: {grievance}"
            )
            response = client.models.generate_content(
                model="gemini-2.0-flash", contents=prompt
            )
            raw = response.text.strip()
            raw = re.sub(r"^```[\w]*\n?", "", raw)
            raw = re.sub(r"\n?```$", "", raw)
            suggestions = __import__("json").loads(raw)
            if isinstance(suggestions, list) and len(suggestions) >= 3:
                return jsonify({"suggestions": [str(s) for s in suggestions[:3]]})
        except Exception:
            pass

    # local fallback
    stop = {"about","the","and","that","this","with","from","have","been","they","their","which","would","could","should","into","also","very","more"}
    words = [w for w in re.findall(r"[A-Za-z]+", text) if w.lower() not in stop]
    subject = " ".join(words[:7])
    return jsonify({"suggestions": [
        f"Petition Regarding {subject}",
        f"Formal Petition on {subject}",
        f"Student Petition: {subject}",
    ]})


init_db()
if __name__ == "__main__":
    app.run(debug=True)
