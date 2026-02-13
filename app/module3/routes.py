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
    # Filter projects by the current user
    scans = Scan.query.filter_by(user_id=current_user.id).order_by(Scan.created_at.desc()).all()
    
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

# Defect insertion logic moved to Module 2

# Defect API logic moved to Module 2

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

# --- Dashboard & User Routes (Merged from Module 1) ---
# Note: Ensure these routes use the module3 blueprint ('bp') defined at the top of this file.

# 1. PROFILE VIEW (Read Only)
@bp.route('/profile')
@login_required
def profile():
    # Fetching count of activity logs
    activity_count = ActivityLog.query.count() 
    return render_template('profile.html', user=current_user, activity_count=activity_count)

# 2. SETTINGS (Update Name/Email)
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

# 3. PASSWORD CHANGE (Security logic)
@bp.route('/change_password', methods=['POST'])
@login_required
def change_password():
    current_pw = request.form.get('current_password')
    new_pw = request.form.get('new_password')
    confirm_pw = request.form.get('confirm_password')

    # Verification checks
    if not current_user.check_password(current_pw):
        flash('Current password is incorrect.', 'danger')
        return redirect(url_for('module3.settings'))

    if new_pw != confirm_pw:
        flash('New passwords do not match.', 'danger')
        return redirect(url_for('module3.settings'))

    # Hashing and saving
    current_user.set_password(new_pw)
    db.session.commit()
    
    flash('Password changed successfully!', 'success')
    return redirect(url_for('module3.profile'))

# 4. DASHBOARDS
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
    
    # 3. Fetch Latest Scan (for 3D Visualizer button)
    from app.module3.models import Scan
    latest_scan = Scan.query.order_by(Scan.created_at.desc()).first()
    
    # 4. Fetch Recent Activity
    # This pulls the log entries created by your 'insert_defect' route
    activities = ActivityLog.query.order_by(ActivityLog.timestamp.desc()).limit(5).all()
    
    # 5. Render the Dashboard with the data
    return render_template(
        'dashboard.html', 
        defects=defects, 
        latest_scan=latest_scan,
        activity=activities
    )
@bp.route('/developer_portal')
@login_required
def developer_portal():
    # 1. Get Selected Project from Query Params (default to first available if None)
    selected_project = request.args.get('project_name')
    
    # 2. Get Statistics for Projects
    # We want to group defects by User.project_name
    from sqlalchemy import func
    from app.module3.models import User # Ensure User is imported if not already avilable via relationship
    
    # Get all unique project names from Users who are homeowners
    projects_query = db.session.query(
        User.project_name, 
        func.count(Defect.id)
    ).join(Defect, User.id == Defect.user_id)\
     .filter(User.role == 'user')\
     .group_by(User.project_name).all()
    
    projects = []
    for p_name, count in projects_query:
        if p_name: # Filter out None
            projects.append({
                'project_name': p_name,
                'active_count': count
            })
            
    # Set default selected project
    if not selected_project and projects:
        selected_project = projects[0]['project_name']
        
    # 3. Fetch Defects for the Selected Project
    defects = []
    stats = {'new': 0, 'in_progress': 0, 'completed': 0, 'current_project': selected_project or "All Projects"}
    
    if selected_project:
        # Join User to filter by project_name
        defects_query = Defect.query.join(User).filter(User.project_name == selected_project).order_by(Defect.created_at.desc()).all()
    else:
        # Fallback: Show all if no projects found
        defects_query = Defect.query.order_by(Defect.created_at.desc()).all()

    for d in defects_query:
        # Calculate Stats
        if d.status in ['Reported', 'draft', 'New']:
            stats['new'] += 1
        elif d.status in ['in_progress', 'Processing', 'locked']:
            stats['in_progress'] += 1
        elif d.status == 'completed':
            stats['completed'] += 1
            
        # Format for Template
        defects.append({
            'id': d.id,
            'full_name': d.user.full_name if d.user else "Unknown",
            'unit_no': d.location, # Using location as unit_no
            'description': d.description,
            'filename': d.scan.model_path if d.scan else 'No File',
            'scan_id': d.scan_id, # ADDED scan_id
            'project_name': d.user.project_name if d.user else "Unknown",
            'severity': d.severity,
            'status': d.status
        })

    return render_template('developer_portal.html', projects=projects, stats=stats, defects=defects)

@bp.route('/lawyer_dashboard')
@login_required
def lawyer_dashboard():
    # Fetch all defects for the lawyer view (Cases)
    all_defects = Defect.query.order_by(Defect.created_at.desc()).all()
    
    cases = []
    for d in all_defects:
        cases.append({
            'id': d.id,
            'unit_no': d.location or "N/A",
            'project_name': d.user.project_name if d.user else "Unknown Project",
            'description': d.description,
            'status': d.status,
            'filename': d.scan.model_path if d.scan else None,
            'scan_id': d.scan_id # ADDED scan_id
        })
        
    return render_template('module3/lawyer_dashboard.html', user=current_user.full_name, cases=cases)

# --- Missing Routes for Templates ---

@bp.route('/update_status/<int:id>/<string:new_status>')
@login_required
def update_status(id, new_status):
    defect = Defect.query.get_or_404(id)
    # Check permissions? For now assume Developer/Lawyer can update
    defect.status = new_status
    
    # Log activity
    log = ActivityLog(
        defect_id=defect.id,
        scan_id=defect.scan_id,
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
    # Placeholder for Evidence Report
    flash("Evidence Report feature coming soon.", "info")
    return redirect(url_for('module3.lawyer_dashboard'))

@bp.route('/validate_all', methods=['POST'])
@login_required
def validate_all():
    # Placeholder for locking all cases
    flash("All cases validated and locked.", "success")
    return redirect(url_for('module3.lawyer_dashboard'))