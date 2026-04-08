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
from app.models import TribunalClaim, Defect, Project, User

from .config_pdf_labels import PDF_LABELS
from .report_generator import generate_ai_report
from .ai_translate_cached import translate_defects_cached, translate_report_cached
from .report_data import build_defect_list

report_bp = Blueprint("report", __name__, url_prefix="/report")

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

REMARKS_FILE = "app/data/remarks.json"
STATUS_FILE = "app/data/status.json"

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

    IMPORTANT: pihak_yang_menuntut is ALWAYS the Homeowner/complainant.
               penentang is ALWAYS the Developer.
               These must never be swapped regardless of which role is logged in.
    """
    try:
        from flask_login import current_user
        if not user_id and current_user and current_user.is_authenticated:
            user_id = current_user.id
    except Exception:
        pass

    session_user = User.query.get(user_id) if user_id else None
    project = Project.query.get(project_id) if project_id else None

    # ── 1. Determine which defects to load ───────────────────────────────────
    if role == "Homeowner":
        if not session_user:
            defects_db = []
        else:
            project = project or session_user.project
            if project:
                defects_db = Defect.query.filter_by(user_id=user_id, project_id=project.id).all()
            else:
                defects_db = Defect.query.filter_by(user_id=user_id).all()
    else:
        # Developer / Legal: load all defects for the project
        if project:
            defects_db = Defect.query.filter_by(project_id=project.id).all()
        else:
            defects_db = Defect.query.all()

    # ── 2. Always resolve the HOMEOWNER (claimant) ───────────────────────────
    # homeowner_user is the actual Homeowner/complainant, regardless of who is logged in.
    homeowner_user = None

    if role == "Homeowner" and session_user and session_user.role in ('user', 'homeowner'):
        # Logged-in user IS the homeowner
        homeowner_user = session_user
    else:
        # Logged-in user is Developer/Legal – find the homeowner from defects or DB
        for d in defects_db:
            if d.user and d.user.role in ('user', 'homeowner'):
                homeowner_user = d.user
                break
        if not homeowner_user and project:
            homeowner_user = (
                User.query.filter_by(role='user', project_id=project.id).first() or
                User.query.filter_by(role='homeowner', project_id=project.id).first()
            )
        if not homeowner_user:
            # Last resort: any homeowner in the system
            homeowner_user = (
                User.query.filter_by(role='user').first() or
                User.query.filter_by(role='homeowner').first()
            )

    # ── 3. Always resolve the DEVELOPER (respondent) ─────────────────────────
    developer_user = None
    dev_id = request.args.get('dev_id', type=int)
    if dev_id:
        developer_user = User.query.get(dev_id)
    elif session_user and session_user.role == 'developer':
        # The logged-in user IS the developer
        developer_user = session_user
    else:
        if project and project.developer_name:
            developer_user = User.query.filter_by(role='developer', company_name=project.developer_name).first()
        if not developer_user and project:
            developer_user = User.query.filter_by(role='developer', project_id=project.id).first()
        if not developer_user:
            developer_user = User.query.filter_by(role='developer').first()

    # ── 4. Build defect list ─────────────────────────────────────────────────
    defects = []
    for d in defects_db:
        image_path = None
        if hasattr(d, 'images') and len(d.images) > 0:
            image_path = "/" + d.images[0].image_path.lstrip('/')

        # Unit number: prefer homeowner's unit, then defect location
        unit_val = "N/A"
        if homeowner_user and getattr(homeowner_user, 'unit_no', None) and str(homeowner_user.unit_no) != "None":
            unit_val = homeowner_user.unit_no
        elif getattr(d, 'location', None) and str(d.location) != "None":
            unit_val = d.location

        # HDA compliance: completed within 30 days of reported date
        hda_ok = True
        if d.reported_date and d.scheduled_date:
            from datetime import timedelta
            hda_ok = (d.scheduled_date - d.reported_date).days <= 30
        if d.status in ["Completed", "Fixed", "Telah Diselesaikan"]:
            actual = d.updated_at.date() if d.updated_at else None
            if actual and d.reported_date:
                hda_ok = (actual - d.reported_date).days <= 30
        else:
            hda_ok = True  # not yet completed, no breach yet

        defects.append({
            "id": d.id,
            "description": d.description or "No description",
            "unit": unit_val,
            "status": d.status or "Pending",
            "severity": d.severity or "Normal",
            "image_path": image_path,

            "project_name": project.name if project else "N/A",
            "full_name": homeowner_user.full_name if homeowner_user else "N/A",
            "desc": d.description or "No description",
            "priority": d.severity or "Normal",
            "urgency": d.severity or "Normal",
            "remarks": d.notes if hasattr(d, 'notes') and d.notes else "",

            # Date fields for defect table
            "reported_date":          d.reported_date,
            "scheduled_date":         d.scheduled_date,
            "deadline":               d.scheduled_date.strftime("%Y-%m-%d") if d.scheduled_date else "",
            "actual_completion_date": d.updated_at.date() if (d.updated_at and d.status in ["Completed", "Fixed", "Telah Diselesaikan"]) else None,

            "is_overdue": bool(d.scheduled_date and d.status not in ["Completed", "Fixed", "Telah Diselesaikan"] and d.scheduled_date < datetime.now().date()),
            "hda_compliant": hda_ok,
        })

    # ── 5. Stats ──────────────────────────────────────────────────────────────
    stats = {
        "total":     len(defects),
        "pending":   sum(1 for d in defects if d["status"] in ["Pending", "draft", "New", "Reported", "Belum Diselesaikan"]),
        "completed": sum(1 for d in defects if d["status"] in ["Completed", "Fixed", "Telah Diselesaikan"]),
        "critical":  sum(1 for d in defects if d["priority"] in ["High", "Tinggi"]),
    }

    # ── 6. Case / Tribunal info ───────────────────────────────────────────────
    # Use homeowner's tribunal city/state if available; fallback to defaults
    maklumat_kes = {
        "tribunal":          "Tribunal Tuntutan Pengguna Malaysia",
        "lokasi_tribunal":   getattr(homeowner_user, 'tribunal_city', None) or "Shah Alam",
        "no_tuntutan":       "TTPM/SGR/2026/000001",
        "tarikh_jana":       datetime.now().strftime("%d-%m-%Y"),
        "amaun_tuntutan":    "RM 0.00",
        "dokumen":           "Dokumen Sokongan Borang 1",
        "negeri":            getattr(homeowner_user, 'tribunal_state', None) or "Selangor",
    }

    # ── 7. CLAIMANT – always the Homeowner ───────────────────────────────────
    pihak_yang_menuntut = {
        "nama":        getattr(homeowner_user, 'full_name', None) or "N/A",
        "no_kp":       getattr(homeowner_user, 'ic_number', None) or "-",
        "alamat_1":    getattr(homeowner_user, 'correspondence_address', None) or "-",
        "alamat_2":    "-",
        "no_telefon":  getattr(homeowner_user, 'phone_number', None) or "-",
        "email":       getattr(homeowner_user, 'email', None) or "-",
        "keterangan":  "Pemilik unit kediaman",
    }

    # ── 8. RESPONDENT – always the Developer ─────────────────────────────────
    penentang_nama = "N/A"
    if developer_user and developer_user.company_name:
        penentang_nama = developer_user.company_name
    elif project and project.developer_name:
        penentang_nama = project.developer_name
    elif developer_user and developer_user.full_name:
        penentang_nama = developer_user.full_name

    penentang = {
        "nama":           penentang_nama,
        "no_pendaftaran": (getattr(developer_user, 'company_reg_no', None) or getattr(developer_user, 'nric', None) or "-") if developer_user else (getattr(project, 'developer_ssm', None) or "-"),
        "alamat_1":       getattr(developer_user, 'company_address', None) or (getattr(project, 'developer_address', None) or "-"),
        "alamat_2":       "-",
        "no_telefon":     getattr(developer_user, 'contact_number', None) or "-",
        "email":          getattr(developer_user, 'fax_email', None) or "-",
        "keterangan":     "Pemaju projek perumahan",
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
@report_bp.route("/")
@report_bp.route("/dashboard")
@report_bp.route("/dashboard/<int:project_id>")
def dashboard(project_id=None):
    from flask_login import current_user
    from flask import current_app, redirect, abort
    
    if not current_user or not current_user.is_authenticated:
        return redirect("http://localhost:5000/") # Or handle 401
    
    user_role = current_user.role.lower() if hasattr(current_user, 'role') else ''
    
    if user_role == 'homeowner' or user_role == 'user':
        role = "Homeowner"
    elif user_role == 'developer':
        role = "Developer"
    elif user_role in ['legal', 'lawyer']:
        role = "Legal"
    else:
        return "Unauthorized role.", 403
        
    user_id = current_user.id

    if project_id is None:
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

    total_defects = stats["total"]
    pending_defects = stats["pending"]
    resolved_defects = stats["completed"]

    if role == "Developer":
        return render_template('module3/dashboard_developer.html', role=role, defects=defects, stats=stats,
                               total_defects=total_defects, resolved_defects=resolved_defects, pending_defects=pending_defects)
    elif role == "Legal":
        return render_template('module3/dashboard_legal.html', role=role, defects=defects, stats=stats,
                               total_defects=total_defects, resolved_defects=resolved_defects, pending_defects=pending_defects)
    elif role == "Homeowner":
        return render_template('module3/dashboard_homeowner.html', role=role, defects=defects, stats=stats,
                               total_defects=total_defects, resolved_defects=resolved_defects, pending_defects=pending_defects)
    else:
        return "Unauthorized role.", 403


# =================================================
# ORIGINAL GENERATE REPORT API
# =================================================
@report_bp.route('/api/generate_report/<report_type>', methods=['GET'])
def generate_report_api_legacy(report_type):
    # This was originally `/api/generate_report/<report_type>`.
    # It acts identically to the original to prevent breakage.
    try:
        from flask_login import current_user
        if not current_user or not current_user.is_authenticated:
            return jsonify({"error": "Unauthorized"}), 403
            
        user_role = current_user.role.lower() if hasattr(current_user, 'role') else ''
        if user_role == 'homeowner' or user_role == 'user':
            role = "Homeowner"
        elif user_role == 'developer':
            role = "Developer"
        elif user_role in ['legal', 'lawyer']:
            role = "Legal"
        else:
            return jsonify({"error": "Unauthorized role"}), 403
            
        language = request.args.get('language', 'en')
        role_map = {
            "homeowner": "Homeowner",
            "developer": "Developer",
            "legal": "Legal"
        }
        requested_role = role_map.get(report_type.lower(), "Homeowner")
        
        if requested_role != role:
            return jsonify({"error": "Cannot generate report for a different role"}), 403

        user_id = current_user.id
        project_id = request.args.get('project_id', type=int)
        
        data = fetch_defects_and_data_from_db(role, user_id, project_id)
        
        # --- NEW CODE: Force AI Generation before building PDF ---
        ai_summary_text = ""
        try:
            # Build structures for AI model prompt
            def build_summary_stats(s):
                return {
                    "jumlah_kecacatan": s.get("total", 0),
                    "belum_diselesaikan": s.get("pending", 0),
                    "telah_diselesaikan": s.get("completed", 0),
                    "kritikal": s.get("critical", 0)
                }
            def build_role_context(r, lang):
                if r == "Homeowner":
                    return {"tajuk_laporan": "BORANG 1 - PERNYATAAN TUNTUTAN" if lang == "ms" else "FORM 1 - STATEMENT OF CLAIM", "tujuan": "Laporan ini disediakan bagi merumuskan kecacatan yang berlaku dalam tempoh Defect Liability Period (DLP) untuk rujukan Tribunal."}
                if r == "Developer":
                    return {"tajuk_laporan": "LAPORAN PEMATUHAN DLP" if lang == "ms" else "DLP COMPLIANCE REPORT", "tujuan": "Laporan ini disediakan untuk menunjukkan status pembaikan dan pematuhan pemaju terhadap kecacatan yang dilaporkan."}
                return {"tajuk_laporan": "LAPORAN RUJUKAN TRIBUNAL DLP" if lang == "ms" else "TRIBUNAL REFERENCE REPORT (DLP)", "tujuan": "Laporan ini disediakan sebagai gambaran keseluruhan status kecacatan dan pematuhan untuk rujukan Tribunal."}
            
            report_data = {
                "maklumat_kes": data['maklumat_kes'],
                "pihak_yang_menuntut": data['pihak_yang_menuntut'],
                "penentang": data['penentang'],
                "konteks_peranan": build_role_context(role, language),
                "ringkasan_statistik": build_summary_stats(data['stats']),
                "senarai_kecacatan": build_defect_list(data['defects'], role),
                "nota_penting": "Laporan ini dijana oleh sistem sebagai dokumen sokongan kepada Borang 1 Tribunal Tuntutan Pengguna Malaysia (TTPM)."
            }
            
            ai_summary_text = generate_ai_report(role, report_data, language)
            
            # Accurate stats patching
            summary = report_data.get("ringkasan_statistik", {})
            total_defects = summary.get("jumlah_kecacatan", 0)
            pending_count = summary.get("belum_diselesaikan", 0)
            completed_count = summary.get("telah_diselesaikan", 0)
            
            if language == "en":
                correct_summary = f"Claim Summary:\nTotal Defects Reported: {total_defects}\nPending: {pending_count}\nCompleted: {completed_count}"
            else:
                correct_summary = f"Ringkasan Tuntutan:\nJumlah Kecacatan Dilaporkan: {total_defects}\nBelum Diselesaikan: {pending_count}\nTelah Diselesaikan: {completed_count}"
            
            import re
            ai_summary_text = re.sub(r"(Claim Summary:.*?)(?=\n[A-Z]|\Z)", correct_summary + "\n", ai_summary_text, flags=re.DOTALL)
            ai_summary_text = re.sub(r"(Ringkasan Tuntutan:.*?)(?=\n[A-Z]|\Z)", correct_summary + "\n", ai_summary_text, flags=re.DOTALL)
            
            if not ai_summary_text or len(ai_summary_text.strip()) < 50:
                ai_summary_text = "Summary generation unavailable."
        except Exception as e:
            current_app.logger.error(f"Forced AI Generation Failed: {str(e)}")
            ai_summary_text = "Summary generation unavailable."

        return export_pdf_internal(role, language, ai_summary_text, data)

    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500


# =================================================
# EVIDENCE ENDPOINTS
# =================================================
@report_bp.route("/upload_evidence", methods=["POST"])
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

@report_bp.route("/evidence/<defect_id>")
def get_evidence(defect_id):
    evidence_dir = os.path.join(current_app.root_path, "evidence")
    filename = f"defect_{defect_id}.jpg"
    filepath = os.path.join(evidence_dir, filename)
    if os.path.exists(filepath):
        return send_file(filepath, mimetype='image/jpeg')
    return jsonify({"error": "Evidence not found"}), 404

@report_bp.route("/evidence_exists/<defect_id>")
def evidence_exists(defect_id):
    evidence_dir = os.path.join(current_app.root_path, "evidence")
    filename = f"defect_{defect_id}.jpg"
    filepath = os.path.join(evidence_dir, filename)
    return jsonify({
        "exists": os.path.exists(filepath),
        "defect_id": defect_id
    })

@report_bp.route("/add_remark", methods=["POST"])
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

@report_bp.route("/update_status", methods=["POST"])
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

@report_bp.route("/api/update_defect_date", methods=["POST"])
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
@report_bp.route("/generate_ai_report", methods=["POST"])
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
@report_bp.route("/export_pdf", methods=["POST"])
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
    from datetime import datetime, date
    from io import BytesIO as _BytesIO

    # ── Platypus imports ──────────────────────────────────────────────────────
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        PageBreak, KeepTogether, Image as RLImage
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.lib.pagesizes import A4 as _A4
    from reportlab.pdfbase import pdfmetrics

    _width, _height = _A4
    LEFT = 50
    RIGHT = _width - 50
    CONTENT_W = RIGHT - LEFT

    # ── Digital hash ─────────────────────────────────────────────────────────
    hash_input = f"{data['maklumat_kes'].get('no_tuntutan','NO_ID')}_{datetime.now().isoformat()}".encode()
    digital_hash = hashlib.sha256(hash_input).hexdigest()[:16].upper()

    labels     = PDF_LABELS.get(language, PDF_LABELS["ms"])
    defects    = data["defects"]
    stats      = data["stats"]
    maklumat_kes       = data["maklumat_kes"]
    pihak_yang_menuntut = data["pihak_yang_menuntut"]
    penentang          = data["penentang"]

    # ── Status / priority normalisation ──────────────────────────────────────
    remarks_store = load_remarks()
    status_store  = load_status()

    for d in defects:
        d["status"]   = status_store.get(str(d["id"]), d["status"])
        d["remarks"]  = remarks_store.get(str(d["id"]), d.get("remarks", ""))
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
        "Tertangguh": "Delayed",
    }
    for d in defects:
        if d.get("status") in STATUS_NORMALISE:
            d["status"] = STATUS_NORMALISE[d["status"]]

    def build_summary_stats(s):
        return {
            "jumlah_kecacatan":  s.get("total", 0),
            "belum_diselesaikan": s.get("pending", 0),
            "telah_diselesaikan": s.get("completed", 0),
            "kritikal":           s.get("critical", 0),
        }

    def build_role_context(r, lang):
        if r == "Homeowner":
            return {"tajuk_laporan": "BORANG 1 - PERNYATAAN TUNTUTAN" if lang == "ms" else "FORM 1 - STATEMENT OF CLAIM",
                    "tujuan": "Laporan ini disediakan bagi merumuskan kecacatan yang berlaku dalam tempoh DLP untuk rujukan Tribunal."}
        if r == "Developer":
            return {"tajuk_laporan": "LAPORAN PEMATUHAN DLP" if lang == "ms" else "DLP COMPLIANCE REPORT",
                    "tujuan": "Laporan ini disediakan untuk menunjukkan status pembaikan dan pematuhan pemaju terhadap kecacatan yang dilaporkan."}
        return {"tajuk_laporan": "LAPORAN RUJUKAN TRIBUNAL DLP" if lang == "ms" else "TRIBUNAL REFERENCE REPORT (DLP)",
                "tujuan": "Laporan ini disediakan sebagai gambaran keseluruhan status kecacatan dan pematuhan untuk rujukan Tribunal."}

    report_data = {
        "maklumat_kes":       maklumat_kes,
        "pihak_yang_menuntut": pihak_yang_menuntut,
        "penentang":          penentang,
        "konteks_peranan":    build_role_context(role, language),
        "ringkasan_statistik": build_summary_stats(stats),
        "senarai_kecacatan":  build_defect_list(defects, role),
        "nota_penting":       "Laporan ini dijana oleh sistem sebagai dokumen sokongan kepada Borang 1 TTPM.",
    }

    STATUS_MAP = {
        "ms": {"Pending": "Belum Diselesaikan", "In Progress": "Dalam Tindakan",
               "Completed": "Telah Diselesaikan", "Delayed": "Tertangguh"},
        "en": {"Pending": "Pending", "In Progress": "In Progress",
               "Completed": "Completed", "Delayed": "Delayed"},
    }
    for d in defects:
        if d.get("status"):
            d["status"] = STATUS_MAP.get(language, {}).get(d["status"], d["status"])

    if role != "Homeowner":
        for d in defects:
            d["remarks"] = ""

    PRIORITY_MAP = {
        "ms": {"High": "Tinggi", "Medium": "Sederhana", "Low": "Rendah"},
        "en": {"Tinggi": "High", "Sederhana": "Medium", "Rendah": "Low"},
    }
    for d in defects:
        if d.get("priority"):
            d["priority"] = PRIORITY_MAP.get(language, {}).get(d["priority"], d["priority"])

    evidence_dir = os.path.join(current_app.root_path, "evidence")
    os.makedirs(evidence_dir, exist_ok=True)

    # ── Styles ────────────────────────────────────────────────────────────────
    styles = getSampleStyleSheet()

    h1 = ParagraphStyle("h1", parent=styles["Normal"],
                        fontName="Helvetica-Bold", fontSize=11, alignment=1, spaceAfter=4)
    h2 = ParagraphStyle("h2", parent=styles["Normal"],
                        fontName="Helvetica-Bold", fontSize=10, alignment=1, spaceAfter=2)
    h3 = ParagraphStyle("h3", parent=styles["Normal"],
                        fontName="Helvetica-Bold", fontSize=12, alignment=1, spaceAfter=6)
    normal = ParagraphStyle("norm", parent=styles["Normal"],
                            fontName="Helvetica", fontSize=9, spaceAfter=2)
    center = ParagraphStyle("ctr", parent=styles["Normal"],
                            fontName="Helvetica", fontSize=10, alignment=1, spaceAfter=2)
    bold_left = ParagraphStyle("bl", parent=styles["Normal"],
                               fontName="Helvetica-Bold", fontSize=10, spaceAfter=4)
    italic_small = ParagraphStyle("is", parent=styles["Normal"],
                                  fontName="Helvetica-Oblique", fontSize=8, spaceAfter=2)
    ai_title_style = ParagraphStyle("ait", parent=styles["Normal"],
                                    fontName="Helvetica-Bold", fontSize=12, alignment=1, spaceAfter=12)
    ai_body_style = ParagraphStyle("aib", parent=styles["Normal"],
                                   fontName="Helvetica", fontSize=9, leading=14, spaceAfter=4)
    disclaimer_title_style = ParagraphStyle("dt", parent=styles["Normal"],
                                            fontName="Helvetica-Bold", fontSize=10, spaceAfter=6)
    disclaimer_body_style = ParagraphStyle("db", parent=styles["Normal"],
                                           fontName="Helvetica-Oblique", fontSize=8, leading=12, spaceAfter=6)

    # ── Table style used for info boxes ──────────────────────────────────────
    INFO_BOX_STYLE = TableStyle([
        ('BOX',       (0,0), (-1,-1), 0.5, colors.black),
        ('FONTNAME',  (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTNAME',  (1,0), (1,-1), 'Helvetica'),
        ('FONTSIZE',  (0,0), (-1,-1), 9),
        ('TOPPADDING',  (0,0),(-1,-1), 3),
        ('BOTTOMPADDING',(0,0),(-1,-1), 3),
        ('LEFTPADDING', (0,0),(-1,-1), 6),
        ('RIGHTPADDING',(0,0),(-1,-1), 6),
        ('VALIGN',    (0,0),(-1,-1), 'TOP'),
    ])

    DEFECT_TABLE_STYLE = TableStyle([
        ('BOX',         (0,0),(-1,-1), 0.5, colors.black),
        ('INNERGRID',   (0,0),(-1,-1), 0.3, colors.grey),
        ('BACKGROUND',  (0,0),(0,-1), colors.HexColor('#f0f0f0')),
        ('FONTNAME',    (0,0),(0,-1), 'Helvetica-Bold'),
        ('FONTNAME',    (1,0),(1,-1), 'Helvetica'),
        ('FONTSIZE',    (0,0),(-1,-1), 9),
        ('TOPPADDING',  (0,0),(-1,-1), 4),
        ('BOTTOMPADDING',(0,0),(-1,-1), 4),
        ('LEFTPADDING', (0,0),(-1,-1), 6),
        ('RIGHTPADDING',(0,0),(-1,-1), 6),
        ('VALIGN',      (0,0),(-1,-1), 'TOP'),
    ])

    SUMMARY_TABLE_STYLE = TableStyle([
        ('BOX',       (0,0),(-1,-1), 0.5, colors.black),
        ('FONTNAME',  (0,0),(-1,-1), 'Helvetica'),
        ('FONTSIZE',  (0,0),(-1,-1), 9),
        ('TOPPADDING',  (0,0),(-1,-1), 4),
        ('BOTTOMPADDING',(0,0),(-1,-1), 4),
        ('LEFTPADDING', (0,0),(-1,-1), 6),
        ('RIGHTPADDING',(0,0),(-1,-1), 6),
    ])

    # ── Footer / header callback ──────────────────────────────────────────────
    def _on_page(canvas_obj, doc_obj):
        canvas_obj.saveState()
        canvas_obj.setFont("Helvetica", 8)
        canvas_obj.drawRightString(_width - 50, 20,
                                   f"{labels['page']} {doc_obj.page}")
        canvas_obj.drawString(50, 20,
                              f"{labels.get('digital_hash_label','Hash:')} {digital_hash}")
        canvas_obj.restoreState()

    # ── Build flowables list ──────────────────────────────────────────────────
    story = []

    # ════════════════════════════════════════════════════════════════════════
    # PAGE 1: BORANG 1 / PERNYATAAN TUNTUTAN  (all roles)
    # ════════════════════════════════════════════════════════════════════════
    if language == "en":
        story.append(Paragraph("CONSUMER PROTECTION ACT 1999", h1))
        story.append(Paragraph("CONSUMER PROTECTION REGULATIONS", h2))
        story.append(Paragraph("(CONSUMER CLAIMS TRIBUNAL) 1999", h2))
        story.append(Spacer(1, 8))
        story.append(Paragraph("FORM 1", h3))
        story.append(Paragraph("(Regulation 5)", ParagraphStyle("reg", parent=normal, alignment=1)))
        story.append(Spacer(1, 8))
        story.append(Paragraph("STATEMENT OF CLAIM", h1))
        story.append(Paragraph("IN THE CONSUMER CLAIMS TRIBUNAL", center))
    else:
        story.append(Paragraph("AKTA PERLINDUNGAN PENGGUNA 1999", h1))
        story.append(Paragraph("PERATURAN-PERATURAN PERLINDUNGAN PENGGUNA", h2))
        story.append(Paragraph("(TRIBUNAL TUNTUTAN PENGGUNA) 1999", h2))
        story.append(Spacer(1, 8))
        story.append(Paragraph("BORANG 1", h3))
        story.append(Paragraph("(Peraturan 5)", ParagraphStyle("reg", parent=normal, alignment=1)))
        story.append(Spacer(1, 8))
        story.append(Paragraph("PERNYATAAN TUNTUTAN", h1))
        story.append(Paragraph("DALAM TRIBUNAL TUNTUTAN PENGGUNA", center))

    story.append(Spacer(1, 6))

    # Location & claim number
    lok = maklumat_kes.get("lokasi_tribunal", "")
    neg = maklumat_kes.get("negeri", "")
    no_tuntutan = maklumat_kes.get("no_tuntutan", "")
    if language == "en":
        story.append(Paragraph(f"AT {lok.upper()}", center))
        story.append(Paragraph(f"IN THE STATE OF {neg.upper()}, MALAYSIA", center))
        story.append(Spacer(1, 4))
        story.append(Paragraph(f"CLAIM NO.: {no_tuntutan}", normal))
    else:
        story.append(Paragraph(f"DI {lok.upper()}", center))
        story.append(Paragraph(f"DI NEGERI {neg.upper()}, MALAYSIA", center))
        story.append(Spacer(1, 4))
        story.append(Paragraph(f"TUNTUTAN NO.: {no_tuntutan}", normal))

    story.append(Spacer(1, 10))

    # ── Claimant (Pihak Yang Menuntut) table ─────────────────────────────────
    claimant = pihak_yang_menuntut
    if language == "en":
        story.append(Paragraph("CLAIMANT", bold_left))
        c_rows = [
            ["Claimant Name",           claimant.get("nama", "-")],
            ["IC/Passport No.",         claimant.get("no_kp", "-")],
            ["Correspondence Address",  claimant.get("alamat_1", "-")],
            ["",                        claimant.get("alamat_2", "")],
            ["Phone No.",               claimant.get("no_telefon", "-")],
            ["Fax/Email",               claimant.get("email", "-")],
        ]
    else:
        story.append(Paragraph("PIHAK YANG MENUNTUT", bold_left))
        c_rows = [
            ["Nama Pihak Yang Menuntut",     claimant.get("nama", "-")],
            ["No. Kad Pengenalan/Pasport",   claimant.get("no_kp", "-")],
            ["Alamat Surat Menyurat",        claimant.get("alamat_1", "-")],
            ["",                             claimant.get("alamat_2", "")],
            ["No. Telefon",                  claimant.get("no_telefon", "-")],
            ["No. Faks/ E-mel",              claimant.get("email", "-")],
        ]
    ct = Table(c_rows, colWidths=[CONTENT_W * 0.38, CONTENT_W * 0.62])
    ct.setStyle(INFO_BOX_STYLE)
    story.append(ct)
    story.append(Spacer(1, 10))

    # ── Respondent (Penentang) table ─────────────────────────────────────────
    resp = penentang
    if language == "en":
        story.append(Paragraph("RESPONDENT", bold_left))
        r_rows = [
            ["Respondent/Company Name",          resp.get("nama", "-")],
            ["IC/Company Registration No.",      resp.get("no_pendaftaran", "-")],
            ["Correspondence Address",           resp.get("alamat_1", "-")],
            ["",                                 resp.get("alamat_2", "")],
            ["Phone No.",                        resp.get("no_telefon", "-")],
            ["Fax/Email",                        resp.get("email", "-")],
        ]
    else:
        story.append(Paragraph("PENENTANG", bold_left))
        r_rows = [
            ["Nama Penentang/Syarikat/\nPertubuhan Perbadanan/Firma", resp.get("nama", "-")],
            ["No. Kad Pengenalan/\nNo. Pendaftaran Syarikat/\nPertubuhan Perbadanan/Firma",
             resp.get("no_pendaftaran", "-")],
            ["Alamat Surat Menyurat",    resp.get("alamat_1", "-")],
            ["",                         resp.get("alamat_2", "")],
            ["No. Telefon",              resp.get("no_telefon", "-")],
            ["No. Faks/E-mel",           resp.get("email", "-")],
        ]
    rt = Table(r_rows, colWidths=[CONTENT_W * 0.38, CONTENT_W * 0.62])
    rt.setStyle(INFO_BOX_STYLE)
    story.append(rt)
    story.append(Spacer(1, 10))

    # ── Pernyataan Tuntutan box ───────────────────────────────────────────────
    amaun = maklumat_kes.get("amaun_tuntutan", "RM 0.00")
    tarikh_jana = maklumat_kes.get("tarikh_jana", "")

    if language == "en":
        story.append(Paragraph("STATEMENT OF CLAIM", bold_left))
        story.append(Paragraph(f"The Claimant's claim is for the amount of RM: {amaun}", normal))
        story.append(Spacer(1, 6))
        story.append(Paragraph("Claim Details", bold_left))
        cd_rows = [
            ["Goods/Services",           "Defect Repairs During DLP Period"],
            ["Date of Purchase/Transaction", tarikh_jana],
            ["Amount Paid",              amaun],
        ]
    else:
        story.append(Paragraph("PERNYATAAN TUNTUTAN", bold_left))
        story.append(Paragraph(f"Tuntutan Pihak Yang Menuntut ialah untuk jumlah RM: {amaun}", normal))
        story.append(Spacer(1, 6))
        story.append(Paragraph("Butir-butir Tuntutan", bold_left))
        cd_rows = [
            ["Barangan/Perkhidmatan",        "Pembaikan Kecacatan Dalam Tempoh DLP"],
            ["Tarikh Pembelian/ Transaksi",   tarikh_jana],
            ["Jumlah yang dibayar",           amaun],
        ]
    cdt = Table(cd_rows, colWidths=[CONTENT_W * 0.38, CONTENT_W * 0.62])
    cdt.setStyle(INFO_BOX_STYLE)
    story.append(cdt)

    # ── End of Page 1 → force new page ───────────────────────────────────────
    story.append(PageBreak())

    # ════════════════════════════════════════════════════════════════════════
    # PAGE 2+: RINGKASAN TUNTUTAN
    # ════════════════════════════════════════════════════════════════════════
    summary = report_data["ringkasan_statistik"]
    if language == "en":
        story.append(Paragraph("Claim Summary:", bold_left))
        sm_rows = [
            [f"Total Defects Reported: {summary['jumlah_kecacatan']}"],
            [f"Pending: {summary['belum_diselesaikan']}"],
            [f"Completed: {summary['telah_diselesaikan']}"],
        ]
    else:
        story.append(Paragraph("Ringkasan Tuntutan:", bold_left))
        sm_rows = [
            [f"Jumlah Kecacatan Dilaporkan: {summary['jumlah_kecacatan']}"],
            [f"Belum Diselesaikan: {summary['belum_diselesaikan']}"],
            [f"Telah Diselesaikan: {summary['telah_diselesaikan']}"],
        ]
    smt = Table(sm_rows, colWidths=[CONTENT_W])
    smt.setStyle(SUMMARY_TABLE_STYLE)
    story.append(smt)
    story.append(Spacer(1, 16))

    # ── Senarai Kecacatan header ──────────────────────────────────────────────
    if language == "en":
        story.append(Paragraph("Defect List:", bold_left))
    else:
        story.append(Paragraph("Senarai Kecacatan:", bold_left))

    story.append(Spacer(1, 6))

    # ════════════════════════════════════════════════════════════════════════
    # DEFECT LOOP – one KeepTogether block per defect
    # ════════════════════════════════════════════════════════════════════════
    for i, defect in enumerate(defects, 1):
        block = []  # will be wrapped in KeepTogether

        # ── Defect heading ────────────────────────────────────────────────
        defect_label = f"{chr(64+i)}. {labels['defect_id']} {defect['id']}"
        block.append(Paragraph(defect_label,
                                ParagraphStyle("dh", parent=styles["Normal"],
                                               fontName="Helvetica-Bold", fontSize=10, spaceAfter=4)))

        # ── Compute date fields ───────────────────────────────────────────
        def _fmt(d):
            if not d:
                return "-"
            if hasattr(d, "strftime"):
                return d.strftime("%d-%m-%Y")
            return str(d)

        tarikh_dilaporkan      = _fmt(defect.get("reported_date"))
        tarikh_siap_dijadualkan = _fmt(defect.get("scheduled_date") or defect.get("deadline"))
        tarikh_siap_sebenar    = _fmt(defect.get("actual_completion_date"))
        is_overdue             = defect.get("is_overdue", False)
        hda_compliant          = defect.get("hda_compliant", True)

        if language == "ms":
            pematuhan_hda   = "Patuh" if hda_compliant else "Tidak Patuh"
            overdue_text    = "Ya" if is_overdue else "Tidak"
        else:
            pematuhan_hda   = "Compliant" if hda_compliant else "Non-Compliant"
            overdue_text    = "Yes" if is_overdue else "No"

        # ── Defect detail table ───────────────────────────────────────────
        desc_para = Paragraph(defect.get("desc") or defect.get("description") or "-", normal)
        if language == "ms":
            d_rows = [
                ["Keterangan",               desc_para],
                ["Unit",                     defect.get("unit", "-")],
                ["Status",                   defect.get("status", "-")],
                ["Tarikh Dilaporkan",         tarikh_dilaporkan],
                ["Tarikh Siap Dijadualkan",   tarikh_siap_dijadualkan],
                ["Tarikh Siap Sebenar",       tarikh_siap_sebenar],
                ["Pematuhan HDA (30 Hari)",   pematuhan_hda],
                ["Melebihi Tarikh",           overdue_text],
                ["Keutamaan",                defect.get("priority", "-")],
            ]
            if role == "Homeowner" and defect.get("remarks"):
                d_rows.append(["Ulasan", defect.get("remarks", "")])
        else:
            d_rows = [
                ["Description",              desc_para],
                ["Unit",                     defect.get("unit", "-")],
                ["Status",                   defect.get("status", "-")],
                ["Date Reported",             tarikh_dilaporkan],
                ["Scheduled Completion Date", tarikh_siap_dijadualkan],
                ["Actual Completion Date",    tarikh_siap_sebenar],
                ["HDA Compliance (30 Days)",  pematuhan_hda],
                ["Overdue",                  overdue_text],
                ["Priority",                 defect.get("priority", "-")],
            ]
            if role == "Homeowner" and defect.get("remarks"):
                d_rows.append(["Remarks", defect.get("remarks", "")])

        dt = Table(d_rows, colWidths=[CONTENT_W * 0.38, CONTENT_W * 0.62])
        dt.setStyle(DEFECT_TABLE_STYLE)
        block.append(dt)

        # ── Defect image(s) ───────────────────────────────────────────────
        image_path = None
        if defect.get("image_path"):
            candidate = os.path.join("/usr/src/app_main/app/static/",
                                     defect["image_path"].lstrip("/"))
            if os.path.exists(candidate):
                image_path = candidate

        if not image_path:
            alt = os.path.join(evidence_dir, f"defect_{defect['id']}.jpg")
            if os.path.exists(alt):
                image_path = alt

        if image_path:
            block.append(Spacer(1, 4))
            block.append(Paragraph(f"{labels['evidence']}:", italic_small))
            try:
                img = RLImage(image_path, width=200, height=110)
                block.append(img)
            except Exception:
                pass

        block.append(Spacer(1, 14))

        # Wrap entire block so it stays together across page breaks
        story.append(KeepTogether(block))

    # ════════════════════════════════════════════════════════════════════════
    # AI SUMMARY SECTION – always starts on a NEW page
    # ════════════════════════════════════════════════════════════════════════
    if ai_report_text:
        story.append(PageBreak())

        if language == "en":
            story.append(Paragraph("LAPORAN SOKONGAN TRIBUNAL", ai_title_style))
        else:
            story.append(Paragraph("LAPORAN SOKONGAN TRIBUNAL", ai_title_style))

        story.append(Spacer(1, 8))

        # Clean markdown/non-ASCII
        clean = ai_report_text
        for tok in ["**", "*", "##", "#"]:
            clean = clean.replace(tok, "")
        clean = clean.replace("\r\n", "\n").replace("\r", "\n")
        clean = re.sub(r"[^\x00-\x7F]+", "", clean)

        # Status/priority normalisation in text
        if language == "en":
            clean = (clean
                     .replace("Status: Telah Diselesaikan", "Status: Completed")
                     .replace("Status: Belum Diselesaikan", "Status: Pending")
                     .replace("Status: Dalam Tindakan",     "Status: In Progress")
                     .replace("Status: Tertangguh",         "Status: Delayed")
                     .replace("Keutamaan:",                 "Priority:")
                     .replace("Priority: Tinggi",           "Priority: High")
                     .replace("Priority: Sederhana",        "Priority: Medium")
                     .replace("Priority: Rendah",           "Priority: Low"))
        else:
            clean = (clean
                     .replace("Status: Completed",   "Status: Telah Diselesaikan")
                     .replace("Status: Pending",     "Status: Belum Diselesaikan")
                     .replace("Status: In Progress", "Status: Dalam Tindakan")
                     .replace("Status: Delayed",     "Status: Tertangguh")
                     .replace("Priority:",            "Keutamaan:")
                     .replace("Keutamaan: High",     "Keutamaan: Tinggi")
                     .replace("Keutamaan: Medium",   "Keutamaan: Sederhana")
                     .replace("Keutamaan: Low",      "Keutamaan: Rendah"))

        for line in clean.split("\n"):
            stripped = line.strip()
            if not stripped:
                story.append(Spacer(1, 6))
                continue
            # Choose style based on line type
            is_header = (
                stripped[:2].isdigit() and "." in stripped[:3] or
                stripped.startswith("PENAFIAN") or
                stripped.startswith("AI Disclaimer") or
                stripped.startswith("Laporan Sokongan") or
                stripped.startswith("Laporan Pematuhan") or
                stripped.startswith("Conclusion") or
                stripped.startswith("Tribunal Support")
            )
            if is_header:
                story.append(Paragraph(stripped,
                                        ParagraphStyle("ail", parent=styles["Normal"],
                                                       fontName="Helvetica-Bold", fontSize=10,
                                                       spaceAfter=4, spaceBefore=10)))
            else:
                safe = stripped.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                story.append(Paragraph(safe, ai_body_style))

    # ════════════════════════════════════════════════════════════════════════
    # AI DISCLAIMER
    # ════════════════════════════════════════════════════════════════════════
    story.append(Spacer(1, 16))
    story.append(Paragraph(labels.get("ai_disclaimer_title", "PENAFIAN AI"), disclaimer_title_style))
    story.append(Paragraph(labels.get("ai_disclaimer_text", ""), disclaimer_body_style))

    # ════════════════════════════════════════════════════════════════════════
    # SIGNATURE PAGE
    # ════════════════════════════════════════════════════════════════════════
    story.append(PageBreak())

    if language == "en":
        story.append(Paragraph("Verification and Signature", h1))
    else:
        story.append(Paragraph("Pengesahan dan Tandatangan", h1))

    story.append(Spacer(1, 60))

    sig_dot_short = "." * 45
    sig_dot_long  = "." * 70

    if language == "en":
        sig_rows = [
            [sig_dot_short, sig_dot_long],
            ["Date", "Signature/Thumbprint of Claimant"],
            ["", ""],
            [sig_dot_short, sig_dot_long],
            ["Filing Date", "Secretary/Tribunal Officer"],
        ]
    else:
        sig_rows = [
            [sig_dot_short, sig_dot_long],
            ["Tarikh", "Tandatangan/Cap ibu jari Pihak Yang Menuntut"],
            ["", ""],
            [sig_dot_short, sig_dot_long],
            ["Tarikh Pemfailan", "Setiausaha/Pegawai Tribunal"],
        ]
    sig_t = Table(sig_rows, colWidths=[CONTENT_W * 0.35, CONTENT_W * 0.65])
    sig_t.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('ALIGN',    (0,0), (0,-1), 'CENTER'),
        ('ALIGN',    (1,0), (1,-1), 'CENTER'),
        ('BOTTOMPADDING', (0,0),(-1,-1), 4),
        ('TOPPADDING',    (0,0),(-1,-1), 4),
    ]))
    story.append(sig_t)
    story.append(Spacer(1, 60))

    if language == "en":
        story.append(Paragraph("(SEAL)", ParagraphStyle("seal", parent=styles["Normal"],
                                                         fontName="Helvetica-Bold", fontSize=10, alignment=1)))
    else:
        story.append(Paragraph("(METERAI)", ParagraphStyle("seal", parent=styles["Normal"],
                                                            fontName="Helvetica-Bold", fontSize=10, alignment=1)))

    # ════════════════════════════════════════════════════════════════════════
    # BUILD PDF
    # ════════════════════════════════════════════════════════════════════════
    buffer = _BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=_A4,
        leftMargin=LEFT,
        rightMargin=_width - RIGHT,
        topMargin=40,
        bottomMargin=40,
    )
    doc.build(story, onFirstPage=_on_page, onLaterPages=_on_page)
    buffer.seek(0)

    if role == "Legal":       filename = labels["legal_filename"]
    elif role == "Developer": filename = labels["developer_filename"]
    else:                     filename = labels["homeowner_filename"]

    return send_file(buffer, as_attachment=True, download_name=filename, mimetype="application/pdf")

