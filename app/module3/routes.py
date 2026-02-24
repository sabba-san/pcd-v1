import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify, send_from_directory
from flask_login import login_required, current_user
import requests
from werkzeug.utils import secure_filename
from app.module3.extensions import db
from app.models import Defect, Project, User

bp = Blueprint('module3', __name__, url_prefix='/module3')

@bp.route('/ws/ws', methods=['GET', 'POST', 'OPTIONS'])
def silence_ws():
    """Dummy route to silence WebSocket 404 errors from external tools."""
    return '', 204

@bp.route('/projects', methods=['GET'])
@login_required
def list_projects():
    """List all projects in the database"""
    # For now, list all projects or just the user's project
    # Since 'Projects' means Housing Areas now, if user is homeowner, show their project.
    # If developer, show their projects.
    
    projects_list = []
    
    if current_user.role == 'user':
        projects_set = set()
        user_defects = Defect.query.filter_by(user_id=current_user.id).all()
        for d in user_defects:
            if d.project_id:
                p = Project.query.get(d.project_id)
                if p: projects_set.add(p)
                
        if current_user.project_id:
             p = Project.query.get(current_user.project_id)
             if p: projects_set.add(p)
             
        projects_query = list(projects_set)
    elif current_user.role == 'developer':
         projects_query = Project.query.filter_by(developer_name=current_user.company_name).all() # Or similar logic
         if not projects_query: # Fallback to all if name match not precise or null
              projects_query = Project.query.all()
    else:
         projects_query = Project.query.all()
    
    
    for proj in projects_query:
        if not proj: continue
        
        # Calculate Project Status
        defects = Defect.query.filter_by(project_id=proj.id).all()
        status = 'New'
        
        if not defects:
            status = 'New'
        else:
            statuses = [d.status for d in defects]
            if all(s == 'completed' for s in statuses):
                status = 'Completed'
            elif any(s in ['in_progress', 'locked', 'Processing'] for s in statuses):
                status = 'Processing'
            elif any(s == 'rejected' for s in statuses):
                status = 'Action Required' 
            else:
                status = 'Pending'

        # Determine Model Path and House Scan Fallback
        model_path = proj.master_model_path
        house_scan_id = None
        
        if not model_path:
            # Fallback to the latest house scan (a defect with a scan_path)
            latest_scan = Defect.query.filter_by(project_id=proj.id).filter(Defect.scan_path != None).order_by(Defect.created_at.desc()).first()
            if latest_scan:
                model_path = latest_scan.scan_path
                house_scan_id = latest_scan.id

        projects_list.append({
            'id': proj.id,
            'name': proj.name,
            'created_at': proj.created_at,
            'defect_count': len(defects),
            'model_path': model_path,
            'house_scan_id': house_scan_id,
            'status': status,
            'metadata': None 
        })
        
    return render_template('module3/projects.html', projects=projects_list)

@bp.route('/visualize/<int:project_id>')
@login_required
def visualize(project_id):
    # Ensure project exists
    project = Project.query.get_or_404(project_id)
    
    # Check if model exists
    model_url = url_for('module3.serve_model', project_id=project_id) if project.master_model_path else None
    
    # Fallback to the latest house scan for this project if no master model
    house_scan_id = None
    if not model_url:
        latest_scan = Defect.query.filter_by(project_id=project.id).filter(Defect.scan_path != None).order_by(Defect.created_at.desc()).first()
        if latest_scan:
            model_url = url_for('module3.serve_defect_model', defect_id=latest_scan.id)
            house_scan_id = latest_scan.id

    return render_template(
        'module3/visualize.html', 
        scan=project, # Template might still use 'scan' variable name
        scan_id=project_id,
        house_scan_id=house_scan_id,
        model_url=model_url,
        project_name=project.name
    )

@bp.route('/model/<int:project_id>')
@login_required
def serve_model(project_id):
    project = Project.query.get_or_404(project_id)
    if not project.master_model_path:
        return "No model uploaded", 404
        
    import os
    file_path = os.path.join(current_app.root_path, 'static', project.master_model_path)
    
    if os.path.exists(file_path):
        directory = os.path.dirname(file_path)
        filename = os.path.basename(file_path)
        return send_from_directory(directory, filename)
        
    return "Model file not found", 404

