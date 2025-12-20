from flask import Blueprint, render_template, request, g, redirect, url_for
import sqlite3
import os

# -------------------------------------------------
# 1. Define Blueprint & Database Config
# -------------------------------------------------
bp = Blueprint('module3', __name__, url_prefix='/module3')

# Calculate the path to your main 'pcd' folder
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATABASE = os.path.join(BASE_DIR, 'app.db')

# --- THE FIX IS HERE 👇 ---
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row 
        
        # AUTO-CREATE TABLE if it doesn't exist
        # This guarantees the table exists before you try to save anything
        db.execute('''
            CREATE TABLE IF NOT EXISTS defects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_name TEXT,
                unit_no TEXT,
                description TEXT,
                status TEXT DEFAULT 'draft',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        db.commit()

    return db
# ---------------------------

@bp.teardown_request
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# -------------------------------------------------
# ROUTE 1: Display Insert Defect Form
# -------------------------------------------------
@bp.route('/insert_defect', methods=['GET'])
def insert_defect():
    return render_template('module3/insert_defect.html')

# -------------------------------------------------
# ROUTE 2: Handle Form Submission (Saves to DB)
# -------------------------------------------------
@bp.route('/submit_defect', methods=['POST'])
def submit_defect():
    project_name = request.form.get('project_name')
    owner_name = request.form.get('owner_name')
    unit_no = request.form.get('unit_no')
    
    # Save File
    upload_folder = os.path.join(os.getcwd(), 'app', 'static', 'uploads')
    os.makedirs(upload_folder, exist_ok=True)
    
    lidar_file = request.files.get('lidar_file')
    filename = "No File"
    if lidar_file and lidar_file.filename:
        filename = lidar_file.filename
        lidar_file.save(os.path.join(upload_folder, filename))

    # Save to Database
    db = get_db()
    db.execute(
        'INSERT INTO defects (project_name, unit_no, description, status) VALUES (?, ?, ?, ?)',
        (project_name, unit_no, f"Uploaded: {filename}", 'draft')
    )
    db.commit()

    return render_template('module3/process_defect.html', 
                           project_name=project_name, owner_name=owner_name, 
                           unit_no=unit_no, filename=filename)

# -------------------------------------------------
# ROUTE 3: Evidence Report (Reads from DB)
# -------------------------------------------------
@bp.route('/evidence_report')
def evidence_report():
    db = get_db()
    cur = db.execute('SELECT * FROM defects')
    defects = cur.fetchall()
    
    case_info = {
        "case_id": "CASE-001",
        "client": "Abbas Abu Dzarr",
        "project": "ASMARINDA12",
        "ai_confidence": 98,
        "risk_level": "High"
    }

    return render_template('module3/evidence_report.html', defects=defects, report=case_info)

# -------------------------------------------------
# ROUTE 4: The LOCK Action
# -------------------------------------------------
@bp.route('/lock_evidence/<int:id>', methods=['POST'])
def lock_evidence(id):
    db = get_db()
    db.execute("UPDATE defects SET status = 'locked' WHERE id = ?", (id,))
    db.commit()
    return redirect(url_for('module3.evidence_report'))


# ... existing lock_evidence route ...

# --- NEW ROUTE: VALIDATE ALL (BULK LOCK) ---
@bp.route('/validate_all', methods=['POST'])
def validate_all():
    db = get_db()
    
    # Update ALL items that are currently 'draft'
    db.execute("UPDATE defects SET status = 'locked' WHERE status = 'draft'")
    db.commit()
    
    # Refresh the page
    return redirect(url_for('module3.evidence_report'))
# -------------------------------------------------
# ROUTE 5: 3D Visualizer
# -------------------------------------------------
@bp.route('/visualize')
def visualize():
    filename = request.args.get('filename', 'sisiranRendered.glb') 
    project_name = request.args.get('project_name', 'Demo Project')
    back_to = request.args.get('back_to', 'homeowner')
    return render_template('module3/visualize.html', filename=filename, project_name=project_name, back_to=back_to)