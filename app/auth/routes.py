from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, login_required
from app.module3.extensions import db
from app.models import User, Project # Updated Import

bp = Blueprint('auth', __name__, url_prefix='/auth')

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['username'] # Using username as email logic
        password = request.form['password']
        full_name = request.form['full_name']
        role = request.form['role']
        
        # Role Specific Fields
        ic_number = request.form.get('ic_number')
        phone_number = request.form.get('phone_number')
        correspondence_address = request.form.get('correspondence_address')
        
        company_name = request.form.get('developer_company')
        developer_ssm = request.form.get('developer_ssm')
        developer_address = request.form.get('developer_address') # Capturing address for developer too
        
        firm_name = request.form.get('law_firm')
        bar_council_id = request.form.get('bar_council_id')

        # Logic to determine and Link "Project"
        project_obj = None
        
        if role == 'user':
            selected_project = request.form.get('project_name_select')
            custom_project = request.form.get('custom_project_name')
            
            project_name = custom_project if selected_project == 'Other' else selected_project
            
            if project_name:
                # Check if project exists, else create
                project_obj = Project.query.filter_by(name=project_name).first()
                if not project_obj:
                    project_obj = Project(name=project_name)
                    # If Homeowner created it via "Other", it might lack developer details initially
                    db.session.add(project_obj)
                    db.session.flush() # Get ID

        # Check if user exists
        if User.query.filter_by(username=username).first():
            flash("Error: Username already taken.", "error")
            return redirect(url_for('auth.register'))

        new_user = User(
            username=username,
            email=email,
            full_name=full_name,
            role=role,
            
            # Homeowner
            ic_number=ic_number,
            phone_number=phone_number,
            correspondence_address=correspondence_address,
            project_id=project_obj.id if project_obj else None,
            
            # Developer
            company_name=company_name,
            company_reg_no=developer_ssm,
            company_address=developer_address, # reusing this field if we want, or map to correspondence
            
            # Lawyer
            firm_name=firm_name,
            bar_council_id=bar_council_id
        )
        new_user.set_password(password)
        
        try:
            db.session.add(new_user)
            db.session.commit()
            flash("Registration successful! Please login.", "success")
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            print(e)
            flash(f"Error: {e}", "error")
            return redirect(url_for('auth.register'))
    
    return render_template('auth/register.html')

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            
            # Optional: Keep session variables if needed by legacy code, 
            # but current_user.project_name is now available everywhere
            session['user_project'] = user.project_name 
            
            return redirect(url_for('module3.dashboard'))
        else:
            flash("Invalid username or password", "error")
            
    return render_template('auth/login.html')

@bp.route('/logout')
def logout():
    logout_user()
    session.clear()
    return redirect(url_for('auth.login'))
