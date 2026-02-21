from flask import Blueprint, send_file, request, current_app, jsonify
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from io import BytesIO
from datetime import datetime
import os
import sys

# To allow importing from centralized app models
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
from app.models import TribunalClaim, Defect, Project, User

from .config_pdf_labels import PDF_LABELS
from .report_generator import generate_ai_report
from .ai_translate_cached import translate_defects_cached

# We need this to build the inner defect lists
from .report_data import build_defect_list

routes = Blueprint("routes", __name__)

def draw_justified_line(pdf, text, x, y, max_width, font_name, font_size):
    words = text.split()
    if len(words) <= 1:
        pdf.drawString(x, y, text)
        return
    pdf.setFont(font_name, font_size)
    words_width = sum(pdf.stringWidth(w, font_name, font_size) for w in words)
    space_needed = max_width - words_width
    if space_needed <= 0:
        pdf.drawString(x, y, text)
        return
    gap = space_needed / (len(words) - 1)
    cursor_x = x
    for w in words:
        pdf.drawString(cursor_x, y, w)
        cursor_x += pdf.stringWidth(w, font_name, font_size) + gap

def draw_footer(pdf, width, labels):
    pdf.setFont("Helvetica", 8)
    pdf.drawRightString(width - 50, 25, f"{labels['page']} {pdf.getPageNumber()}")

def draw_wrapped_text(pdf, text, x, y, max_width, font_name="Helvetica", font_size=9, leading=14):
    pdf.setFont(font_name, font_size)
    words = text.split()
    line = ""
    for word in words:
        test = line + " " + word if line else word
        if pdf.stringWidth(test, font_name, font_size) <= max_width:
            line = test
        else:
            pdf.drawString(x, y, line)
            y -= leading
            line = word
    if line:
        pdf.drawString(x, y, line)
        y -= leading
    return y