@bp.route('/visualize_defect/<int:defect_id>')
@login_required
def visualize_defect(defect_id):
    # This route is used to visualize a House Scan which is stored as a Defect
    defect = Defect.query.get_or_404(defect_id)
    
    # Check if model exists
    model_url = url_for('module3.serve_defect_model', defect_id=defect_id) if defect.scan_path else None
    
    return render_template(
        'module3/visualize.html', 
        scan=defect, 
        scan_id=defect.project_id if defect.project else None, # Pass project ID for other generic API calls
        house_scan_id=defect.id,
        model_url=model_url,
        project_name=defect.project.name if defect.project else 'No Project'
    )

@bp.route('/model/defect/<int:defect_id>')
@login_required
def serve_defect_model(defect_id):
    defect = Defect.query.get_or_404(defect_id)
    if not defect.scan_path:
        return "No model uploaded", 404
        
    import os
    file_path = os.path.join(current_app.root_path, 'static', defect.scan_path)
    
    if os.path.exists(file_path):
        directory = os.path.dirname(file_path)
        filename = os.path.basename(file_path)
        return send_from_directory(directory, filename)
        
    return "Model file not found", 404

# --- Dashboard & User Routes ---

@bp.route('/profile')
@login_required
def profile():
    activity_count = 0 # ActivityLog removed
    return render_template('profile.html', user=current_user, activity_count=activity_count)

@bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        current_user.full_name = request.form.get('full_name')
        current_user.email = request.form.get('email')
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('module3.profile'))
    
    taman_name = current_user.project_name if current_user.project_name else "Tiada Taman Ditetapkan"
    return render_template('settings.html', user=current_user, taman_name=taman_name)

@bp.route('/change_password', methods=['POST'])
@login_required
def change_password():
    current_pw = request.form.get('current_password')
    new_pw = request.form.get('new_password')
    confirm_pw = request.form.get('confirm_password')

    if not current_user.check_password(current_pw):
        flash('Current password is incorrect.', 'danger')
        return redirect(url_for('module3.settings'))

    if new_pw != confirm_pw:
        flash('New passwords do not match.', 'danger')
        return redirect(url_for('module3.settings'))

    current_user.set_password(new_pw)
    db.session.commit()
    
    flash('Password changed successfully!', 'success')
    return redirect(url_for('module3.profile'))

@bp.route('/dashboard')
@login_required
def dashboard():
    # 1. Role-Based Redirects
    if current_user.role == 'developer':
        return redirect(url_for('module3.developer_portal'))
    elif current_user.role == 'lawyer':
        return redirect(url_for('module3.lawyer_dashboard'))
    
    # 2. Fetch Defects for the Homeowner (Recent Activity)
    user_defects = Defect.query.filter_by(user_id=current_user.id).order_by(Defect.created_at.desc()).all()
    
    # Structure recent activity into grouped_activity
    house_scans = [d for d in user_defects if d.scan_path]
    defect_pins = [d for d in user_defects if not d.scan_path]
    
    grouped_activity = []
    
    for hs in house_scans:
        # Children are defect pins with the same project_id as the house scan
        children = [pin for pin in defect_pins if pin.project_id == hs.project_id]
        grouped_activity.append({
            'scan': hs,
            'children': children
        })
        
    # Also add any standalone pins that don't match any house scan's project_id
    handled_pin_ids = {pin.id for group in grouped_activity for pin in group['children']}
    standalone_pins = [pin for pin in defect_pins if pin.id not in handled_pin_ids]
    for sp in standalone_pins:
        grouped_activity.append({
            'scan': sp,
            'children': []
        })

    # Sort groups by scan created_at (most recent first)
    grouped_activity.sort(key=lambda g: g['scan'].created_at if g['scan'].created_at else datetime.min, reverse=True)
    
    # 3. Fetch Latest Scan (for 3D Visualizer button)
    latest_scan_defect = Defect.query.filter_by(user_id=current_user.id).filter(Defect.scan_path != None).order_by(Defect.created_at.desc()).first()
    latest_scan_id = latest_scan_defect.id if latest_scan_defect else None
    
    project_name = current_user.project.name if current_user.project else 'No Project'
    
    return render_template(
        'module3/dashboard_fixed.html', 
        projects=[], # To avoid breaking legacy references if any
        grouped_activity=grouped_activity, 
        latest_scan_id=latest_scan_id,
        defect_count=len(user_defects),
        project_name=project_name
    )

