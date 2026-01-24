from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from app.module3.extensions import db
from app.module3.models import Defect, ActivityLog 

bp = Blueprint('module1', __name__, url_prefix='/')

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
        return redirect(url_for('module1.profile'))
    
    return render_template('settings.html', user=current_user)

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
        return redirect(url_for('module1.settings'))

    if new_pw != confirm_pw:
        flash('New passwords do not match.', 'danger')
        return redirect(url_for('module1.settings'))

    # Hashing and saving
    current_user.set_password(new_pw)
    db.session.commit()
    
    flash('Password changed successfully!', 'success')
    return redirect(url_for('module1.profile'))

# 4. DASHBOARDS
@bp.route('/dashboard')
@login_required
def dashboard():
    # 1. Role-Based Redirects
    if current_user.role == 'developer':
        return redirect(url_for('module1.developer_portal'))
    elif current_user.role == 'lawyer':
        return redirect(url_for('module1.lawyer_dashboard'))
    
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
    return render_template('developer_portal.html', projects=[], stats={}, defects=[])

@bp.route('/lawyer_dashboard')
@login_required
def lawyer_dashboard():
    return render_template('module1/lawyer_dashboard.html', user=current_user.full_name, cases=[])