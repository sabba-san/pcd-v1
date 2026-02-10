from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, login_required
from app.module3.extensions import db
from app.module3.models import User

bp = Blueprint('auth', __name__, url_prefix='/auth')

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['username'] # Using username as email logic
        password = request.form['password']
        full_name = request.form['full_name']
        role = request.form['role']
        
        # Logic to determine "Project Name"
        project_name = None
        
        if role == 'user':
            if request.form.get('project_name_select') == 'Other':
                project_name = request.form.get('custom_project_name')
            else:
                project_name = request.form.get('project_name_select')       
        elif role == 'developer':
            project_name = request.form.get('developer_company')    
        elif role == 'lawyer':
            project_name = request.form.get('law_firm')

        # Check if user exists
        if User.query.filter_by(username=username).first():
            flash("Error: Username already taken.", "error")
            return redirect(url_for('auth.register'))

        new_user = User(
            username=username,
            email=email,
            full_name=full_name,
            role=role,
            project_name=project_name
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
