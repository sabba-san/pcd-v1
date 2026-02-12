import os
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app.module3.extensions import db
from .models import Defect, ActivityLog, Scan

# Define the Blueprint
bp = Blueprint('module2', __name__, url_prefix='/module2')

@bp.route('/insert_defect', methods=['GET', 'POST'])
@login_required
def insert_defect():
    if request.method == 'POST':
        try:
            # 1. Handle File Upload (Create new Scan or use existing)
            lidar_file = request.files.get('lidar_file')
            
            scan = None
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
                    model_path=f"uploads/{filename}", # Relative path for static folder
                    user_id=current_user.id
                )
                db.session.add(scan)
                db.session.flush() # Get ID
            else:
                # Fallback to existing or default scan
                scan = Scan.query.filter_by(user_id=current_user.id).order_by(Scan.created_at.desc()).first()
                if not scan:
                    # Create a default if absolutely none exists (edge case)
                    scan = Scan(name="Default Project Scan", model_path="uploads/default.glb", user_id=current_user.id)
                    db.session.add(scan)
                    db.session.flush()

            # 2. Get Coordinates from Form
            try:
                x = float(request.form.get('x', 0))
                y = float(request.form.get('y', 0))
                z = float(request.form.get('z', 0))
            except (ValueError, TypeError):
                x, y, z = 0.0, 0.0, 0.0

            # 3. Create the defect linked to this specific scan
            new_defect = Defect(
                scan_id=scan.id,
                user_id=current_user.id,
                description=request.form.get('description'),
                location=request.form.get('unit_no'),
                status='Reported',
                x=x, y=y, z=z
            )
            
            db.session.add(new_defect)
            
            # 4. Log the activity
            log = ActivityLog(
                defect_id=new_defect.id,
                scan_id=scan.id,
                action=f"Claim submitted by {current_user.username}",
                new_value="Reported"
            )
            db.session.add(log)
            
            db.session.commit()
            
            # 5. Trigger the success message
            flash('Defect claim submitted successfully!', 'success')
            return redirect(url_for('module3.dashboard')) # Redirect to Dashboard (in Module 3 now)
            
        except Exception as e:
            db.session.rollback()
            print(f"DATABASE ERROR: {e}")
            flash(f'Error saving defect: {str(e)}', 'danger')
            return redirect(url_for('module2.insert_defect'))

    # GET Request: Fetch existing data for visualization
    # Get the latest scan for the user to display in the viewer
    latest_scan = Scan.query.filter_by(user_id=current_user.id).order_by(Scan.created_at.desc()).first()
    
    defects = []
    model_url = None
    scan_id = None
    
    if latest_scan:
        scan_id = latest_scan.id
        # Construct proper URL for the model
        if latest_scan.model_path:
             # Assuming model_path is stored as 'uploads/filename.glb'
            model_url = url_for('static', filename=latest_scan.model_path)
        
        # Fetch actual defects for this scan
        defects_query = Defect.query.filter_by(scan_id=latest_scan.id).all()
        # Serialize for JS using the new model method
        defects = [d.to_dict() for d in defects_query]

    return render_template('module2/insert_defect.html', 
                          defects=defects, 
                          model_url=model_url, 
                          scan_id=scan_id)

@bp.route('/api/defect/add', methods=['POST'])
def api_add_defect():
    try:
        # 1. Validate File
        if 'file' not in request.files:
            return jsonify({'status': 'error', 'message': 'No file part'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'status': 'error', 'message': 'No selected file'}), 400
            
        if file:
            # 2. Save File
            filename = secure_filename(file.filename)
            upload_folder = os.path.join(current_app.root_path, 'static', 'uploads')
            os.makedirs(upload_folder, exist_ok=True)
            
            file_path = os.path.join(upload_folder, filename)
            file.save(file_path)
            
            # 3. Handle Project/Scan Association
            # Determine Project/Scan to link to
            scan_id = request.form.get('scan_id')
            project_name = request.form.get('project_name')
            
            scan = None
            if scan_id:
                scan = Scan.query.get(scan_id)
            
            if not scan:
                # Create a new scan/project if one doesn't exist or wasn't provided
                name = project_name if project_name else f"API Upload - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                scan = Scan(
                    name=name,
                    model_path=f"uploads/{filename}", # Associating the upload as the model as well for now
                    user_id=user_id
                )
                db.session.add(scan)
                db.session.flush()

            # 4. Handle User Association
            user_id = request.form.get('user_id')
            if not user_id and current_user.is_authenticated:
                user_id = current_user.id
            
            # 5. Create Defect
            new_defect = Defect(
                scan_id=scan.id,
                user_id=user_id,
                description=request.form.get('description'),
                location=request.form.get('location'),
                status='Reported',
                x=0, y=0, z=0,
                image_path=f"uploads/{filename}" # Save image path
            )
            
            db.session.add(new_defect)
            db.session.flush() # Get ID
            
            # 6. Log Activity
            log = ActivityLog(
                defect_id=new_defect.id,
                scan_id=scan.id,
                action="Defect created via API",
                new_value="Reported"
            )
            db.session.add(log)
            db.session.commit()
            
            return jsonify({
                'status': 'success', 
                'message': 'Defect added successfully', 
                'defect_id': new_defect.id,
                'scan_id': scan.id
            }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500