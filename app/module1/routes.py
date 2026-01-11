from flask import Blueprint, render_template, session, redirect, url_for, flash, request
from werkzeug.security import check_password_hash, generate_password_hash
from app.db import get_db
import psycopg2.extras

bp = Blueprint('module1', __name__, url_prefix='/')

# --- DASHBOARD ---
@bp.route('/dashboard')
def dashboard():
    # Security: Kick out guests
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    # 1. Fetch User's Real Defects from DB
    db = get_db()
    cur = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    cur.execute("""
        SELECT * FROM defects 
        WHERE user_id = %s 
        ORDER BY created_at DESC 
        LIMIT 5
    """, (session['user_id'],))
    
    my_defects = cur.fetchall()
    cur.close()

    return render_template('dashboard.html', defects=my_defects)

# --- PROFILE ---
@bp.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    db = get_db()
    cur = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    # Get user details
    cur.execute("SELECT * FROM users WHERE id = %s", (session['user_id'],))
    user_info = cur.fetchone()
    
    # Get count of their defects
    cur.execute("SELECT COUNT(*) FROM defects WHERE user_id = %s", (session['user_id'],))
    defect_count = cur.fetchone()[0]
    
    cur.close()

    # Note: 'profile.html' is in the main templates folder
    return render_template('profile.html', user=user_info, activity_count=defect_count)

# --- SETTINGS (Placeholder) ---
@bp.route('/settings')
def settings():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    return render_template('settings.html')

# --- HANDLE PASSWORD CHANGE ---
@bp.route('/settings/password', methods=['POST'])
def change_password():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    current_pw = request.form.get('current_password')
    new_pw = request.form.get('new_password')
    confirm_pw = request.form.get('confirm_password')

    if new_pw != confirm_pw:
        flash("New passwords do not match.", "error")
        return redirect(url_for('module1.settings'))

    db = get_db()
    cur = db.cursor(cursor_factory=psycopg2.extras.DictCursor)

    # 1. Get current password hash
    cur.execute("SELECT password_hash FROM users WHERE id = %s", (session['user_id'],))
    user = cur.fetchone()

    # 2. Verify Old Password
    if not user or not check_password_hash(user['password_hash'], current_pw):
        flash("Incorrect current password.", "error")
        cur.close()
        return redirect(url_for('module1.settings'))

    # 3. Update to New Password
    new_hash = generate_password_hash(new_pw)
    cur.execute("UPDATE users SET password_hash = %s WHERE id = %s", (new_hash, session['user_id']))
    db.commit()
    cur.close()

    flash("Password updated successfully!", "success")
    return redirect(url_for('module1.settings'))