@routes.route('/api/generate_report/<report_type>', methods=['GET'])
def generate_report_api(report_type):
    try:
        language = request.args.get('language', 'en')
        role_map = {
            "homeowner": "Homeowner",
            "developer": "Developer",
            "legal": "Legal"
        }
        role = role_map.get(report_type.lower(), "Homeowner")

        # 1. Fetch data from Centralized DB
        user_id = request.args.get('user_id', type=int)
        project_id = request.args.get('project_id', type=int)
        
        user = User.query.get(user_id) if user_id else None
        project = Project.query.get(project_id) if project_id else None
        
        if role == "Homeowner":
            if not user:
                return jsonify({"error": "User not found"}), 404
            project = user.project or (Project.query.first() if not project else project)
            defects_db = Defect.query.filter_by(user_id=user_id).all()
        else:
            if project:
                defects_db = Defect.query.filter_by(project_id=project.id).all()
            else:
                defects_db = Defect.query.all()

        # 2. Map Database objects to Dictionaries required by PDF & AI
        defects = []
        for d in defects_db:
            defects.append({
                "id": str(d.id),
                "desc": d.description or "No description",
                "unit": user.unit_no if user else (d.location or "N/A"),
                "status": d.status or "Pending",
                "priority": d.severity or "Normal",
                "remarks": "",
                "deadline": d.scheduled_date.strftime("%d-%m-%Y") if d.scheduled_date else "-",
                "is_overdue": False,
                "hda_compliant": True
            })

        # Calculate stats
        stats = {
            "total": len(defects),
            "pending": sum(1 for d in defects if d["status"] in ["Pending", "draft", "New", "Reported", "Belum Diselesaikan"]),
            "completed": sum(1 for d in defects if d["status"] in ["Completed", "Fixed", "Telah Diselesaikan"]),
            "critical": sum(1 for d in defects if d["priority"] in ["High", "Tinggi"])
        }

        # Build dynamic case info from DB
        maklumat_kes = {
            "tribunal": "Tribunal Tuntutan Pengguna Malaysia",
            "lokasi_tribunal": user.tribunal_city if (user and user.tribunal_city) else "Shah Alam",
            "no_tuntutan": f"TTPM/SGR/2026/000001",
            "tarikh_jana": datetime.now().strftime("%d-%m-%Y"),
            "amaun_tuntutan": "RM 0.00",
            "dokumen": "Dokumen Sokongan Borang 1",
            "negeri": user.tribunal_state if (user and user.tribunal_state) else "Selangor"
        }

        pihak_yang_menuntut = {
            "nama": user.full_name if user else "N/A",
            "no_kp": user.ic_number if user else "-",
            "alamat_1": user.correspondence_address if user else "-",
            "alamat_2": "-",
            "no_telefon": user.phone_number if user else "-",
            "email": user.email if user else "-",
            "keterangan": "Pemilik unit kediaman"
        }

        penentang = {
            "nama": project.developer_name if project else "-",
            "no_pendaftaran": project.developer_ssm if project else "-",
            "alamat_1": project.developer_address if project else "-",
            "alamat_2": "-",
            "no_telefon": "-",
            "email": "-",
            "keterangan": "Pemaju projek perumahan"
        }

        # Format context for AI
        def build_summary_stats(s):
            return {
                "jumlah_kecacatan": s.get("total", 0),
                "belum_diselesaikan": s.get("pending", 0),
                "telah_diselesaikan": s.get("completed", 0),
                "kritikal": s.get("critical", 0)
            }
            
        def build_role_context(r):
            if r == "Homeowner":
                return {
                    "tajuk_laporan": "Laporan Tuntutan Kecacatan Defect Liability Period (DLP)",
                    "tujuan": "Laporan ini disediakan bagi merumuskan kecacatan yang berlaku dalam tempoh Defect Liability Period (DLP) untuk rujukan Tribunal."
                }
            if r == "Developer":
                return {
                    "tajuk_laporan": "Laporan Pematuhan Pembaikan Defect Liability Period (DLP)",
                    "tujuan": "Laporan ini disediakan untuk menunjukkan status pembaikan dan pematuhan pemaju terhadap kecacatan yang dilaporkan."
                }
            return {
                "tajuk_laporan": "Laporan Gambaran Keseluruhan Pematuhan Defect Liability Period (DLP)",
                "tujuan": "Laporan ini disediakan sebagai gambaran keseluruhan status kecacatan dan pematuhan untuk rujukan Tribunal."
            }

        report_data = {
            "maklumat_kes": maklumat_kes,
            "pihak_yang_menuntut": pihak_yang_menuntut,
            "penentang": penentang,
            "konteks_peranan": build_role_context(role),
            "ringkasan_statistik": build_summary_stats(stats),
            "senarai_kecacatan": build_defect_list(defects, role),
            "nota_penting": "Laporan ini dijana oleh sistem sebagai dokumen sokongan kepada Borang 1 Tribunal Tuntutan Pengguna Malaysia (TTPM)."
        }

        # STATUS TRANSLATION/NORMALISATION
        for d in defects:
            d["_status_raw"] = d["status"]  # lock status

        defects = translate_defects_cached(defects, language=language, role=role)

        for d in defects:
            d["status"] = d.pop("_status_raw", d["status"])

        STATUS_NORMALISE = {
            "Belum Diselesaikan": "Pending", "draft": "Pending", "New": "Pending", "Reported": "Pending",
            "Dalam Tindakan": "In Progress", "Processing": "In Progress", "Under Review": "In Progress", "in_progress": "In Progress",
            "Telah Diselesaikan": "Completed", "Fixed": "Completed", "completed": "Completed",
            "Tertangguh": "Delayed"
        }
        for d in defects:
            if d.get("status") in STATUS_NORMALISE:
                d["status"] = STATUS_NORMALISE[d["status"]]

        # 3. Generate AI Report (The text component)
        ai_report_text = generate_ai_report(role, report_data, language)

        # 4. Generate PDF Layout
        labels = PDF_LABELS.get(language, PDF_LABELS["ms"])
        
        STATUS_MAP = {
            "ms": {
                "Pending": "Belum Diselesaikan",
                "In Progress": "Dalam Tindakan",
                "Completed": "Telah Diselesaikan",
                "Delayed": "Tertangguh",
            },
            "en": {
                "Pending": "Pending",
                "In Progress": "In Progress",
                "Completed": "Completed",
                "Delayed": "Delayed",
            }
        }
        for d in defects:
            if d.get("status"):
                d["status"] = STATUS_MAP.get(language, {}).get(d["status"], d["status"])

        buffer = BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4

        # Headers
        pdf.setFont("Helvetica-Bold", 11)
        if language == "en":
            pdf.drawCentredString(width/2, height - 40, "CONSUMER PROTECTION ACT 1999")
            pdf.setFont("Helvetica-Bold", 10)
            pdf.drawCentredString(width/2, height - 55, "CONSUMER PROTECTION REGULATIONS (CONSUMER CLAIMS TRIBUNAL) 1999")
            pdf.setFont("Helvetica-Bold", 12)
            pdf.drawCentredString(width/2, height - 90, "FORM 1")
            pdf.setFont("Helvetica", 9)
            pdf.drawCentredString(width/2, height - 102, "(Regulation 5)")
            pdf.setFont("Helvetica-Bold", 11)
            pdf.drawCentredString(width/2, height - 125, "STATEMENT OF CLAIM")
            pdf.setFont("Helvetica", 10)
            pdf.drawCentredString(width/2, height - 145, "IN THE CONSUMER CLAIMS TRIBUNAL")
        else:
            pdf.drawCentredString(width/2, height - 40, "AKTA PERLINDUNGAN PENGGUNA 1999")
            pdf.setFont("Helvetica-Bold", 10)
            pdf.drawCentredString(width/2, height - 55, "PERATURAN-PERATURAN PERLINDUNGAN PENGGUNA (TRIBUNAL TUNTUTAN PENGGUNA) 1999")
            pdf.setFont("Helvetica-Bold", 12)
            pdf.drawCentredString(width/2, height - 90, "BORANG 1")
            pdf.setFont("Helvetica", 9)
            pdf.drawCentredString(width/2, height - 102, "(Peraturan 5)")
            pdf.setFont("Helvetica-Bold", 11)
            pdf.drawCentredString(width/2, height - 125, "PERNYATAAN TUNTUTAN")
            pdf.setFont("Helvetica", 10)
            pdf.drawCentredString(width/2, height - 145, "DALAM TRIBUNAL TUNTUTAN PENGGUNA")

        y = height - 175
        pdf.setFont("Helvetica", 10)
        pdf.drawCentredString(width/2, y, f"AT {maklumat_kes['lokasi_tribunal']}".upper() if language == "en" else f"DI {maklumat_kes['lokasi_tribunal']}".upper())
        y -= 20
        pdf.drawCentredString(width/2, y, f"IN THE STATE OF {maklumat_kes['negeri']}, MALAYSIA".upper() if language == "en" else f"DI NEGERI {maklumat_kes['negeri']}, MALAYSIA".upper())
        y -= 20
        pdf.drawString(50, y, f"CLAIM NO.: {maklumat_kes['no_tuntutan']}" if language == "en" else f"TUNTUTAN NO.: {maklumat_kes['no_tuntutan']}")

        # Claimant
        y -= 40
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(50, y, "CLAIMANT" if language == "en" else "PIHAK YANG MENUNTUT")
        pdf.rect(50, y - 120, width - 100, 110)
        y -= 20
        pdf.setFont("Helvetica", 9)
        if language == "en":
            pdf.drawString(60, y, "Claimant Name")
            pdf.drawString(200, y, f": {pihak_yang_menuntut.get('nama', '')}")
            pdf.drawString(60, y-18, "IC/Passport No.")
            pdf.drawString(200, y-18, f": {pihak_yang_menuntut.get('no_kp', '')}")
            pdf.drawString(60, y-36, "Correspondence Address")
            pdf.drawString(200, y-36, f": {pihak_yang_menuntut.get('alamat_1', '')}")
            pdf.drawString(200, y-51, f"  {pihak_yang_menuntut.get('alamat_2', '')}")
            pdf.drawString(60, y-69, "Phone No.")
            pdf.drawString(200, y-69, f": {pihak_yang_menuntut.get('no_telefon', '')}")
            pdf.drawString(60, y-87, "Fax/Email")
            pdf.drawString(200, y-87, f": {pihak_yang_menuntut.get('email', '')}")
        else:
            pdf.drawString(60, y, "Nama Pihak Yang Menuntut")
            pdf.drawString(200, y, f": {pihak_yang_menuntut.get('nama', '')}")
            pdf.drawString(60, y-18, "No. Kad Pengenalan/Pasport")
            pdf.drawString(200, y-18, f": {pihak_yang_menuntut.get('no_kp', '')}")
            pdf.drawString(60, y-36, "Alamat Surat Menyurat")
            pdf.drawString(200, y-36, f": {pihak_yang_menuntut.get('alamat_1', '')}")
            pdf.drawString(200, y-51, f"  {pihak_yang_menuntut.get('alamat_2', '')}")
            pdf.drawString(60, y-69, "No. Telefon")
            pdf.drawString(200, y-69, f": {pihak_yang_menuntut.get('no_telefon', '')}")
            pdf.drawString(60, y-87, "No. Faks/ E-mel")
            pdf.drawString(200, y-87, f": {pihak_yang_menuntut.get('email', '')}")

        y -= 120
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(50, y, "RESPONDENT" if language == "en" else "PENENTANG")
        pdf.rect(50, y - 130, width - 100, 120)
        y -= 22
        pdf.setFont("Helvetica", 9)
        pdf.drawString(60, y, "Respondent/Company Name" if language == "en" else "Nama Penentang/Syarikat/")
        pdf.drawString(200, y, f": {penentang.get('nama', '')}")
        pdf.drawString(60, y-18, "IC/Company Registration No." if language == "en" else "No. Kad Pengenalan/")
        pdf.drawString(200, y-18, f": {penentang.get('no_pendaftaran', '')}")
        pdf.drawString(60, y-36, "Correspondence Address" if language == "en" else "Alamat Surat Menyurat")
        pdf.drawString(200, y-36, f": {penentang.get('alamat_1', '')}")
        pdf.drawString(60, y-54, "Phone No." if language == "en" else "No. Telefon")
        pdf.drawString(200, y-54, f": {penentang.get('no_telefon', '')}")
        pdf.drawString(60, y-72, "Fax/Email" if language == "en" else "No. Faks/E-mel")
        pdf.drawString(200, y-72, f": {penentang.get('email', '')}")

        y -= 130
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(50, y, "STATEMENT OF CLAIM" if language == "en" else "PERNYATAAN TUNTUTAN")
        y -= 20
        pdf.setFont("Helvetica", 9)
        pdf.drawString(50, y, "The Claimant's claim is for the amount of RM:" if language == "en" else "Tuntutan Pihak Yang Menuntut ialah untuk jumlah RM:")
        pdf.drawString(280, y, f"{maklumat_kes['amaun_tuntutan']}")

        y -= 30
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(50, y, "Claim Details" if language == "en" else "Butir-butir Tuntutan")
        pdf.rect(50, y - 70, width - 100, 60)
        y -= 20
        pdf.setFont("Helvetica", 9)
        pdf.drawString(60, y, "Goods/Services" if language == "en" else "Barangan/Perkhidmatan")
        pdf.drawString(200, y, ": Defect Repairs During DLP Period" if language == "en" else ": Pembaikan Kecacatan Dalam Tempoh DLP")
        pdf.drawString(60, y-15, "Date of Purchase/Transaction" if language == "en" else "Tarikh Pembelian/ Transaksi")
        pdf.drawString(200, y-15, f": {maklumat_kes['tarikh_jana']}")
        pdf.drawString(60, y-30, "Amount Paid" if language == "en" else "Jumlah yang dibayar")
        pdf.drawString(200, y-30, f": {maklumat_kes['amaun_tuntutan']}")

        # Page 2
        draw_footer(pdf, width, labels)
        pdf.showPage()
        y = height - 50

        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(50, y, "Claim Summary:" if language == "en" else "Ringkasan Tuntutan:")
        pdf.rect(50, y - 90, width - 100, 80)
        y -= 25
        pdf.setFont("Helvetica", 9)
        pdf.drawString(60, y, f"Total Defects Reported: {stats['total']}" if language == "en" else f"Jumlah Kecacatan Dilaporkan: {stats['total']}")
        pdf.drawString(60, y-15, f"Pending: {stats['pending']}" if language == "en" else f"Belum Diselesaikan: {stats['pending']}")
        pdf.drawString(60, y-30, f"Completed: {stats['completed']}" if language == "en" else f"Telah Diselesaikan: {stats['completed']}")
        
        y -= 90
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(50, y, "Defect List:" if language == "en" else "Senarai Kecacatan:")
        y -= 20
        pdf.setFont("Helvetica", 9)

        evidence_dir = os.path.join(current_app.root_path, "evidence")
        
        for i, defect in enumerate(defects, 1):
            if y < 260:
                draw_footer(pdf, width, labels)
                pdf.showPage()
                y = height - 50
                pdf.setFont("Helvetica-Bold", 10)
                pdf.drawString(50, y, "Defect List (continued):" if language == "en" else "Senarai Kecacatan (sambungan):")
                y -= 30

            pdf.setFont("Helvetica-Bold", 10)
            pdf.drawString(50, y, f"{chr(64+i)}. {labels['defect_id']} {defect['id']}:")
            y -= 16

            pdf.setFont("Helvetica", 9)
            pdf.drawString(70, y, labels["description"])
            y = draw_wrapped_text(pdf, f": {defect['desc']}", 120, y, width - 170)
            
            pdf.drawString(70, y, labels["unit"])
            pdf.drawString(120, y, f": {defect['unit']}")
            y -= 14

            pdf.drawString(70, y, labels["status"])
            pdf.drawString(120, y, f": {defect['status']}")
            y -= 14
            
            # Evidence
            image_path = os.path.join(evidence_dir, f"defect_{defect['id']}.jpg")
            if os.path.exists(image_path):
                if y < 180:
                    draw_footer(pdf, width, labels)
                    pdf.showPage()
                    y = height - 50
                pdf.setFont("Helvetica-Oblique", 8)
                pdf.drawString(70, y, f"{labels['evidence']}:")
                try:
                    pdf.drawImage(ImageReader(image_path), 70, y - 110, width=200, height=110)
                    y -= 125
                except Exception:
                    y -= 10
            y -= 25

        # AI Report Text Processing
        if ai_report_text:
            draw_footer(pdf, width, labels)
            pdf.showPage()
            y = height - 50

            pdf.setFont("Helvetica-Bold", 12)
            pdf.drawCentredString(width/2, y, "AI-GENERATED CLAIM SUMMARY REPORT" if language == "en" else "LAPORAN RINGKASAN TUNTUTAN DIJANA AI")
            y -= 30

            import re
            clean_text = ai_report_text.replace('**', '').replace('*', '').replace('##', '').replace('#', '').replace('\r\n', '\n').replace('\r', '\n')
            clean_text = re.sub(r'[^\x00-\x7F]+', '', clean_text)
            
            lines = clean_text.split('\n')
            for line in lines:
                if not line.strip():
                    y -= 8
                    continue
                if y < 80:
                    draw_footer(pdf, width, labels)
                    pdf.showPage()
                    y = height - 50
                stripped = line.strip()
                if stripped[:2].isdigit() and stripped[1] == ".": y -= 12
                if stripped[:2] in ["A.", "B.", "C.", "D."]: y -= 8
                
                pdf.setFont("Helvetica", 9)
                y = draw_wrapped_text(pdf, stripped, 50, y, width - 100)

        # Signature page
        draw_footer(pdf, width, labels)
        pdf.showPage()
        y = height - 50
        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawCentredString(width / 2, y, "Verification and Signature" if language == "en" else "Pengesahan dan Tandatangan")
        y -= 90
        pdf.setFont("Helvetica", 9)
        pdf.drawString(50, y, "." * 55)
        pdf.drawString(width - 200, y, "." * 60)
        y -= 20
        pdf.drawString(50, y, "Date" if language == "en" else "Tarikh")
        pdf.drawString(width - 200, y, "Signature" if language == "en" else "Tandatangan")

        draw_footer(pdf, width, labels)
        pdf.save()
        buffer.seek(0)
        
        filename = labels["legal_filename"] if role == "Legal" else labels["developer_filename"] if role == "Developer" else labels["homeowner_filename"]
        return send_file(buffer, as_attachment=True, download_name=filename, mimetype="application/pdf")

    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500