@bp.route('/developer_portal')
@login_required
def developer_portal():
    selected_project_name = request.args.get('project_name')
    
    # Group defects by Project
    from sqlalchemy import func
    
    # Get all projects
    projects_query = Project.query.all()
    
    projects_data = []
    for p in projects_query:
        # Count active defects
        count = Defect.query.filter_by(project_id=p.id).count()
        projects_data.append({
            'project_name': p.name,
            'active_count': count
        })
            
    if not selected_project_name and projects_data:
        selected_project_name = projects_data[0]['project_name']
        
    # Fetch Defects
    defects = []
    stats = {'new': 0, 'in_progress': 0, 'completed': 0, 'current_project': selected_project_name or "All Projects"}
    
    defects_query = []
    if selected_project_name:
         target_project = Project.query.filter_by(name=selected_project_name).first()
         if target_project:
             defects_query = Defect.query.filter_by(project_id=target_project.id).order_by(Defect.created_at.desc()).all()
    else:
         defects_query = Defect.query.order_by(Defect.created_at.desc()).all()

    for d in defects_query:
        if d.status in ['Reported', 'draft', 'New', 'Pending']:
            stats['new'] += 1
        elif d.status in ['in_progress', 'Processing', 'locked', 'Under Review']:
            stats['in_progress'] += 1
        elif d.status in ['completed', 'Fixed']:
            stats['completed'] += 1
            
        defects.append({
            'id': d.id,
            'full_name': d.user.full_name if d.user else "Unknown",
            'unit_no': d.location,
            'description': d.description,
            'filename': d.scan_path if d.scan_path else 'No File',
            'scan_id': d.project_id, 
            'project_name': d.project.name if d.project else "Unknown",
            'severity': d.severity,
            'status': d.status
        })

    return render_template('developer_portal.html', projects=projects_data, stats=stats, defects=defects)

@bp.route('/lawyer_dashboard')
@login_required
def lawyer_dashboard():
    # Fetch all defects for the lawyer view
    all_defects = Defect.query.order_by(Defect.created_at.desc()).all()
    
    cases = []
    for d in all_defects:
        cases.append({
            'id': d.id,
            'unit_no': d.location or "N/A",
            'project_name': d.project.name if d.project else "Unknown Project",
            'description': d.description,
            'status': d.status,
            'filename': d.scan_path if d.scan_path else None,
            'scan_id': d.project_id
        })
        
    return render_template('module3/lawyer_dashboard.html', user=current_user.full_name, cases=cases)

@bp.route('/update_status/<int:id>/<string:new_status>')
@login_required
def update_status(id, new_status):
    defect = Defect.query.get_or_404(id)
    defect.status = new_status
    

    db.session.commit()
    
    flash(f"Defect status updated to {new_status}", "success")
    return redirect(request.referrer or url_for('module3.dashboard'))

@bp.route('/evidence_report')
@login_required
def evidence_report():
    # Only fetch defects that are pins (no scan_path) 
    defect_pins = Defect.query.filter(Defect.scan_path == None).order_by(Defect.created_at.desc()).all()
    
    cases = []
    for d in defect_pins:
        # Mock an AI Confidence score based on severity for demonstration
        confidence = 85
        if d.severity == 'High':
            confidence = 94
        elif d.severity == 'Low':
            confidence = 72
            
        # Get the first image if it exists
        image_url = url_for('static', filename=d.images[0].image_path) if d.images else None
        
        cases.append({
            'id': d.id,
            'unit_no': d.location or "N/A",
            'project_name': d.project.name if d.project else "Unknown Project",
            'description': d.description,
            'element': d.element or 'Unknown',
            'severity': d.severity or 'Medium',
            'status': d.status,
            'image_url': image_url,
            'confidence': confidence,
            'scan_id': d.project_id
        })
        
    return render_template('module3/evidence_report.html', user=current_user.full_name, cases=cases)

