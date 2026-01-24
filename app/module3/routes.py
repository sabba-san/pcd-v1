import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify, send_from_directory
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app.module3.extensions import db
from app.module3.models import Defect, ActivityLog, Scan

bp = Blueprint('module3', __name__, url_prefix='/module3')

@bp.route('/projects', methods=['GET'])
@login_required
def list_projects():
    """List all scans/projects in the database"""
    scans = Scan.query.order_by(Scan.created_at.desc()).all()
    
    # Enhance scan data with defect counts
    projects = []
    for scan in scans:
        defect_count = Defect.query.filter_by(scan_id=scan.id).count()
        
        projects.append({
            'id': scan.id,
            'name': scan.name,
            'created_at': scan.created_at,
            'defect_count': defect_count,
            'model_path': scan.model_path,
            # Placeholder for metadata until file upload logic is fully ported
            'metadata': None 
        })
        
    return render_template('module3/projects.html', projects=projects)

@bp.route('/insert_defect', methods=['GET', 'POST'])
@login_required
def insert_defect():
    if request.method == 'POST':
        try:
            # 1. Handle File Upload (Create new Scan or use existing)
            lidar_file = request.files.get('lidar_file')
            pdf_file = request.files.get('pdf_file') # For future use
            
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
            return redirect(url_for('module1.dashboard'))
            
        except Exception as e:
            db.session.rollback()
            print(f"DATABASE ERROR: {e}")
            flash(f'Error saving defect: {str(e)}', 'danger')
            return redirect(url_for('module3.insert_defect'))

    return render_template('module3/insert_defect.html')

@bp.route('/api/scans/<int:scan_id>/defects', methods=['GET'])
@login_required
def get_scan_defects(scan_id):
    scan = Scan.query.get_or_404(scan_id)
    
    # Filter by user if they are a homeowner (role='user')
    if current_user.role == 'user':
        defects = Defect.query.filter_by(scan_id=scan_id, user_id=current_user.id).all()
    else:
        # Developers/Lawyers/Admin see all
        defects = Defect.query.filter_by(scan_id=scan_id).all()
    
    defect_list = [{
        'id': d.id,
        'x': d.x, 
        'y': d.y, 
        'z': d.z,
        'element': d.element,
        'location': d.location,
        'defect_type': d.defect_type,
        'severity': d.severity,
        'status': d.status,
        'description': d.description,
        'created_at': d.created_at.strftime('%Y-%m-%d') if d.created_at else None
    } for d in defects]
    
    return jsonify(defect_list)

@bp.route('/api/scans/<int:scan_id>/defects', methods=['POST'])
@login_required
def create_defect(scan_id):
    scan = Scan.query.get_or_404(scan_id)
    data = request.get_json()
    
    try:
        new_defect = Defect(
            scan_id=scan_id,
            user_id=current_user.id,
            x=data.get('x', 0),
            y=data.get('y', 0),
            z=data.get('z', 0),
            element=data.get('element', ''),
            location=data.get('location', ''),
            defect_type=data.get('defect_type', 'Unknown'),
            severity=data.get('severity', 'Medium'),
            description=data.get('description', ''),
            status=data.get('status', 'Reported'),
            notes=data.get('notes', '')
        )
        
        db.session.add(new_defect)
        db.session.flush() # Get ID
        
        # Log activity
        log = ActivityLog(
            defect_id=new_defect.id,
            scan_id=scan.id,
            action=f"Defect created by {current_user.username}",
            new_value="Reported"
        )
        db.session.add(log)
        
        db.session.commit()
        return jsonify({'message': 'Defect created', 'defectId': new_defect.id}), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/api/defects/<int:defect_id>', methods=['PUT'])
@login_required
def update_defect(defect_id):
    defect = Defect.query.get_or_404(defect_id)
    data = request.get_json()
    
    try:
        if 'status' in data:
            old_status = defect.status
            defect.status = data['status']
            if old_status != defect.status:
                log = ActivityLog(
                    defect_id=defect.id,
                    scan_id=defect.scan_id,
                    action=f"Status updated by {current_user.username}",
                    old_value=old_status,
                    new_value=defect.status
                )
                db.session.add(log)
                
        if 'notes' in data: defect.notes = data['notes']
        if 'description' in data: defect.description = data['description']
        if 'severity' in data: defect.severity = data['severity']
        if 'location' in data: defect.location = data['location']
        if 'defect_type' in data: defect.defect_type = data['defect_type']
        
        db.session.commit()
        return jsonify({'message': 'Defect updated successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/api/defects/<int:defect_id>', methods=['DELETE'])
@login_required
def delete_defect(defect_id):
    defect = Defect.query.get_or_404(defect_id)
    try:
        db.session.delete(defect)
        db.session.commit()
        return jsonify({'message': 'Defect deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/visualize/<int:scan_id>')
@login_required
def visualize(scan_id):
    # Ensure scan exists
    scan = Scan.query.get_or_404(scan_id)
    
    # Check if model exists
    model_url = url_for('module3.serve_model', scan_id=scan_id) if scan.model_path else None
    
    return render_template(
        'module3/visualize.html', 
        scan=scan,
        scan_id=scan_id,
        model_url=model_url,
        project_name=current_user.project_name
    )

@bp.route('/model/<int:scan_id>')
@login_required
def serve_model(scan_id):
    scan = Scan.query.get_or_404(scan_id)
    if not scan.model_path:
        return "No model uploaded", 404
        
    # In this simplified version, we assume models are in static/models or uploads
    # Adjust this path based on where you actually store files
    # For now, let's assume they are in app/static
    import os
    file_path = os.path.join(current_app.root_path, 'static', scan.model_path)
    
    # If using absolute path or uploads folder logic:
    if os.path.exists(file_path):
        directory = os.path.dirname(file_path)
        filename = os.path.basename(file_path)
        return send_from_directory(directory, filename)
        
    return "Model file not found", 404