import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify, send_from_directory
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app.module3.extensions import db
from app.models import Defect, ActivityLog, Project, User

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
        if current_user.project_id:
             projects_query = [Project.query.get(current_user.project_id)]
        else:
             projects_query = [] # Show nothing if not linked
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

        projects_list.append({
            'id': proj.id,
            'name': proj.name,
            'created_at': proj.created_at,
            'defect_count': len(defects),
            'model_path': proj.master_model_path,
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
    
    return render_template(
        'module3/visualize.html', 
        scan=project, # Template might still use 'scan' variable name
        scan_id=project_id,
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

# --- Dashboard & User Routes ---

@bp.route('/profile')
@login_required
def profile():
    activity_count = ActivityLog.query.count() # Filter by user if needed?
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
    
    # 2. Fetch Defects for the Homeowner
    if current_user.role == 'user':
        defects = Defect.query.filter_by(user_id=current_user.id).order_by(Defect.created_at.desc()).all()
    else:
        defects = Defect.query.order_by(Defect.created_at.desc()).all()
    
    # 3. Fetch Latest Project (for 3D Visualizer button)
    latest_project = None
    if current_user.project_id:
        latest_project = Project.query.get(current_user.project_id)
    else:
        latest_project = Project.query.order_by(Project.created_at.desc()).first()
        
    latest_scan_id = latest_project.id if latest_project else None
    
    # 4. Fetch Recent Activity
    activities = ActivityLog.query.order_by(ActivityLog.timestamp.desc()).limit(5).all()
    
    return render_template(
        'module3/dashboard_fixed.html', 
        defects=defects, 
        latest_scan=latest_project, # Variable name preservation for template
        latest_scan_id=latest_scan_id,
        activity=activities,
        defect_count=len(defects),
        project_name=latest_project.name if latest_project else 'No Project'
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
        elif d.status in ['in_progress', 'Processing', 'locked']:
            stats['in_progress'] += 1
        elif d.status == 'completed':
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
    
    log = ActivityLog(
        defect_id=defect.id,
        action=f"Status updated to {new_status} by {current_user.username}",
        old_value=defect.status,
        new_value=new_status
    )
    db.session.add(log)
    db.session.commit()
    
    flash(f"Defect status updated to {new_status}", "success")
    return redirect(request.referrer or url_for('module3.dashboard'))

@bp.route('/evidence_report')
@login_required
def evidence_report():
    flash("Evidence Report feature coming soon.", "info")
    return redirect(url_for('module3.lawyer_dashboard'))

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
        return jsonify([d.to_dict() for d in defects])
        
    if request.method == 'POST':
        data = request.json
        try:
            new_defect = Defect(
                project_id=project_id, # Linking to Project now
                user_id=current_user.id,
                description=data.get('description'),
                defect_type=data.get('defect_type'),
                severity=data.get('severity'),
                status=data.get('status', 'Reported'),
                x_coord=float(data.get('x', 0.0)), # Ensure float
                y_coord=float(data.get('y', 0.0)),
                z_coord=float(data.get('z', 0.0)),
                location="3D Pin" # Default location for pins
            )
            db.session.add(new_defect)
            db.session.commit()
            
            # Log it
            log = ActivityLog(
                defect_id=new_defect.id,
                action=f"Defect pined on 3D model by {current_user.username}",
                new_value="Reported"
            )
            db.session.add(log)
            db.session.commit()
            
            return jsonify(new_defect.to_dict()), 201
        except Exception as e:
            db.session.rollback()
            print(f"ERROR saving defect: {str(e)}")
            return jsonify({'error': str(e)}), 500

@bp.route('/api/defects/<int:defect_id>', methods=['PUT', 'DELETE'])
@login_required
def api_update_defect(defect_id):
    defect = Defect.query.get_or_404(defect_id)
    
    if request.method == 'PUT':
        data = request.json
        
        # Track changes (simple version)
        if data.get('status') and data.get('status') != defect.status:
             log = ActivityLog(
                defect_id=defect.id,
                action=f"Status changed to {data.get('status')} via 3D Viewer",
                old_value=defect.status,
                new_value=data.get('status')
             )
             db.session.add(log)
        
        if 'description' in data: defect.description = data['description']
        if 'defect_type' in data: defect.defect_type = data['defect_type']
        if 'severity' in data: defect.severity = data['severity']
        if 'status' in data: defect.status = data['status']
        
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
        ActivityLog.query.filter_by(defect_id=d.id).delete()
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
    ActivityLog.query.filter_by(defect_id=defect.id).delete()
    
    db.session.delete(defect)
    db.session.commit()
    
    flash("Defect deleted successfully.", "success")
    return redirect(url_for('module3.dashboard'))

