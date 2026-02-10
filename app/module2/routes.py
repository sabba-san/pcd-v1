import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app.module3.extensions import db
from app.module3.models import Defect, ActivityLog, Scan

# Define the Blueprint
bp = Blueprint('module2', __name__, url_prefix='/module2')

@bp.route('/insert_defect', methods=['GET', 'POST'])
@login_required
def insert_defect():
    if request.method == 'POST':
        try:
            # 1. Handle File Upload (Create new Scan or use existing)
            lidar_file = request.files.get('lidar_file')
            
            if lidar_file and lidar_file.filename:
                # Save the new file
                filename = secure_filename(lidar_file.filename)
                # Ensure uploads directory exists
                upload_folder = os.path.join(current_app.root_path, 'static', 'uploads')
                os.makedirs(upload_folder, exist_ok=True)
                
                lidar_path = os.path.join(upload_folder, filename)
                lidar_file.save(lidar_path)
                
                # Create a NEW Scan record for this upload
                project_name = request.form.get('project_name') or "New Project Scan"
                scan = Scan(
                    name=f"{project_name} - {filename}",
                    model_path=f"uploads/{filename}" # Relative path for static folder
                )
                db.session.add(scan)
                db.session.flush() # Get ID
            else:
                # Fallback URL or error? For now, fallback to default if exists
                scan = Scan.query.first()
                if not scan:
                    scan = Scan(name="Default Project Scan")
                    db.session.add(scan)
                    db.session.flush()

            # 2. Create the defect linked to this specific scan
            new_defect = Defect(
                scan_id=scan.id,
                user_id=current_user.id,
                description=request.form.get('description'),
                location=request.form.get('unit_no'),
                status='Reported',
                x=0, y=0, z=0
            )
            
            db.session.add(new_defect)
            
            # 3. Log the activity
            log = ActivityLog(
                defect_id=new_defect.id,
                scan_id=scan.id,
                action=f"Claim submitted by {current_user.username}",
                new_value="Reported"
            )
            db.session.add(log)
            
            db.session.commit()
            
            # 4. Trigger the success message
            flash('Defect claim submitted successfully!', 'success')
            return redirect(url_for('module3.dashboard')) # Redirect to Dashboard (in Module 3 now)
            
        except Exception as e:
            db.session.rollback()
            print(f"DATABASE ERROR: {e}")
            flash(f'Error saving defect: {str(e)}', 'danger')
            return redirect(url_for('module2.insert_defect'))

    return render_template('module2/insert_defect.html')