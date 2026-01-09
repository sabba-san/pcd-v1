from flask import Blueprint, render_template, request, g, redirect, url_for, session, current_app
import sqlite3
import os

# Define the Blueprint
bp = Blueprint('module3', __name__, url_prefix='/module3')

# --- DATABASE CONNECTION ---
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        # Connect to the Main PCD Database
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        DATABASE = os.path.join(BASE_DIR, 'app.db')
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@bp.teardown_request
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# --- ROUTES ---

@bp.route('/')
def index():
    # Redirect root to the insert/upload page
    return redirect(url_for('module3.insert_defect'))

# 1. INSERT DEFECT (Uses your 'upload.html')
@bp.route('/insert_defect', methods=['GET'])
def insert_defect():
    return render_template('module3/upload.html')

# 2. HANDLE SUBMISSION
@bp.route('/submit_defect', methods=['POST'])
def submit_defect():
    # Handle File Upload
    if 'lidar_file' not in request.files:
        return 'No file part', 400
    file = request.files['lidar_file']

    filename = ""
    if file and file.filename != '':
        filename = file.filename
        # Save to Main App's upload folder
        upload_folder = os.path.join(current_app.root_path, 'static', 'uploads')
        os.makedirs(upload_folder, exist_ok=True)
        file.save(os.path.join(upload_folder, filename))

    project_name = request.form.get('project_name', 'My Project')

    # Decide where to go: Visualize or Report
    action = request.form.get('action')

    if action == 'visualize':
        return redirect(url_for('module3.visualize', filename=filename, project_name=project_name))
    else:
        return redirect(url_for('module3.report', filename=filename, project_name=project_name))

# 3. VISUALIZER (Uses your 'visualization.html')
@bp.route('/visualize')
def visualize():
    filename = request.args.get('filename', 'sisiranRendered.glb') 
    project_name = request.args.get('project_name', 'Project')
    return render_template('module3/visualization.html', filename=filename, project_name=project_name)

# 4. REPORT (Uses your 'process_result.html')
@bp.route('/report')
def report():
    filename = request.args.get('filename', '')
    project_name = request.args.get('project_name', '')
    return render_template('module3/process_result.html', filename=filename, project_name=project_name)
