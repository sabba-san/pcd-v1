from flask import (
    Blueprint,
    render_template,
    send_file,
    request,
    current_app,
    jsonify
)

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

from io import BytesIO
from datetime import datetime
# from werkzeug.utils import secure_filename
import os
import json
import re

# --------------------------------
# IMPORT DATA & SERVICES
# --------------------------------
from config_pdf_labels import PDF_LABELS
from dummy_data import get_defects_for_role, calculate_stats
from report_data import build_report_data
from report_generator import generate_ai_report
# from prompts import get_language_config
from ai_translate_cached import (
    translate_defects_cached,
    translate_report_cached
)

# --------------------------------
# BLUEPRINT
# --------------------------------
routes = Blueprint("routes", __name__)

# --------------------------------
# IMAGE UPLOAD CONFIG
# --------------------------------
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --------------------------------
# FILE STORAGE
# --------------------------------
REMARKS_FILE = "remarks.json"
STATUS_FILE = "status.json"

def load_remarks():
    """
    Load all saved remarks from JSON file.
    If file does not exist yet, return empty dictionary.
    """
    if not os.path.exists(REMARKS_FILE):
        return {}
    with open(REMARKS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_remarks(data):
    """
    Save all remarks to JSON file.
    ensure_ascii=False allows Bahasa Malaysia text.
    """
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
    pdf.drawRightString(
        width - 50,
        25,
        f"{labels['page']} {pdf.getPageNumber()}"
    )

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

# =================================================
# DASHBOARD ROUTE (THIS MAKES THE UI OPEN)
# =================================================
@routes.route("/")
def dashboard():
    role = request.args.get("role", "Homeowner")

    defects = get_defects_for_role(role)
    remarks_store = load_remarks()
    status_store = load_status()

    for d in defects:
        # Status is shared across all roles
        d["status"] = status_store.get(str(d["id"]), d["status"])

        # Remarks are ONLY visible to Homeowner
        if role == "Homeowner":
            d["remarks"] = remarks_store.get(str(d["id"]), "")
        else:
            d["remarks"] = ""  # Hide remarks for Developer & Legal

    stats = calculate_stats(defects)

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
# UPLOAD EVIDENCE IMAGE
# =================================================
@routes.route("/upload_evidence", methods=["POST"])
def upload_evidence():
    """
    Upload evidence image for a specific defect.
    Images are stored in the evidence folder with naming: defect_{id}.jpg
    Only the uploader can see their uploaded images (privacy).
    """
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
        
        # Create evidence directory if not exists
        evidence_dir = os.path.join(current_app.root_path, "evidence")
        os.makedirs(evidence_dir, exist_ok=True)
        
        # Save file with defect ID naming convention
        filename = f"defect_{defect_id}.jpg"
        filepath = os.path.join(evidence_dir, filename)
        
        # Save the file
        file.save(filepath)
        
        return jsonify({
            "success": True,
            "message": f"Evidence uploaded for defect #{defect_id}",
            "filename": filename,
            "defect_id": defect_id
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =================================================
# GET EVIDENCE IMAGE
# =================================================
@routes.route("/evidence/<defect_id>")
def get_evidence(defect_id):
    """
    Retrieve evidence image for a specific defect.
    """
    evidence_dir = os.path.join(current_app.root_path, "evidence")
    filename = f"defect_{defect_id}.jpg"
    filepath = os.path.join(evidence_dir, filename)
    
    if os.path.exists(filepath):
        return send_file(filepath, mimetype='image/jpeg')
    else:
        return jsonify({"error": "Evidence not found"}), 404


# =================================================
# CHECK IF EVIDENCE EXISTS
# =================================================
@routes.route("/evidence_exists/<defect_id>")
def evidence_exists(defect_id):
    """
    Check if evidence image exists for a defect.
    """
    evidence_dir = os.path.join(current_app.root_path, "evidence")
    filename = f"defect_{defect_id}.jpg"
    filepath = os.path.join(evidence_dir, filename)
    
    return jsonify({
        "exists": os.path.exists(filepath),
        "defect_id": defect_id
    })

# =================================================
# ADD / SAVE REMARK (NOTE)
# =================================================
@routes.route("/add_remark", methods=["POST"])
def add_remark():
    data = request.get_json()
    role = data.get("role")

    # Only Homeowner is allowed to add remarks
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

# =================================================
# UPDATE STATUS (DEVELOPER)
# =================================================
@routes.route("/update_status", methods=["POST"])
def update_status():
    data = request.get_json()

    defect_id = str(data.get("id"))
    new_status = data.get("status")

    ALLOWED_STATUS = {
        "Pending",
        "In Progress",
        "Completed",
        "Delayed"
    }

    if not defect_id or new_status not in ALLOWED_STATUS:
        return jsonify({"message": "Invalid status"}), 400

    status_store = load_status()
    status_store[defect_id] = new_status
    save_status(status_store)

    return jsonify({"message": "Status updated successfully"})

# =================================================
# GENERATE AI REPORT (JSON)
# =================================================
@routes.route("/generate_ai_report", methods=["POST"])
def generate_ai_report_api():
    try:
        data = request.get_json(silent=True) or {}
        role = data.get("role", "Homeowner")
        language = data.get("language", "ms")

        defects = get_defects_for_role(role)
        remarks_store = load_remarks()
        status_store = load_status()

        for d in defects:
            d["status"] = status_store.get(str(d["id"]), d["status"])
            d["remarks"] = remarks_store.get(str(d["id"]), "")  # optional
            # NORMALISE urgency → priority (SEBELUM translate)
            if "urgency" in d and not d.get("priority"):
                d["priority"] = d["urgency"]

        # LOCK STATUS (BACKEND AUTHORITY)
        for d in defects:
            d["_status_raw"] = d["status"]

        # AI TRANSLATION (CACHE IKUT ROLE)
        defects = translate_defects_cached(
            defects,
            language=language,
            role=role
        )

        # ==========================================
        # FORCE REMARKS LANGUAGE CONSISTENTLY
        # (ONLY FOR AI REPORT, NOT PDF)
        # ==========================================
        if language == "ms":
            for d in defects:
                if d.get("remarks"):
                    d["remarks"] = translate_report_cached(
                        d["remarks"],
                        language="ms",
                        role=role
                    )
        elif language == "en":
            for d in defects:
                if d.get("remarks"):
                    d["remarks"] = translate_report_cached(
                        d["remarks"],
                        language="en",
                        role=role
                    )

        # RESTORE STATUS
        for d in defects:
            d["status"] = d.pop("_status_raw", d["status"])

        if role != "Homeowner":
            for d in defects:
                d["remarks"] = ""
        
        # =================================================
        # NORMALISE STATUS FOR STATISTICS (ALWAYS ENGLISH)
        # =================================================
        STATUS_NORMALISE = {
            "Belum Diselesaikan": "Pending",
            "Dalam Tindakan": "In Progress",
            "Telah Diselesaikan": "Completed",
            "Tertangguh": "Delayed",
        }

        for d in defects:
            if d.get("status") in STATUS_NORMALISE:
                d["status"] = STATUS_NORMALISE[d["status"]]

        # BUILD REPORT
        stats = calculate_stats(defects)
        report_data = build_report_data(role, defects, stats)

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
                d["status"] = STATUS_MAP.get(language, {}).get(
                    d["status"],
                    d["status"]
                )

        report = generate_ai_report(role, report_data, language)

        # PREPARE CORRECT CLAIM SUMMARY (BACKEND)
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

        import re
        # Replace ONLY the Claim Summary section in AI text
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

        # =================================================
        # FIX LANGUAGE MIXING IN AI REPORT PREVIEW (TEXT)
        # =================================================
        if language == "en":
            report = (
                report
                # STATUS
                .replace("Status: Belum Diselesaikan", "Status: Pending")
                .replace("Status: Dalam Tindakan", "Status: In Progress")
                .replace("Status: Telah Diselesaikan", "Status: Completed")
                .replace("Status: Tertangguh", "Status: Delayed")

                # PRIORITY
                .replace("Keutamaan:", "Priority:")
                .replace("Priority: Tinggi", "Priority: High")
                .replace("Priority: Sederhana", "Priority: Medium")
                .replace("Priority: Rendah", "Priority: Low")
            )

        elif language == "ms":
            report = (
                report
                # STATUS
                .replace("Status: Pending", "Status: Belum Diselesaikan")
                .replace("Status: In Progress", "Status: Dalam Tindakan")
                .replace("Status: Completed", "Status: Telah Diselesaikan")
                .replace("Status: Delayed", "Status: Tertangguh")

                # PRIORITY
                .replace("Priority:", "Keutamaan:")
                .replace("Keutamaan: High", "Keutamaan: Tinggi")
                .replace("Keutamaan: Medium", "Keutamaan: Sederhana")
                .replace("Keutamaan: Low", "Keutamaan: Rendah")
            )

        # Validate AI report is not empty
        if not report or len(report.strip()) < 50:
            raise Exception("AI generated empty or insufficient report")

        return jsonify({
            "generated_at": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            "role": role,
            "language": language,
            "report": report
        })

    except Exception as e:
        # DEBUG
        current_app.logger.error(f"AI Report Generation Failed: {str(e)}")
        
        # Provide more helpful error messages
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
# EXPORT PDF - BORANG 1 TTPM FORMAT WITH AI REPORT
# PDF EXPORT ROUTE
# =================================================
@routes.route("/export_pdf", methods=["POST"])
def export_pdf():
    role = request.form.get("role", "Homeowner")
    language = request.form.get("language", "ms")
    ai_report_text = request.form.get("ai_report", "")

    # Load language-specific labels
    labels = PDF_LABELS.get(language, PDF_LABELS["ms"])

    defects = get_defects_for_role(role)
    remarks_store = load_remarks()
    status_store = load_status()

    # LOAD DATA AND NORMALISE FIELDS
    for d in defects:
        # Load latest status from storage
        d["status"] = status_store.get(str(d["id"]), d["status"])

        # Load remarks (Homeowner only, filtered later)
        d["remarks"] = remarks_store.get(str(d["id"]), "")

        # Normalise urgency → priority if priority is missing
        if "urgency" in d and not d.get("priority"):
            d["priority"] = d["urgency"]

    # LOCK STATUS (BACKEND AUTHORITY)
    # Status must NEVER be modified by AI
    for d in defects:
        d["_status_raw"] = d["status"]  # Always English internally

    # TRANSLATE DEFECT TEXT (AI, CACHED)
    # Status is NOT translated here
    defects = translate_defects_cached(
        defects,
        language=language,
        role=role
    )

    # RESTORE ORIGINAL STATUS BEFORE STATS
    for d in defects:
        d["status"] = d.pop("_status_raw", d["status"])

    # =================================================
    # NORMALISE STATUS FOR STATISTICS (ALWAYS ENGLISH)
    # =================================================
    STATUS_NORMALISE = {
        "Belum Diselesaikan": "Pending",
        "Dalam Tindakan": "In Progress",
        "Telah Diselesaikan": "Completed",
        "Tertangguh": "Delayed",
    }

    for d in defects:
        if d.get("status") in STATUS_NORMALISE:
            d["status"] = STATUS_NORMALISE[d["status"]]

    # CALCULATE STATISTICS (STATUS MUST BE ENGLISH)
    stats = calculate_stats(defects)
    report_data = build_report_data(role, defects, stats)

    # TRANSLATE STATUS FOR PDF DISPLAY ONLY
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

    for d in defects:
        if d.get("status"):
            d["status"] = STATUS_MAP.get(language, {}).get(
                d["status"],
                d["status"]
            )

    # HIDE REMARKS FOR NON-HOMEOWNER ROLES
    if role != "Homeowner":
        for d in defects:
            d["remarks"] = ""

    # TRANSLATE PRIORITY FOR PDF DISPLAY
    PRIORITY_MAP = {
        "ms": {
            "High": "Tinggi",
            "Medium": "Sederhana",
            "Low": "Rendah",
        },
        "en": {
            "Tinggi": "High",
            "Sederhana": "Medium",
            "Rendah": "Low",
        }
    }

    for d in defects:
        if d.get("priority"):
            d["priority"] = PRIORITY_MAP.get(language, {}).get(
                d["priority"],
                d["priority"]
            )

    # START PDF GENERATION
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # Ensure evidence directory exists
    evidence_dir = os.path.join(current_app.root_path, "evidence")
    os.makedirs(evidence_dir, exist_ok=True)

    # ============================================
    # PAGE 1: BORANG 1 HEADER & PARTIES
    # ============================================
    
    # --- HEADER (Centered) ---
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
    
    # --- Location & Case Number ---
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
    
    # --- PIHAK YANG MENUNTUT (Claimant) ---
    y -= 40
    pdf.setFont("Helvetica-Bold", 10)
    if language == "en":
        pdf.drawString(50, y, "CLAIMANT")
    else:
        pdf.drawString(50, y, "PIHAK YANG MENUNTUT")
    
    # Draw box for claimant details
    box_x = 50
    box_y = y - 120
    box_width = width - 100
    box_height = 110
    pdf.rect(box_x, box_y, box_width, box_height)
    
    # Claimant form fields
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
    
    # --- PENENTANG (Respondent/Developer) ---
    y -= 35
    pdf.setFont("Helvetica-Bold", 10)
    if language == "en":
        pdf.drawString(50, y, "RESPONDENT")
    else:
        pdf.drawString(50, y, "PENENTANG")
    
    # Draw box for respondent details - make it taller to fit all content
    box_top = y - 10
    box_height = 170
    pdf.rect(box_x, box_top - box_height, box_width, box_height)
    
    # Respondent form fields
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

    # Move y below the PENENTANG box
    y = box_top - box_height - 20
    
    # --- PERNYATAAN TUNTUTAN (Claim Amount) - on same page ---
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
    
    # --- BUTIR-BUTIR TUNTUTAN (Claim Details) ---
    y -= 30
    pdf.setFont("Helvetica-Bold", 10)
    if language == "en":
        pdf.drawString(50, y, "Claim Details")
    else:
        pdf.drawString(50, y, "Butir-butir Tuntutan")
    
    # Draw box for claim details - box starts below title
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

    # ============================================
    # PAGE 2: RINGKASAN & SENARAI KECACATAN
    # ============================================
    draw_footer(pdf, width, labels)
    pdf.showPage()
    y = height - 50
    
    # --- RINGKASAN TUNTUTAN (Claim Summary) ---
    pdf.setFont("Helvetica-Bold", 10)
    if language == "en":
        pdf.drawString(50, y, "Claim Summary:")
    else:
        pdf.drawString(50, y, "Ringkasan Tuntutan:")
    
    # Draw box for claim summary
    box_top = y - 10
    box_height = 80
    pdf.rect(50, box_top - box_height, width - 100, box_height)
    
    # Summary statistics inside the box
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
    
    # Move y below the box
    y = box_top - box_height - 20
    
    # --- SENARAI KECACATAN (Defect List) ---
    y -= 35
    pdf.setFont("Helvetica-Bold", 10)
    if language == "en":
        pdf.drawString(50, y, "Defect List:")
    else:
        pdf.drawString(50, y, "Senarai Kecacatan:")
    
    y -= 20
    pdf.setFont("Helvetica", 9)
    
    for i, defect in enumerate(defects, 1):

        # Ensure enough space for ONE full defect block
        if y < 260:
            draw_footer(pdf, width, labels)
            pdf.showPage()
            y = height - 50
            pdf.setFont("Helvetica-Bold", 10)
            if language == "en":
                pdf.drawString(50, y, "Defect List (continued):")
            else:
                pdf.drawString(50, y, "Senarai Kecacatan (sambungan):")
            y -= 30

        # ===============================
        # CONSISTENT INDENT POSITIONS
        # ===============================
        HEADER_X = 50      # a. Kecacatan ID
        LABEL_X  = 70      # Keterangan / Unit / Status
        VALUE_X  = 120     # isi selepas :
        TEXT_WIDTH = width - VALUE_X - 50

        # ===== DEFECT HEADER =====
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(
            HEADER_X,
            y,
            f"{chr(64+i)}. {labels['defect_id']} {defect['id']}:"
        )
        y -= 16

        pdf.setFont("Helvetica", 9)

        # ---- Keterangan ----
        desc_text = defect['desc']
        pdf.drawString(LABEL_X, y, labels["description"])
        y = draw_wrapped_text(
            pdf,
            f": {desc_text}",
            VALUE_X,
            y,
            TEXT_WIDTH
        )

        # ---- Unit ----
        pdf.drawString(LABEL_X, y, labels["unit"])
        pdf.drawString(VALUE_X, y, f": {defect['unit']}")
        y -= 14

        # ---- Status ----
        pdf.drawString(LABEL_X, y, labels["status"])
        status_text = defect["status"]
        pdf.drawString(VALUE_X, y, f": {status_text}")
        y -= 14

        # ---- Keutamaan (jika ada) ----
        if defect.get("priority"):
            pdf.drawString(LABEL_X, y, labels["priority"])
            pdf.drawString(VALUE_X, y, f": {defect['priority']}")
            y -= 14

        # ---- Ulasan (Homeowner sahaja) ----
        if role == "Homeowner" and defect.get("remarks"):
            pdf.drawString(LABEL_X, y, labels["remarks"])
            y = draw_wrapped_text(
                pdf,
                f": {defect['remarks']}",
                VALUE_X,
                y,
                TEXT_WIDTH
            )

        # ---- Bukti Kecacatan ----
        image_path = os.path.join(evidence_dir, f"defect_{defect['id']}.jpg")
        if os.path.exists(image_path):
            if y < 180:
                draw_footer(pdf, width, labels)
                pdf.showPage()
                y = height - 50

            pdf.setFont("Helvetica-Oblique", 8)
            pdf.drawString(LABEL_X, y, f"{labels['evidence']}:")
            y -= 10

            pdf.drawImage(
                ImageReader(image_path),
                LABEL_X,
                y - 110,
                width=200,
                height=110
            )
            y -= 125

        # Space between defects
        y -= 25

    # ============================================
    # AI REPORT SECTION (Ringkasan Tuntutan)
    # ============================================
    if ai_report_text:
        draw_footer(pdf, width, labels)
        pdf.showPage()
        y = height - 50

        # Margins & spacing
        LEFT_MARGIN = 50
        PARAGRAPH_INDENT = 70
        RIGHT_MARGIN = width - 50
        LINE_HEIGHT = 18
        TEXT_WIDTH = RIGHT_MARGIN - PARAGRAPH_INDENT

        # AI Report Header
        pdf.setFont("Helvetica-Bold", 12)
        if language == "en":
            pdf.drawCentredString(width/2, y, "AI-GENERATED CLAIM SUMMARY REPORT")
        else:
            pdf.drawCentredString(width/2, y, "LAPORAN RINGKASAN TUNTUTAN DIJANA AI")

        y -= 30

        # Clean AI report text
        import re
        clean_text = ai_report_text
        clean_text = clean_text.replace('**', '')
        clean_text = clean_text.replace('*', '')
        clean_text = clean_text.replace('##', '')
        clean_text = clean_text.replace('#', '')
        clean_text = clean_text.replace('\r\n', '\n')
        clean_text = clean_text.replace('\r', '\n')
        clean_text = re.sub(r'[^\x00-\x7F]+', '', clean_text)
        # TRANSLATE PRIORITY INSIDE AI REPORT TEXT
        if language == "en":
            # Force ALL status to English
            clean_text = clean_text.replace("Status: Telah Diselesaikan", "Status: Completed")
            clean_text = clean_text.replace("Status: Belum Diselesaikan", "Status: Pending")
            clean_text = clean_text.replace("Status: Dalam Tindakan", "Status: In Progress")
            clean_text = clean_text.replace("Status: Tertangguh", "Status: Delayed")

            # Priority
            clean_text = clean_text.replace("Keutamaan:", "Priority:")
            clean_text = clean_text.replace("Priority: Tinggi", "Priority: High")
            clean_text = clean_text.replace("Priority: Sederhana", "Priority: Medium")
            clean_text = clean_text.replace("Priority: Rendah", "Priority: Low")

        elif language == "ms":
            # Force ALL status to Bahasa Malaysia
            clean_text = clean_text.replace("Status: Completed", "Status: Telah Diselesaikan")
            clean_text = clean_text.replace("Status: Pending", "Status: Belum Diselesaikan")
            clean_text = clean_text.replace("Status: In Progress", "Status: Dalam Tindakan")
            clean_text = clean_text.replace("Status: Delayed", "Status: Tertangguh")

            # Priority
            clean_text = clean_text.replace("Priority:", "Keutamaan:")
            clean_text = clean_text.replace("Keutamaan: High", "Keutamaan: Tinggi")
            clean_text = clean_text.replace("Keutamaan: Medium", "Keutamaan: Sederhana")
            clean_text = clean_text.replace("Keutamaan: Low", "Keutamaan: Rendah")

        # =================================================
        # FIX REMARKS LANGUAGE USING DEFECT DATA (AUTHORITATIVE)
        # =================================================
        if language == "ms":
            for defect in defects:
                if defect.get("remarks"):
                    clean_text = clean_text.replace(
                        "Ulasan:",
                        "Ulasan:"
                    )

        elif language == "en":
            for defect in defects:
                if defect.get("remarks"):
                    clean_text = clean_text.replace(
                        "Remarks:",
                        "Remarks:"
                    )

        # Split AI report into lines
        lines = clean_text.split('\n')

        prev_line_is_sub_item = False

        for line in lines:
            # Empty line spacing
            if not line.strip():
                y -= 8
                prev_line_is_sub_item = False
                continue

            # Page break
            if y < 80:
                draw_footer(pdf, width, labels)
                pdf.showPage()
                y = height - 50

            stripped = line.strip()

            # -----------------------------------------
            # FORMAL SPACING RULES (TRIBUNAL-GRADE)
            # -----------------------------------------

            # Extra space before numbered sections (2., 3., etc.)
            if stripped[:2].isdigit() and stripped[1] == ".":
                y -= 12   # space before new main section

            # Extra space before lettered items (A., B., C.)
            if stripped[:2] in ["A.", "B.", "C.", "D.", "E.", "F."]:
                y -= 8    # space before each defect item

            # Extra space after finishing one defect block
            if stripped.startswith("Tarikh siap") or stripped.startswith("Tarikh dijadualkan") or stripped.startswith("Tarikh Siap"):
                y -= 10   # space after one defect

            # Detect headers (LEFT ALIGN ONLY)
            is_numbered_header = (
                stripped.startswith('1.') or
                stripped.startswith('2.') or
                stripped.startswith('3.') or
                stripped.startswith('4.') or
                stripped.startswith('5.') or
                stripped.startswith('6.') or
                stripped.startswith('PENAFIAN AI') or
                stripped.startswith('Penafian AI') or
                stripped.startswith('AI Disclaimer') or
                stripped.startswith('Laporan Sokongan') or
                stripped.startswith('Laporan Pematuhan') or
                stripped.startswith('Laporan Gambaran') or
                stripped.startswith('Purpose of the Report') or
                stripped.startswith('Summary of Reported Defects') or
                stripped.startswith('Defect List') or
                stripped.startswith('Defects That Have Exceeded') or
                stripped.startswith('Formal Request') or
                stripped.startswith('Conclusion') or
                stripped.startswith('Tribunal Support Report')
            )

            is_sub_item = (
                stripped.startswith('A.') or
                stripped.startswith('B.') or
                stripped.startswith('C.') or
                stripped.startswith('D.') or
                stripped.startswith('E.') or
                stripped.startswith('F.') or
                stripped.startswith('a.') or
                stripped.startswith('b.') or
                stripped.startswith('c.') or
                stripped.startswith('d.') or
                stripped.startswith('e.') or
                stripped.startswith('f.')
            )

            # Defect detail fields
            is_defect_field = stripped.startswith((
                "Keterangan:",
                "Unit:",
                "Status:",
                "Keutamaan:",
                "Ulasan:",
                "Description:",
                "Priority:",
                "Remarks:",
                "Tarikh siap:",
                "Tarikh Siap:",
                "Completion Date:",
                "Current Status:",
                "Scheduled Completion Date:"
            ))

            # Font & indent
            if is_numbered_header:
                pdf.setFont("Helvetica-Bold", 10)
                x_pos = LEFT_MARGIN
            elif is_sub_item:
                pdf.setFont("Helvetica-Bold", 9)
                x_pos = LEFT_MARGIN + 20
            else:
                pdf.setFont("Helvetica", 9)
                if is_defect_field:
                    x_pos = LEFT_MARGIN + 40
                else:
                    x_pos = PARAGRAPH_INDENT

            prev_line_is_sub_item = is_sub_item

            # ============================================
            # WORD WRAP + JUSTIFY (ISI PERENGGAN SAHAJA)
            # ============================================
            words = stripped.split()
            current_line = ""

            for word in words:
                test_line = current_line + " " + word if current_line else word
                if pdf.stringWidth(test_line, "Helvetica", 9) <= TEXT_WIDTH:
                    current_line = test_line
                else:
                    if is_numbered_header:
                        # Header → kiri sahaja
                        pdf.drawString(x_pos, y, current_line)
                    else:
                        # ISI → JUSTIFY DI SINI
                        draw_justified_line(
                            pdf,
                            current_line,
                            x_pos,
                            y,
                            TEXT_WIDTH,
                            "Helvetica",
                            9
                        )

                    y -= LINE_HEIGHT
                    if y < 80:
                        draw_footer(pdf, width, labels)
                        pdf.showPage()
                        y = height - 50
                        pdf.setFont("Helvetica", 9)

                    current_line = word

            # Last line (JANGAN justify – standard dokumen rasmi)
            if current_line:
                pdf.drawString(x_pos, y, current_line)
                y -= LINE_HEIGHT

    # ============================================
    # SIGNATURE & METERAI (HALAMAN BERASINGAN)
    # ============================================
    # Start signature on a new page (BEST PRACTICE)
    draw_footer(pdf, width, labels)
    pdf.showPage()
    y = height - 50

    # Title
    pdf.setFont("Helvetica-Bold", 11)
    if language == "en":
        pdf.drawCentredString(width / 2, y, "Verification and Signature")
    else:
        pdf.drawCentredString(width / 2, y, "Pengesahan dan Tandatangan")
    
    y -= 90

    # Signature section
    pdf.setFont("Helvetica", 9)

    # Left: short line for date
    short_line = "." * 55
    # Right: long line for signature
    long_line = "." * 90

    # Calculate widths
    short_width = pdf.stringWidth(short_line, "Helvetica", 9)
    long_width = pdf.stringWidth(long_line, "Helvetica", 9)

    # Positions - left starts at 50, right ends at width-50
    left_x = 50
    right_x = width - 50 - long_width

    # Centers for labels
    left_center = left_x + (short_width / 2)
    right_center = right_x + (long_width / 2)

    # Row 1: Tarikh + Tandatangan
    pdf.drawString(left_x, y, short_line)
    pdf.drawString(right_x, y, long_line)
    y -= 20
    if language == "en":
        pdf.drawCentredString(left_center, y, "Date")
        pdf.drawCentredString(right_center, y, "Signature/Thumbprint of Claimant")
    else:
        pdf.drawCentredString(left_center, y, "Tarikh")
        pdf.drawCentredString(right_center, y, "Tandatangan/Cap ibu jari Pihak Yang Menuntut")

    # Row spacing (lebih luas)
    y -= 90

    # Row 2: Tarikh Pemfailan + Setiausaha
    pdf.drawString(left_x, y, short_line)
    pdf.drawString(right_x, y, long_line)
    y -= 20
    if language == "en":
        pdf.drawCentredString(left_center, y, "Filing Date")
        pdf.drawCentredString(right_center, y, "Secretary/Tribunal Officer")
    else:
        pdf.drawCentredString(left_center, y, "Tarikh Pemfailan")
        pdf.drawCentredString(right_center, y, "Setiausaha/Pegawai Tribunal")

    # Meterai
    y -= 100
    pdf.setFont("Helvetica-Bold", 10)
    if language == "en":
        pdf.drawCentredString(width / 2, y, "(SEAL)")
    else:
        pdf.drawCentredString(width / 2, y, "(METERAI)")

    draw_footer(pdf, width, labels)
    pdf.save()
    buffer.seek(0)

    # Filename based on role
    if role == "Legal":
        filename = labels["legal_filename"]
    elif role == "Developer":
        filename = labels["developer_filename"]
    else:
        filename = labels["homeowner_filename"]

    return send_file(
        buffer,
        as_attachment=True,
        download_name=filename,
        mimetype="application/pdf"

)