@bp.route('/validate_all', methods=['POST'])
@login_required
def validate_all():
    flash("All cases validated and locked.", "success")
    return redirect(url_for('module3.lawyer_dashboard'))
# --- API Routes for 3D Visualizer ---

@bp.route('/api/scans/<int:project_id>/defects', methods=['GET', 'POST'])
@login_required
def api_project_defects(project_id):
    if request.method == 'GET':
        defects = Defect.query.filter_by(project_id=project_id).all()
        return jsonify([{
            'defectId': d.id,
            'x': d.x_coord or 0.0,
            'y': d.y_coord or 0.0,
            'z': d.z_coord or 0.0,
            'element': d.element or 'Unknown',
            'location': d.location or '',
            'defect_type': d.defect_type or 'Unknown',
            'severity': d.severity or 'Medium',
            'status': d.status or 'Reported',
            'description': d.description or '',
            'created_at': d.created_at.strftime('%Y-%m-%d') if d.created_at else None
        } for d in defects])
        
    if request.method == 'POST':
        if request.is_json:
            data = request.json
        else:
            data = request.form
            
        try:
            new_defect = Defect(
                project_id=project_id, # Linking to Project now
                user_id=current_user.id,
                description=data.get('description', ''),
                defect_type=data.get('defect_type', 'Unknown'),
                severity=data.get('severity', 'Medium'),
                status=data.get('status', 'Reported'),
                x_coord=float(data.get('x', 0.0)), # Ensure float
                y_coord=float(data.get('y', 0.0)),
                z_coord=float(data.get('z', 0.0)),
                location=data.get('location', '3D Pin') # Use actual input location
            )
            if 'notes' in data and hasattr(Defect, 'notes'):
                new_defect.notes = data['notes']
            db.session.add(new_defect)
            db.session.commit()
            
            if request.files:
                import uuid, os
                from werkzeug.utils import secure_filename
                from app.models import DefectImage
                files = request.files.getlist('images')
                for file in files:
                    if file and file.filename != '':
                        filename = secure_filename(file.filename)
                        unique_filename = f"{uuid.uuid4().hex}_{filename}"
                        upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'defects')
                        os.makedirs(upload_folder, exist_ok=True)
                        
                        file_path = os.path.join(upload_folder, unique_filename)
                        file.save(file_path)
                        
                        relative_path = f"uploads/defects/{unique_filename}"
                        defect_image = DefectImage(defect_id=new_defect.id, image_path=relative_path)
                        db.session.add(defect_image)
                db.session.commit()
            
            return jsonify(new_defect.to_dict()), 201
        except Exception as e:
            db.session.rollback()
            print(f"ERROR saving defect: {str(e)}")
            return jsonify({'error': str(e)}), 500

