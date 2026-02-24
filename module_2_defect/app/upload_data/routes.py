import json
import os
from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from werkzeug.utils import secure_filename

from .pdf_utils import extract_pdf_images

upload_data_bp = Blueprint("upload_data", __name__)

ALLOWED_GLB_EXT = {".glb"}
ALLOWED_PDF_EXT = {".pdf"}
METADATA_FILENAME = "latest_upload.json"

def _allowed_file(filename: str, allowed_exts) -> bool:
    _, ext = os.path.splitext(filename.lower())
    return ext in allowed_exts

@upload_data_bp.route("/upload-data", methods=["GET", "POST"])
def upload_scan_data():
    """
    Use Case DM_01: Upload Scan Data
    User: Homeowner / Inspector
    Goal: Upload the 3D GLB model to the system.
    Precondition: None
    Postcondition: Files are stored, and automated data processing is initiated.
    """
    if request.method == "GET":
        return render_template("upload_data/upload.html")

    try:
        glb_file = request.files.get("glb_model")
        unit_no = request.form.get("unit_no", "")
        notes = request.form.get("notes", "")

        if not glb_file or glb_file.filename == "":
            flash("Please upload a GLB 3D model file.", "error")
            return redirect(request.url)

        if not _allowed_file(glb_file.filename, ALLOWED_GLB_EXT):
            flash("Invalid 3D model file type. Only .glb is allowed.", "error")
            return redirect(request.url)

        upload_root = os.path.join(current_app.instance_path, "uploads", "upload_data")
        os.makedirs(upload_root, exist_ok=True)

        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        upload_id = f"upload_{timestamp}"

        glb_name = secure_filename(glb_file.filename)
        glb_path = os.path.join(upload_root, glb_name)
        glb_file.save(glb_path)

        _persist_latest_upload_metadata(
            upload_root,
            {
                "id": upload_id,
                "created_at": timestamp,
                "unit_no": unit_no,
                "glb_path": glb_path,
                "notes": notes,
            },
        )

        _start_automated_data_processing(glb_path, unit_no, notes)

        flash("Scan data uploaded successfully. Automated processing has started.", "success")
        return redirect(url_for("upload_data.upload_scan_data"))
    except Exception as e:
        current_app.logger.error("Error during upload: %s", str(e))
        flash(f"An error occurred during upload: {str(e)}", "error")
        return redirect(request.url)

def _start_automated_data_processing(glb_path: str, unit_no: str, notes: str) -> None:
    current_app.logger.info("Starting automated processing for:")
    current_app.logger.info("GLB: %s", glb_path)
    current_app.logger.info("Unit No: %s", unit_no)
    if notes:
        current_app.logger.info("Notes: %s", notes)
    # TODO: implement real processing here


def _persist_latest_upload_metadata(upload_root: str, payload: dict) -> None:
    metadata_path = os.path.join(upload_root, METADATA_FILENAME)
    with open(metadata_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)