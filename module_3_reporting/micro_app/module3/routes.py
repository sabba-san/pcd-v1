from flask import Blueprint, send_file, request, current_app, jsonify, render_template

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

from io import BytesIO
from datetime import datetime
import os
import sys
import json
import re

# To allow importing from centralized app models
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
from app.models import TribunalClaim, Defect, Project, User

from .config_pdf_labels import PDF_LABELS
from .report_generator import generate_ai_report
from .ai_translate_cached import translate_defects_cached, translate_report_cached
from .report_data import build_defect_list

routes = Blueprint("routes", __name__)

# --------------------------------
# HELPERS
# --------------------------------
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

def draw_footer(pdf, width, labels, hash_str=""):
    pdf.setFont("Helvetica", 8)
    pdf.drawRightString(width - 50, 25, f"{labels['page']} {pdf.getPageNumber()}")
    if hash_str:
        pdf.drawString(50, 25, f"{labels.get('digital_hash_label', 'Digital Validation Hash:')} {hash_str}")

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

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

REMARKS_FILE = "remarks.json"
STATUS_FILE = "status.json"

def load_remarks():
    if not os.path.exists(REMARKS_FILE):
        return {}
    with open(REMARKS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_remarks(data):
    with open(REMARKS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def load_status():
    if not os.path.exists(STATUS_FILE):
        return {}
    with open(STATUS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_status(data):
    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


# =========================================================================
# CENTRALIZED DATA FETCHER
# Extracts logic from API to be reused by both the new Dashboard & API
# =========================================================================
def fetch_defects_and_data_from_db(role, user_id, project_id):
    """
    Fetches real data from DB, acting as the bridge replacing `dummy_data.py`.
    Returns dict containing: defects, stats, maklumat_kes, pihak_yang_menuntut, penentang
    """
    user = User.query.get(user_id) if user_id else None
    project = Project.query.get(project_id) if project_id else None
    
    if role == "Homeowner":
        if not user:
            # Fallback for empty requests or missing user
            defects_db = []
        else:
            project = user.project or (Project.query.first() if not project else project)
            defects_db = Defect.query.filter_by(user_id=user_id).all()
    else:
        if project:
            defects_db = Defect.query.filter_by(project_id=project.id).all()
        else:
            defects_db = Defect.query.all()
        
        if not user and defects_db:
            for d in defects_db:
                if d.user and d.user.role == 'user':
                    user = d.user
                    break

    defects = []
    for d in defects_db:
        defect_image_path = d.images[0].image_path if hasattr(d, 'images') and len(d.images) > 0 else None
        
        unit_val = "N/A"
        if user and hasattr(user, 'unit_no') and user.unit_no and str(user.unit_no) != "None":
            unit_val = user.unit_no
        elif hasattr(d, 'location') and d.location and str(d.location) != "None":
            unit_val = d.location
        elif hasattr(d, 'unit_no') and d.unit_no and str(d.unit_no) != "None":
            unit_val = d.unit_no

        defects.append({
            "id": d.id,
            "project_name": project.name if project else "N/A",
            "full_name": user.full_name if user else "N/A",
            "unit": unit_val,
            "desc": d.description or "No description",
            "status": d.status or "Pending",
            "priority": d.severity or "Normal",
            # Fallback urgencys for Nabilah's UI mapping
            "urgency": d.severity or "Normal",
            "remarks": d.notes if hasattr(d, 'notes') and d.notes else "",
            "deadline": d.scheduled_date.strftime("%Y-%m-%d") if d.scheduled_date else "",
            "is_overdue": False,
            "hda_compliant": True,
            "image_path": defect_image_path
        })

    # Stats
    stats = {
        "total": len(defects),
        "pending": sum(1 for d in defects if d["status"] in ["Pending", "draft", "New", "Reported", "Belum Diselesaikan"]),
        "completed": sum(1 for d in defects if d["status"] in ["Completed", "Fixed", "Telah Diselesaikan"]),
        "critical": sum(1 for d in defects if d["priority"] in ["High", "Tinggi"])
    }

    # Case info
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

    developer_user = None
    dev_id = request.args.get('dev_id', type=int)
    if dev_id:
        developer_user = User.query.get(dev_id)
    elif project and project.developer_name:
        developer_user = User.query.filter_by(role='developer', company_name=project.developer_name).first()
        
    penentang_nama = "Gamuda Berhad"
    if developer_user and developer_user.company_name:
        penentang_nama = developer_user.company_name
    elif project and project.developer_name:
        penentang_nama = project.developer_name
    elif developer_user and developer_user.full_name:
        penentang_nama = developer_user.full_name
        
    penentang = {
        "nama": penentang_nama,
        "no_pendaftaran": (developer_user.company_reg_no or developer_user.nric or "-") if developer_user else (project.developer_ssm if project else "-"),
        "alamat_1": (developer_user.company_address or "-") if developer_user else (project.developer_address if project else "-"),
        "alamat_2": "-",
        "no_telefon": (developer_user.contact_number or "-") if developer_user else "-",
        "email": (developer_user.fax_email or "-") if developer_user else "-",
        "keterangan": "Pemaju projek perumahan"
    }

    return {
        "defects": defects,
        "stats": stats,
        "maklumat_kes": maklumat_kes,
        "pihak_yang_menuntut": pihak_yang_menuntut,
        "penentang": penentang
    }

# =================================================
# NEW DASHBOARD ROUTE (Merges Nabilah's UI with Active DB)
# =================================================
@routes.route("/")
def dashboard():
    role = request.args.get("role", "Homeowner")
    
    # NEW: Fetch DB values dynamically based on args instead of dummy_data
    user_id = request.args.get('user_id', type=int)
    project_id = request.args.get('project_id', type=int)
    
    data = fetch_defects_and_data_from_db(role, user_id, project_id)
    defects = data["defects"]
    stats = data["stats"]
    
    remarks_store = load_remarks()
    status_store = load_status()

    # Apply overridden statuses / remarks
    for d in defects:
        d["status"] = status_store.get(str(d["id"]), d["status"])

        if role == "Homeowner":
            d["remarks"] = remarks_store.get(str(d["id"]), d["remarks"])
        else:
            d["remarks"] = ""

    template = (
        "dashboard_homeowner.html"
        if role == "Homeowner"
        else "dashboard_developer.html"
        if role == "Developer"
        else "dashboard_legal.html"
    )

    return render_template(
        template,
        role=role,
        defects=defects,
        stats=stats
    )


# =================================================
# ORIGINAL GENERATE REPORT API
# =================================================
@routes.route('/api/generate_report/<report_type>', methods=['GET'])
def generate_report_api_legacy(report_type):
    # This was originally `/api/generate_report/<report_type>`.
    # It acts identically to the original to prevent breakage.
    try:
        language = request.args.get('language', 'en')
        role_map = {
            "homeowner": "Homeowner",
            "developer": "Developer",
            "legal": "Legal"
        }
        role = role_map.get(report_type.lower(), "Homeowner")

        user_id = request.args.get('user_id', type=int)
        project_id = request.args.get('project_id', type=int)
        
        data = fetch_defects_and_data_from_db(role, user_id, project_id)
        
        return export_pdf_internal(role, language, "", data)

    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500


# =================================================
# EVIDENCE ENDPOINTS
# =================================================
@routes.route("/upload_evidence", methods=["POST"])
def upload_evidence():
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400
        
        file = request.files['file']
        defect_id = request.form.get('defect_id')
        
        if not defect_id:
            return jsonify({"error": "No defect ID provided"}), 400
        
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        
        if not allowed_file(file.filename):
            return jsonify({"error": "File type not allowed. Use: png, jpg, jpeg, gif, webp"}), 400
        
        evidence_dir = os.path.join(current_app.root_path, "evidence")
        os.makedirs(evidence_dir, exist_ok=True)
        
        filename = f"defect_{defect_id}.jpg"
        filepath = os.path.join(evidence_dir, filename)
        file.save(filepath)
        
        return jsonify({
            "success": True,
            "message": f"Evidence uploaded for defect #{defect_id}",
            "filename": filename,
            "defect_id": defect_id
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@routes.route("/evidence/<defect_id>")
def get_evidence(defect_id):
    evidence_dir = os.path.join(current_app.root_path, "evidence")
    filename = f"defect_{defect_id}.jpg"
    filepath = os.path.join(evidence_dir, filename)
    if os.path.exists(filepath):
        return send_file(filepath, mimetype='image/jpeg')
    return jsonify({"error": "Evidence not found"}), 404

@routes.route("/evidence_exists/<defect_id>")
def evidence_exists(defect_id):
    evidence_dir = os.path.join(current_app.root_path, "evidence")
    filename = f"defect_{defect_id}.jpg"
    filepath = os.path.join(evidence_dir, filename)
    return jsonify({
        "exists": os.path.exists(filepath),
        "defect_id": defect_id
    })

@routes.route("/add_remark", methods=["POST"])
def add_remark():
    data = request.get_json()
    role = data.get("role")
    if role != "Homeowner":
        return jsonify({"error": "Unauthorized"}), 403
    defect_id = str(data.get("id"))
    remark = data.get("remark")
    if not defect_id or not remark:
        return jsonify({"error": "Invalid data"}), 400
    remarks = load_remarks()
    remarks[defect_id] = remark
    save_remarks(remarks)
    return jsonify({"success": True})

@routes.route("/update_status", methods=["POST"])
def update_status():
    data = request.get_json()
    defect_id = str(data.get("id"))
    new_status = data.get("status")
    ALLOWED_STATUS = {"Pending", "In Progress", "Completed", "Delayed"}
    if not defect_id or new_status not in ALLOWED_STATUS:
        return jsonify({"message": "Invalid status"}), 400
    status_store = load_status()
    status_store[defect_id] = new_status
    save_status(status_store)
    return jsonify({"message": "Status updated successfully"})

@routes.route("/api/update_defect_date", methods=["POST"])
def update_defect_date():
    from app import db
    data = request.get_json()
    defect_id = data.get("id")
    new_date = data.get("date")
    
    if not defect_id or not new_date:
        return jsonify({"message": "Invalid date or ID"}), 400
        
    defect = Defect.query.get(defect_id)
    if not defect:
        return jsonify({"message": "Defect not found"}), 404
        
    try:
        defect.scheduled_date = datetime.strptime(new_date, "%Y-%m-%d")
        db.session.commit()
        return jsonify({"message": "Deadline updated successfully"})
    except ValueError:
        return jsonify({"message": "Invalid date format, expected YYYY-MM-DD"}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": f"Error updating date: {str(e)}"}), 500



# =================================================
# NEW GENERATE AI REPORT (JSON)
# =================================================
@routes.route("/generate_ai_report", methods=["POST"])
def generate_ai_report_endpoint():
    try:
        data_req = request.get_json(silent=True) or {}
        role = data_req.get("role", "Homeowner")
        language = data_req.get("language", "ms")
        
        user_id = data_req.get('user_id')
        project_id = data_req.get('project_id')

        data = fetch_defects_and_data_from_db(role, user_id, project_id)
        defects = data['defects']
        
        remarks_store = load_remarks()
        status_store = load_status()

        for d in defects:
            d["status"] = status_store.get(str(d["id"]), d["status"])
            d["remarks"] = remarks_store.get(str(d["id"]), d["remarks"])
            if "urgency" in d and not d.get("priority"):
                d["priority"] = d["urgency"]

        for d in defects:
            d["_status_raw"] = d["status"]

        defects = translate_defects_cached(defects, language=language, role=role)

        if language == "ms":
            for d in defects:
                if d.get("remarks"):
                    d["remarks"] = translate_report_cached(d["remarks"], language="ms", role=role)
        elif language == "en":
            for d in defects:
                if d.get("remarks"):
                    d["remarks"] = translate_report_cached(d["remarks"], language="en", role=role)

        for d in defects:
            d["status"] = d.pop("_status_raw", d["status"])

        if role != "Homeowner":
            for d in defects:
                d["remarks"] = ""
        
        STATUS_NORMALISE = {
            "Belum Diselesaikan": "Pending", "draft": "Pending", "New": "Pending", "Reported": "Pending",
            "Dalam Tindakan": "In Progress", "Processing": "In Progress", "Under Review": "In Progress", "in_progress": "In Progress",
            "Telah Diselesaikan": "Completed", "Fixed": "Completed", "completed": "Completed",
            "Tertangguh": "Delayed"
        }

        for d in defects:
            if d.get("status") in STATUS_NORMALISE:
                d["status"] = STATUS_NORMALISE[d["status"]]

        def build_summary_stats(s):
            return {
                "jumlah_kecacatan": s.get("total", 0),
                "belum_diselesaikan": s.get("pending", 0),
                "telah_diselesaikan": s.get("completed", 0),
                "kritikal": s.get("critical", 0)
            }
            
        def build_role_context(r, lang):
            if r == "Homeowner":
                return {
                    "tajuk_laporan": "BORANG 1 - PERNYATAAN TUNTUTAN" if lang == "ms" else "FORM 1 - STATEMENT OF CLAIM",
                    "tujuan": "Laporan ini disediakan bagi merumuskan kecacatan yang berlaku dalam tempoh Defect Liability Period (DLP) untuk rujukan Tribunal."
                }
            if r == "Developer":
                return {
                    "tajuk_laporan": "LAPORAN PEMATUHAN DLP" if lang == "ms" else "DLP COMPLIANCE REPORT",
                    "tujuan": "Laporan ini disediakan untuk menunjukkan status pembaikan dan pematuhan pemaju terhadap kecacatan yang dilaporkan."
                }
            return {
                "tajuk_laporan": "LAPORAN RUJUKAN TRIBUNAL DLP" if lang == "ms" else "TRIBUNAL REFERENCE REPORT (DLP)",
                "tujuan": "Laporan ini disediakan sebagai gambaran keseluruhan status kecacatan dan pematuhan untuk rujukan Tribunal."
            }

        report_data = {
            "maklumat_kes": data['maklumat_kes'],
            "pihak_yang_menuntut": data['pihak_yang_menuntut'],
            "penentang": data['penentang'],
            "konteks_peranan": build_role_context(role, language),
            "ringkasan_statistik": build_summary_stats(data['stats']),
            "senarai_kecacatan": build_defect_list(defects, role),
            "nota_penting": "Laporan ini dijana oleh sistem sebagai dokumen sokongan kepada Borang 1 Tribunal Tuntutan Pengguna Malaysia (TTPM)."
        }

        STATUS_MAP = {
            "ms": {
                "Pending": "Belum Diselesaikan",
                "In Progress": "Dalam Tindakan",
                "Completed": "Telah Diselesaikan",
                "Delayed": "Tertangguh",
            },
            "en": {
                "Belum Diselesaikan": "Pending",
                "Dalam Tindakan": "In Progress",
                "Telah Diselesaikan": "Completed",
                "Tertangguh": "Delayed",
            }
        }

        for d in report_data.get("defects", []):
            if d.get("status"):
                d["status"] = STATUS_MAP.get(language, {}).get(d["status"], d["status"])

        report = generate_ai_report(role, report_data, language)

        summary = report_data.get("ringkasan_statistik", {})

        total_defects = summary.get("jumlah_kecacatan", 0)
        pending_count = summary.get("belum_diselesaikan", 0)
        completed_count = summary.get("telah_diselesaikan", 0)

        if language == "en":
            correct_summary = (
                "Claim Summary:\n"
                f"Total Defects Reported: {total_defects}\n"
                f"Pending: {pending_count}\n"
                f"Completed: {completed_count}"
            )
        else:
            correct_summary = (
                "Ringkasan Tuntutan:\n"
                f"Jumlah Kecacatan Dilaporkan: {total_defects}\n"
                f"Belum Diselesaikan: {pending_count}\n"
                f"Telah Diselesaikan: {completed_count}"
            )

        report = re.sub(
            r"(Claim Summary:.*?)(?=\n[A-Z]|\Z)",
            correct_summary + "\n",
            report,
            flags=re.DOTALL
        )
        report = re.sub(
            r"(Ringkasan Tuntutan:.*?)(?=\n[A-Z]|\Z)",
            correct_summary + "\n",
            report,
            flags=re.DOTALL
        )

        if language == "en":
            report = (
                report
                .replace("Status: Belum Diselesaikan", "Status: Pending")
                .replace("Status: Dalam Tindakan", "Status: In Progress")
                .replace("Status: Telah Diselesaikan", "Status: Completed")
                .replace("Status: Tertangguh", "Status: Delayed")
                .replace("Keutamaan:", "Priority:")
                .replace("Priority: Tinggi", "Priority: High")
                .replace("Priority: Sederhana", "Priority: Medium")
                .replace("Priority: Rendah", "Priority: Low")
            )
        elif language == "ms":
            report = (
                report
                .replace("Status: Pending", "Status: Belum Diselesaikan")
                .replace("Status: In Progress", "Status: Dalam Tindakan")
                .replace("Status: Completed", "Status: Telah Diselesaikan")
                .replace("Status: Delayed", "Status: Tertangguh")
                .replace("Priority:", "Keutamaan:")
                .replace("Keutamaan: High", "Keutamaan: Tinggi")
                .replace("Keutamaan: Medium", "Keutamaan: Sederhana")
                .replace("Keutamaan: Low", "Keutamaan: Rendah")
            )

        if not report or len(report.strip()) < 50:
            raise Exception("AI generated empty or insufficient report")

        return jsonify({
            "generated_at": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            "role": role,
            "language": language,
            "report": report
        })

    except Exception as e:
        current_app.logger.error(f"AI Report Generation Failed: {str(e)}")
        error_message = str(e)
        if "quota" in error_message.lower() or "429" in error_message:
            error_details = "API rate limit exceeded. Please try again later."
        elif "401" in error_message or "api_key" in error_message.lower():
            error_details = "API key invalid or missing. Check your GROQ_API_KEY."
        elif "timeout" in error_message.lower():
            error_details = "Request timed out. Please try again."
        else:
            error_details = str(e)

        return jsonify({
            "error": "Failed to generate AI report",
            "details": error_details,
            "debug": str(e) if current_app.debug else None
        }), 500


# =================================================
# EXPORT PDF
# =================================================
@routes.route("/export_pdf", methods=["POST"])
def export_pdf():
    role = request.form.get("role", "Homeowner")
    language = request.form.get("language", "ms")
    ai_report_text = request.form.get("ai_report", "")
    
    user_id = request.form.get('user_id', type=int)
    project_id = request.form.get('project_id', type=int)

    data = fetch_defects_and_data_from_db(role, user_id, project_id)
    return export_pdf_internal(role, language, ai_report_text, data)


def export_pdf_internal(role, language, ai_report_text, data):
    import hashlib
    from datetime import datetime
    
    hash_input = f"{data['maklumat_kes'].get('no_tuntutan', 'NO_ID')}_{datetime.now().isoformat()}".encode('utf-8')
    digital_hash = hashlib.sha256(hash_input).hexdigest()[:16].upper()

    labels = PDF_LABELS.get(language, PDF_LABELS["ms"])
    
    defects = data["defects"]
    stats = data["stats"]
    maklumat_kes = data["maklumat_kes"]
    pihak_yang_menuntut = data["pihak_yang_menuntut"]
    penentang = data["penentang"]

    remarks_store = load_remarks()
    status_store = load_status()

    for d in defects:
        d["status"] = status_store.get(str(d["id"]), d["status"])
        d["remarks"] = remarks_store.get(str(d["id"]), d["remarks"])
        if "urgency" in d and not d.get("priority"):
            d["priority"] = d["urgency"]

    for d in defects:
        d["_status_raw"] = d["status"]

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

    # Build report data for AI or mapping if used
    def build_summary_stats(s):
        return {
            "jumlah_kecacatan": s.get("total", 0),
            "belum_diselesaikan": s.get("pending", 0),
            "telah_diselesaikan": s.get("completed", 0),
            "kritikal": s.get("critical", 0)
        }
            
    def build_role_context(r, lang):
        if r == "Homeowner":
            return {
                "tajuk_laporan": "BORANG 1 - PERNYATAAN TUNTUTAN" if lang == "ms" else "FORM 1 - STATEMENT OF CLAIM",
                "tujuan": "Laporan ini disediakan bagi merumuskan kecacatan yang berlaku dalam tempoh Defect Liability Period (DLP) untuk rujukan Tribunal."
            }
        if r == "Developer":
            return {
                "tajuk_laporan": "LAPORAN PEMATUHAN DLP" if lang == "ms" else "DLP COMPLIANCE REPORT",
                "tujuan": "Laporan ini disediakan untuk menunjukkan status pembaikan dan pematuhan pemaju terhadap kecacatan yang dilaporkan."
            }
        return {
            "tajuk_laporan": "LAPORAN RUJUKAN TRIBUNAL DLP" if lang == "ms" else "TRIBUNAL REFERENCE REPORT (DLP)",
            "tujuan": "Laporan ini disediakan sebagai gambaran keseluruhan status kecacatan dan pematuhan untuk rujukan Tribunal."
        }

    report_data = {
        "maklumat_kes": maklumat_kes,
        "pihak_yang_menuntut": pihak_yang_menuntut,
        "penentang": penentang,
        "konteks_peranan": build_role_context(role, language),
        "ringkasan_statistik": build_summary_stats(stats),
        "senarai_kecacatan": build_defect_list(defects, role),
        "nota_penting": "Laporan ini dijana oleh sistem sebagai dokumen sokongan kepada Borang 1 Tribunal Tuntutan Pengguna Malaysia (TTPM)."
    }

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

    if role != "Homeowner":
        for d in defects:
            d["remarks"] = ""

    PRIORITY_MAP = {
        "ms": { "High": "Tinggi", "Medium": "Sederhana", "Low": "Rendah", },
        "en": { "Tinggi": "High", "Sederhana": "Medium", "Rendah": "Low", }
    }
    for d in defects:
        if d.get("priority"):
            d["priority"] = PRIORITY_MAP.get(language, {}).get(d["priority"], d["priority"])

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    evidence_dir = os.path.join(current_app.root_path, "evidence")
    os.makedirs(evidence_dir, exist_ok=True)

    # PAGE 1
    if role == "Homeowner":
        pdf.setFont("Helvetica-Bold", 11)
        if language == "en":
            pdf.drawCentredString(width/2, height - 40, "CONSUMER PROTECTION ACT 1999")
            pdf.setFont("Helvetica-Bold", 10)
            pdf.drawCentredString(width/2, height - 55, "CONSUMER PROTECTION REGULATIONS")
            pdf.drawCentredString(width/2, height - 68, "(CONSUMER CLAIMS TRIBUNAL) 1999")
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
            pdf.drawCentredString(width/2, height - 55, "PERATURAN-PERATURAN PERLINDUNGAN PENGGUNA")
            pdf.drawCentredString(width/2, height - 68, "(TRIBUNAL TUNTUTAN PENGGUNA) 1999")
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
        if language == "en":
            pdf.drawCentredString(width/2, y, f"AT  {report_data['maklumat_kes']['lokasi_tribunal']}".upper())
            y -= 20
            pdf.drawCentredString(width/2, y, f"IN THE STATE OF {report_data['maklumat_kes']['negeri']}, MALAYSIA".upper())
            y -= 20
            pdf.drawString(50, y, f"CLAIM NO.: {report_data['maklumat_kes']['no_tuntutan']}")
        else:
            pdf.drawCentredString(width/2, y, f"DI  {report_data['maklumat_kes']['lokasi_tribunal']}".upper())
            y -= 20
            pdf.drawCentredString(width/2, y, f"DI NEGERI {report_data['maklumat_kes']['negeri']}, MALAYSIA".upper())
            y -= 20
            pdf.drawString(50, y, f"TUNTUTAN NO.: {report_data['maklumat_kes']['no_tuntutan']}")

        y -= 40
        pdf.setFont("Helvetica-Bold", 10)
        if language == "en":
            pdf.drawString(50, y, "CLAIMANT")
        else:
            pdf.drawString(50, y, "PIHAK YANG MENUNTUT")

        box_x = 50
        box_y = y - 120
        box_width = width - 100
        box_height = 110
        pdf.rect(box_x, box_y, box_width, box_height)

        y -= 20
        pdf.setFont("Helvetica", 9)
        claimant = report_data['pihak_yang_menuntut']
        if language == "en":
            pdf.drawString(60, y, "Claimant Name")
            pdf.drawString(200, y, f": {claimant.get('nama', '')}")
            y -= 18
            pdf.drawString(60, y, "IC/Passport No.")
            pdf.drawString(200, y, f": {claimant.get('no_kp', '')}")
            y -= 18
            pdf.drawString(60, y, "Correspondence Address")
            pdf.drawString(200, y, f": {claimant.get('alamat_1', '')}")
            y -= 15
            pdf.drawString(200, y, f"  {claimant.get('alamat_2', '')}")
            y -= 18
            pdf.drawString(60, y, "Phone No.")
            pdf.drawString(200, y, f": {claimant.get('no_telefon', '')}")
            y -= 18
            pdf.drawString(60, y, "Fax/Email")
            pdf.drawString(200, y, f": {claimant.get('email', '')}")
        else:
            pdf.drawString(60, y, "Nama Pihak Yang Menuntut")
            pdf.drawString(200, y, f": {claimant.get('nama', '')}")
            y -= 18
            pdf.drawString(60, y, "No. Kad Pengenalan/Pasport")
            pdf.drawString(200, y, f": {claimant.get('no_kp', '')}")
            y -= 18
            pdf.drawString(60, y, "Alamat Surat Menyurat")
            pdf.drawString(200, y, f": {claimant.get('alamat_1', '')}")
            y -= 15
            pdf.drawString(200, y, f"  {claimant.get('alamat_2', '')}")
            y -= 18
            pdf.drawString(60, y, "No. Telefon")
            pdf.drawString(200, y, f": {claimant.get('no_telefon', '')}")
            y -= 18
            pdf.drawString(60, y, "No. Faks/ E-mel")
            pdf.drawString(200, y, f": {claimant.get('email', '')}")

        y -= 35
        pdf.setFont("Helvetica-Bold", 10)
        if language == "en":
            pdf.drawString(50, y, "RESPONDENT")
        else:
            pdf.drawString(50, y, "PENENTANG")

        box_top = y - 10
        box_height = 170
        pdf.rect(box_x, box_top - box_height, box_width, box_height)

        y -= 22
        pdf.setFont("Helvetica", 9)
        respondent = report_data['penentang']
        if language == "en":
            pdf.drawString(60, y, "Respondent/Company Name")
            pdf.drawString(200, y, f": {respondent.get('nama', '')}")
            y -= 18
            pdf.drawString(60, y, "IC/Company Registration No.")
            pdf.drawString(200, y, f": {respondent.get('no_pendaftaran', '')}")
            y -= 18
            pdf.drawString(60, y, "Correspondence Address")
            pdf.drawString(200, y, f": {respondent.get('alamat_1', '')}")
            y -= 12
            pdf.drawString(200, y, f"  {respondent.get('alamat_2', '')}")
            y -= 16
            pdf.drawString(60, y, "Phone No.")
            pdf.drawString(200, y, f": {respondent.get('no_telefon', '')}")
            y -= 16
            pdf.drawString(60, y, "Fax/Email")
            pdf.drawString(200, y, f": {respondent.get('email', '')}")
        else:
            pdf.drawString(60, y, "Nama Penentang/Syarikat/")
            pdf.drawString(200, y, f": {respondent.get('nama', '')}")
            y -= 12
            pdf.drawString(60, y, "Pertubuhan Perbadanan/Firma")
            y -= 18
            pdf.drawString(60, y, "No. Kad Pengenalan/")
            pdf.drawString(200, y, f": {respondent.get('no_pendaftaran', '')}")
            y -= 12
            pdf.drawString(60, y, "No. Pendaftaran Syarikat/")
            y -= 12
            pdf.drawString(60, y, "Pertubuhan Perbadanan/Firma")
            y -= 18
            pdf.drawString(60, y, "Alamat Surat Menyurat")
            pdf.drawString(200, y, f": {respondent.get('alamat_1', '')}")
            y -= 12
            pdf.drawString(200, y, f"  {respondent.get('alamat_2', '')}")
            y -= 16
            pdf.drawString(60, y, "No. Telefon")
            pdf.drawString(200, y, f": {respondent.get('no_telefon', '')}")
            y -= 16
            pdf.drawString(60, y, "No. Faks/E-mel")
            pdf.drawString(200, y, f": {respondent.get('email', '')}")

        y = box_top - box_height - 20
        pdf.setFont("Helvetica-Bold", 10)
        if language == "en":
            pdf.drawString(50, y, "STATEMENT OF CLAIM")
            y -= 20
            pdf.setFont("Helvetica", 9)
            pdf.drawString(50, y, "The Claimant's claim is for the amount of RM:")
            pdf.drawString(280, y, f"{report_data['maklumat_kes']['amaun_tuntutan']}")
        else:
            pdf.drawString(50, y, "PERNYATAAN TUNTUTAN")
            y -= 20
            pdf.setFont("Helvetica", 9)
            pdf.drawString(50, y, "Tuntutan Pihak Yang Menuntut ialah untuk jumlah RM:")
            pdf.drawString(280, y, f"{report_data['maklumat_kes']['amaun_tuntutan']}")

        y -= 30
        pdf.setFont("Helvetica-Bold", 10)
        if language == "en":
            pdf.drawString(50, y, "Claim Details")
        else:
            pdf.drawString(50, y, "Butir-butir Tuntutan")

        box_top = y - 10
        box_height = 60
        pdf.rect(50, box_top - box_height, width - 100, box_height)
        y -= 20
        pdf.setFont("Helvetica", 9)
        if language == "en":
            pdf.drawString(60, y, "Goods/Services")
            pdf.drawString(200, y, ": Defect Repairs During DLP Period")
            y -= 15
            pdf.drawString(60, y, "Date of Purchase/Transaction")
            pdf.drawString(200, y, f": {report_data['maklumat_kes']['tarikh_jana']}")
            y -= 15
            pdf.drawString(60, y, "Amount Paid")
            pdf.drawString(200, y, f": {report_data['maklumat_kes']['amaun_tuntutan']}")
        else:
            pdf.drawString(60, y, "Barangan/Perkhidmatan")
            pdf.drawString(200, y, ": Pembaikan Kecacatan Dalam Tempoh DLP")
            y -= 15
            pdf.drawString(60, y, "Tarikh Pembelian/ Transaksi")
            pdf.drawString(200, y, f": {report_data['maklumat_kes']['tarikh_jana']}")
            y -= 15
            pdf.drawString(60, y, "Jumlah yang dibayar")
            pdf.drawString(200, y, f": {report_data['maklumat_kes']['amaun_tuntutan']}")

        # PAGE 2
        draw_footer(pdf, width, labels, digital_hash)
        pdf.showPage()
        y = height - 50
    else:
        pdf.setFont("Helvetica-Bold", 14)
        if role == "Developer":
            title = "DLP COMPLIANCE REPORT" if language == "en" else "LAPORAN PEMATUHAN DLP"
        else:
            title = "TRIBUNAL REFERENCE REPORT (DLP)" if language == "en" else "LAPORAN RUJUKAN TRIBUNAL DLP"
        pdf.drawCentredString(width/2, height - 50, title)
        
        pdf.setFont("Helvetica", 10)
        if language == "en":
            pdf.drawCentredString(width/2, height - 70, f"Generated Date: {report_data['maklumat_kes']['tarikh_jana']}")
            pdf.drawCentredString(width/2, height - 85, f"Claim No: {report_data['maklumat_kes']['no_tuntutan']} | Location: {report_data['maklumat_kes']['lokasi_tribunal']}")
        else:
            pdf.drawCentredString(width/2, height - 70, f"Tarikh Jana: {report_data['maklumat_kes']['tarikh_jana']}")
            pdf.drawCentredString(width/2, height - 85, f"No. Tuntutan: {report_data['maklumat_kes']['no_tuntutan']} | Lokasi: {report_data['maklumat_kes']['lokasi_tribunal']}")
            
        y = height - 120

    pdf.setFont("Helvetica-Bold", 10)
    if language == "en":
        pdf.drawString(50, y, "Claim Summary:")
    else:
        pdf.drawString(50, y, "Ringkasan Tuntutan:")

    box_top = y - 10
    box_height = 80
    pdf.rect(50, box_top - box_height, width - 100, box_height)
    y -= 25
    pdf.setFont("Helvetica", 9)
    summary = report_data['ringkasan_statistik']
    if language == "en":
        pdf.drawString(60, y, f"Total Defects Reported: {summary['jumlah_kecacatan']}")
        y -= 15
        pdf.drawString(60, y, f"Pending: {summary['belum_diselesaikan']}")
        y -= 15
        pdf.drawString(60, y, f"Completed: {summary['telah_diselesaikan']}")
    else:
        pdf.drawString(60, y, f"Jumlah Kecacatan Dilaporkan: {summary['jumlah_kecacatan']}")
        y -= 15
        pdf.drawString(60, y, f"Belum Diselesaikan: {summary['belum_diselesaikan']}")
        y -= 15
        pdf.drawString(60, y, f"Telah Diselesaikan: {summary['telah_diselesaikan']}")

    y = box_top - box_height - 20

    # Defect List
    y -= 35
    pdf.setFont("Helvetica-Bold", 10)
    if language == "en":
        pdf.drawString(50, y, "Defect List:")
    else:
        pdf.drawString(50, y, "Senarai Kecacatan:")

    y -= 20
    pdf.setFont("Helvetica", 9)

    for i, defect in enumerate(defects, 1):
        if y < 260:
            draw_footer(pdf, width, labels, digital_hash)
            pdf.showPage()
            y = height - 50
            pdf.setFont("Helvetica-Bold", 10)
            if language == "en":
                pdf.drawString(50, y, "Defect List (continued):")
            else:
                pdf.drawString(50, y, "Senarai Kecacatan (sambungan):")
            y -= 30

        HEADER_X = 50
        LABEL_X  = 70
        VALUE_X  = 120
        TEXT_WIDTH = width - VALUE_X - 50
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(HEADER_X, y, f"{chr(64+i)}. {labels['defect_id']} {defect['id']}:")
        y -= 16

        pdf.setFont("Helvetica", 9)
        pdf.drawString(LABEL_X, y, labels["description"])
        y = draw_wrapped_text(pdf, f": {defect['desc']}", VALUE_X, y, TEXT_WIDTH)

        pdf.drawString(LABEL_X, y, labels["unit"])
        pdf.drawString(VALUE_X, y, f": {defect['unit']}")
        y -= 14

        pdf.drawString(LABEL_X, y, labels["status"])
        pdf.drawString(VALUE_X, y, f": {defect['status']}")
        y -= 14

        if defect.get("priority"):
            pdf.drawString(LABEL_X, y, labels["priority"])
            pdf.drawString(VALUE_X, y, f": {defect['priority']}")
            y -= 14

        if role == "Homeowner" and defect.get("remarks"):
            pdf.drawString(LABEL_X, y, labels["remarks"])
            y = draw_wrapped_text(pdf, f": {defect['remarks']}", VALUE_X, y, TEXT_WIDTH)

        image_path = None
        # Try local static directory if image_path exists in data
        if defect.get('image_path'):
            image_path_candidate = os.path.join("/usr/src/app_main/app/static/", defect['image_path'].lstrip('/'))
            if os.path.exists(image_path_candidate):
                 image_path = image_path_candidate

        # Fallback to evidence dir
        if not image_path:
             alt_image = os.path.join(evidence_dir, f"defect_{defect['id']}.jpg")
             if os.path.exists(alt_image):
                 image_path = alt_image
                 
        if image_path:
            if y < 180:
                draw_footer(pdf, width, labels, digital_hash)
                pdf.showPage()
                y = height - 50

            pdf.setFont("Helvetica-Oblique", 8)
            pdf.drawString(LABEL_X, y, f"{labels['evidence']}:")
            y -= 10
            pdf.drawImage(ImageReader(image_path), LABEL_X, y - 110, width=200, height=110, preserveAspectRatio=True)
            y -= 125
        else:
            pdf.setFont("Helvetica-Oblique", 8)
            pdf.drawString(LABEL_X, y, f"{labels['evidence']}")
            pdf.drawString(VALUE_X, y, ": Image Not Found")
            y -= 10

        y -= 25

    # AI REPORT SECTION
    if ai_report_text:
        draw_footer(pdf, width, labels, digital_hash)
        pdf.showPage()
        y = height - 50

        LEFT_MARGIN = 50
        PARAGRAPH_INDENT = 70
        RIGHT_MARGIN = width - 50
        LINE_HEIGHT = 18
        TEXT_WIDTH = RIGHT_MARGIN - PARAGRAPH_INDENT

        pdf.setFont("Helvetica-Bold", 12)
        if language == "en":
            pdf.drawCentredString(width/2, y, "AI-GENERATED CLAIM SUMMARY REPORT")
        else:
            pdf.drawCentredString(width/2, y, "LAPORAN RINGKASAN TUNTUTAN DIJANA AI")
        y -= 30

        clean_text = ai_report_text
        clean_text = clean_text.replace('**', '').replace('*', '').replace('##', '').replace('#', '').replace('\r\n', '\n').replace('\r', '\n')
        clean_text = re.sub(r'[^\x00-\x7F]+', '', clean_text)
        if language == "en":
            clean_text = clean_text.replace("Status: Telah Diselesaikan", "Status: Completed").replace("Status: Belum Diselesaikan", "Status: Pending").replace("Status: Dalam Tindakan", "Status: In Progress").replace("Status: Tertangguh", "Status: Delayed")
            clean_text = clean_text.replace("Keutamaan:", "Priority:").replace("Priority: Tinggi", "Priority: High").replace("Priority: Sederhana", "Priority: Medium").replace("Priority: Rendah", "Priority: Low")
        elif language == "ms":
            clean_text = clean_text.replace("Status: Completed", "Status: Telah Diselesaikan").replace("Status: Pending", "Status: Belum Diselesaikan").replace("Status: In Progress", "Status: Dalam Tindakan").replace("Status: Delayed", "Status: Tertangguh")
            clean_text = clean_text.replace("Priority:", "Keutamaan:").replace("Keutamaan: High", "Keutamaan: Tinggi").replace("Keutamaan: Medium", "Keutamaan: Sederhana").replace("Keutamaan: Low", "Keutamaan: Rendah")

        if language == "ms":
            for defect in defects:
                if defect.get("remarks"): clean_text = clean_text.replace("Ulasan:", "Ulasan:")
        elif language == "en":
            for defect in defects:
                if defect.get("remarks"): clean_text = clean_text.replace("Remarks:", "Remarks:")

        lines = clean_text.split('\n')
        prev_line_is_sub_item = False

        for line in lines:
            if not line.strip():
                y -= 8
                prev_line_is_sub_item = False
                continue
            if y < 80:
                draw_footer(pdf, width, labels, digital_hash)
                pdf.showPage()
                y = height - 50

            stripped = line.strip()
            if stripped[:2].isdigit() and stripped[1] == ".": y -= 12
            if stripped[:2] in ["A.", "B.", "C.", "D.", "E.", "F."]: y -= 8
            if stripped.startswith("Tarikh siap") or stripped.startswith("Tarikh dijadualkan") or stripped.startswith("Tarikh Siap"): y -= 10

            is_numbered_header = stripped.startswith(('1.', '2.', '3.', '4.', '5.', '6.', 'PENAFIAN AI', 'Penafian AI', 'AI Disclaimer', 'Laporan Sokongan', 'Laporan Pematuhan', 'Laporan Gambaran', 'Purpose of the Report', 'Summary of Reported Defects', 'Defect List', 'Defects That Have Exceeded', 'Formal Request', 'Conclusion', 'Tribunal Support Report'))
            is_sub_item = stripped.startswith(('A.', 'B.', 'C.', 'D.', 'E.', 'F.', 'a.', 'b.', 'c.', 'd.', 'e.', 'f.'))
            is_defect_field = stripped.startswith(("Keterangan:", "Unit:", "Status:", "Keutamaan:", "Ulasan:", "Description:", "Priority:", "Remarks:", "Tarikh siap:", "Tarikh Siap:", "Completion Date:", "Current Status:", "Scheduled Completion Date:"))

            if is_numbered_header:
                pdf.setFont("Helvetica-Bold", 10)
                x_pos = LEFT_MARGIN
            elif is_sub_item:
                pdf.setFont("Helvetica-Bold", 9)
                x_pos = LEFT_MARGIN + 20
            else:
                pdf.setFont("Helvetica", 9)
                if is_defect_field: x_pos = LEFT_MARGIN + 40
                else: x_pos = PARAGRAPH_INDENT

            prev_line_is_sub_item = is_sub_item
            words = stripped.split()
            current_line = ""

            for word in words:
                test_line = current_line + " " + word if current_line else word
                if pdf.stringWidth(test_line, "Helvetica", 9) <= TEXT_WIDTH:
                    current_line = test_line
                else:
                    if is_numbered_header: pdf.drawString(x_pos, y, current_line)
                    else: draw_justified_line(pdf, current_line, x_pos, y, TEXT_WIDTH, "Helvetica", 9)
                    y -= LINE_HEIGHT
                    if y < 80:
                        draw_footer(pdf, width, labels, digital_hash)
                        pdf.showPage()
                        y = height - 50
                        pdf.setFont("Helvetica", 9)
                    current_line = word

            if current_line:
                pdf.drawString(x_pos, y, current_line)
                y -= LINE_HEIGHT

    # SIGNATURE PAGE
    draw_footer(pdf, width, labels, digital_hash)
    pdf.showPage()
    y = height - 50

    pdf.setFont("Helvetica-Bold", 11)
    if language == "en":
        pdf.drawCentredString(width / 2, y, "Verification and Signature")
    else:
        pdf.drawCentredString(width / 2, y, "Pengesahan dan Tandatangan")
    
    y -= 90
    pdf.setFont("Helvetica", 9)

    short_line = "." * 55
    long_line = "." * 90
    short_width = pdf.stringWidth(short_line, "Helvetica", 9)
    long_width = pdf.stringWidth(long_line, "Helvetica", 9)
    left_x = 50
    right_x = width - 50 - long_width
    left_center = left_x + (short_width / 2)
    right_center = right_x + (long_width / 2)

    pdf.drawString(left_x, y, short_line)
    pdf.drawString(right_x, y, long_line)
    y -= 20
    if language == "en":
        pdf.drawCentredString(left_center, y, "Date")
        pdf.drawCentredString(right_center, y, "Signature/Thumbprint of Claimant")
    else:
        pdf.drawCentredString(left_center, y, "Tarikh")
        pdf.drawCentredString(right_center, y, "Tandatangan/Cap ibu jari Pihak Yang Menuntut")

    y -= 90
    pdf.drawString(left_x, y, short_line)
    pdf.drawString(right_x, y, long_line)
    y -= 20
    if language == "en":
        pdf.drawCentredString(left_center, y, "Filing Date")
        pdf.drawCentredString(right_center, y, "Secretary/Tribunal Officer")
    else:
        pdf.drawCentredString(left_center, y, "Tarikh Pemfailan")
        pdf.drawCentredString(right_center, y, "Setiausaha/Pegawai Tribunal")

    y -= 100
    pdf.setFont("Helvetica-Bold", 10)
    if language == "en":
        pdf.drawCentredString(width / 2, y, "(SEAL)")
    else:
        pdf.drawCentredString(width / 2, y, "(METERAI)")

    draw_footer(pdf, width, labels, digital_hash)
    pdf.save()
    buffer.seek(0)

    if role == "Legal": filename = labels["legal_filename"]
    elif role == "Developer": filename = labels["developer_filename"]
    else: filename = labels["homeowner_filename"]

    return send_file(buffer, as_attachment=True, download_name=filename, mimetype="application/pdf")