@bp.route('/api/defects/<int:defect_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def api_update_defect(defect_id):
    defect = Defect.query.get_or_404(defect_id)
    
    if request.method == 'GET':
        return jsonify({
            'defectId': defect.id,
            'element': defect.element if hasattr(defect, 'element') else 'Unknown',
            'location': defect.location,
            'defect_type': defect.defect_type if hasattr(defect, 'defect_type') else 'Unknown',
            'severity': defect.severity if hasattr(defect, 'severity') else 'Medium',
            'description': defect.description,
            'x': defect.x_coord,
            'y': defect.y_coord,
            'z': defect.z_coord,
            'status': defect.status,
            'imageUrls': [url_for('static', filename=img.image_path) for img in defect.images] if defect.images else [],
            'notes': defect.notes if hasattr(defect, 'notes') else ''
        })

    if request.method == 'PUT':
        if request.is_json:
            data = request.json
        else:
            data = request.form
            
        if 'description' in data: defect.description = data['description']
        if 'defect_type' in data and hasattr(defect, 'defect_type'): defect.defect_type = data['defect_type']
        if 'severity' in data and hasattr(defect, 'severity'): defect.severity = data['severity']
        if 'status' in data: defect.status = data['status']
        if 'location' in data: defect.location = data['location']
        if 'notes' in data and hasattr(defect, 'notes'): defect.notes = data['notes']
        
        if request.files:
            import uuid, os
            from werkzeug.utils import secure_filename
            from app.models import DefectImage
            files = request.files.getlist('images')
            for file in files:
                if file and file.filename != '':
                    filename = secure_filename(file.filename)
                    unique_filename = f"{uuid.uuid4().hex}_{filename}"
                    upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'defects')
                    os.makedirs(upload_folder, exist_ok=True)
                    
                    file_path = os.path.join(upload_folder, unique_filename)
                    file.save(file_path)
                    
                    relative_path = f"uploads/defects/{unique_filename}"
                    defect_image = DefectImage(defect_id=defect.id, image_path=relative_path)
                    db.session.add(defect_image)
                    
        db.session.commit()
        return jsonify(defect.to_dict())

    if request.method == 'DELETE':
        db.session.delete(defect)
        db.session.commit()
        return jsonify({'message': 'Deleted'})

@bp.route('/delete_project/<int:project_id>', methods=['POST'])
@login_required
def delete_project(project_id):
    # Only homeowners can delete their own project reference
    if current_user.role != 'user':
        flash("Unauthorized action.", "danger")
        return redirect(url_for('module3.list_projects'))

    project = Project.query.get_or_404(project_id)
    
    # 1. Unlink any users currently attached to this project
    linked_users = User.query.filter_by(project_id=project_id).all()
    for u in linked_users:
        u.project_id = None
    
    # 2. Delete all defects associated with this project
    defects = Defect.query.filter_by(project_id=project_id).all()
    for d in defects:
        # Delete activity logs for each defect

        # Delete the defect itself
        db.session.delete(d)
    
    # 3. Delete the project itself
    db.session.delete(project)
    db.session.commit()
    
    flash(f"Project '{project.name}' and all associated data permanently deleted.", "success")
        
    return redirect(url_for('module3.list_projects'))

@bp.route('/delete_defect/<int:defect_id>', methods=['POST'])
@login_required
def delete_defect(defect_id):
    defect = Defect.query.get_or_404(defect_id)
    
    # Check permission (Homeowner can only delete own defects)
    if current_user.role == 'user' and defect.user_id != current_user.id:
        flash("Unauthorized action.", "danger")
        return redirect(url_for('module3.dashboard'))

    # Delete related logs first

    
    db.session.delete(defect)
    db.session.commit()
    
    flash("Defect deleted successfully.", "success")
    return redirect(url_for('module3.dashboard'))


@bp.route('/download_report/<report_type>')
@login_required
def download_report(report_type):
    from flask import Response
    
    # URL of the microservice
    # It must match the module_3_reporting service name on docker network
    microservice_url = f"http://module_3_reporting:5003/module3/api/generate_report/{report_type}"
    
    try:
        lang = request.args.get('language', 'ms')
        params = {'language': lang}
        if request.args.get('user_id'):
            params['user_id'] = request.args.get('user_id')
        if request.args.get('project_id'):
            params['project_id'] = request.args.get('project_id')
            
        # Stream the PDF response back to the client
        resp = requests.get(microservice_url, params=params, stream=True)
        
        if resp.status_code == 200:
            return Response(
                resp.iter_content(chunk_size=1024),
                content_type=resp.headers.get('Content-Type', 'application/pdf'),
                headers={
                    'Content-Disposition': resp.headers.get('Content-Disposition', f'attachment; filename=report.pdf')
                }
            )
        else:
            flash(f"Failed to generate report. Microservice returned: {resp.status_code}", "danger")
            return redirect(request.referrer or url_for('module3.dashboard_homeowner'))
            
    except requests.exceptions.RequestException as e:
        flash(f"Error communicating with reporting service: {str(e)}", "danger")
        return redirect(request.referrer or url_for('module3.dashboard_homeowner'))
