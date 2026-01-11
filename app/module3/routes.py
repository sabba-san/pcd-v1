from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from werkzeug.utils import secure_filename
from app.db import get_db # Importing the new Postgres connection
import os

bp = Blueprint('module3', __name__, url_prefix='/defects')

# 1. SHOW THE FORM
@bp.route('/new', methods=['GET'])
def insert_defect():
    # Security: Require Login
    if 'user_id' not in session:
        flash("Please log in to report a defect.", "error")
        return redirect(url_for('auth.login'))
        
    # Show the new file you created
    return render_template('module3/defect_form.html')

# 2. HANDLE SUBMISSION
@bp.route('/submit', methods=['POST'])
def submit_defect():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    # 1. Get Form Data
    user_id = session['user_id']
    unit_no = request.form.get('unit_no')
    project_name = request.form.get('project_name')
    description = request.form.get('description')
    action = request.form.get('action') # 'submit' or 'visualize'

    # 2. Handle File Upload
    filename = None
    if 'lidar_file' in request.files:
        file = request.files['lidar_file']
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            # Save to: app/static/uploads
            upload_path = os.path.join(current_app.root_path, 'static', 'uploads')
            os.makedirs(upload_path, exist_ok=True) # Create folder if missing
            file.save(os.path.join(upload_path, filename))

    # 3. Save to PostgreSQL Database
    try:
        db = get_db()
        cur = db.cursor()
        cur.execute(
            """INSERT INTO defects (user_id, project_name, unit_no, description, filename, status) 
               VALUES (%s, %s, %s, %s, %s, 'New')""",
            (user_id, project_name, unit_no, description, filename)
        )
        db.commit()
        cur.close()
    except Exception as e:
        print(f"Database Error: {e}")
        flash("Error saving defect. Please try again.", "error")
        return redirect(url_for('module3.insert_defect'))

    # 4. Decide where to go next
    if action == 'visualize':
        # Pass data to the visualizer (We will build this view next)
        return redirect(url_for('module3.visualize', filename=filename))
    
    flash(f"Defect reported for Unit {unit_no} successfully!", "success")
    return redirect(url_for('module1.dashboard'))

# 3. VISUALIZER (Placeholder for now)
@bp.route('/visualize')
def visualize():
    filename = request.args.get('filename')
    return f"<h1>3D Visualizer Loading... File: {filename}</h1>"