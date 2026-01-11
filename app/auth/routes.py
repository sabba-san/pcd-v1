from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from app.db import get_db
import psycopg2.extras

bp = Blueprint('auth', __name__, url_prefix='/auth')

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        full_name = request.form['full_name']
        role = request.form['role']
        
        # Logic to determine "Organization" based on Role
        organization = None
        
        if role == 'user':
            if request.form.get('project_name_select') == 'Other':
                organization = request.form.get('custom_project_name')
            else:
                organization = request.form.get('project_name_select')       
        elif role == 'developer':
            organization = request.form.get('developer_company')    
        elif role == 'lawyer':
            organization = request.form.get('law_firm')

        hashed_pw = generate_password_hash(password)
        
        try:
            db = get_db()
            cur = db.cursor()
            cur.execute(
                "INSERT INTO users (username, password_hash, role, full_name, organization) VALUES (%s, %s, %s, %s, %s)",
                (username, hashed_pw, role, full_name, organization)
            )
            db.commit()
            cur.close()
            flash("Registration successful! Please login.", "success")
            return redirect(url_for('auth.login'))
        except Exception as e:
            print(e)
            flash(f"Error: Username might already be taken.", "error")
            return redirect(url_for('auth.register'))
    
    return render_template('auth/register.html')

@bp.route('/login', methods=['GET', 'POST'])

def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        db = get_db()
        cur = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # 1. Fetch the User AND their Organization (Project Name)
        cur.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cur.fetchone()
        cur.close()
        
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['user_role'] = user['role']
            
            # --- THE FIX IS HERE ---
            # Save the Project Name into the session so other pages can see it
            session['user_project'] = user['organization'] 
            # -----------------------
            
            return redirect(url_for('module1.dashboard'))
        else:
            flash("Invalid username or password", "error")
            
    return render_template('auth/login.html')

@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))
