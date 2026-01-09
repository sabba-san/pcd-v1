from flask import Blueprint, render_template, request, redirect, url_for, session, g, flash
import sqlite3
import os

bp = Blueprint('module1', __name__)

# --- DATABASE CONFIG ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATABASE = os.path.join(BASE_DIR, 'app.db')

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
        
        # --- 1. AUTO-CREATE TABLES ---
        db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                full_name TEXT NOT NULL,
                role TEXT DEFAULT 'user',
                project_name TEXT
            )
        ''')

        db.execute('''
            CREATE TABLE IF NOT EXISTS defects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                project_name TEXT,
                unit_no TEXT,
                description TEXT,
                status TEXT DEFAULT 'draft',
                severity TEXT DEFAULT 'Low',
                filename TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')
        
        # --- 2. AUTO-SEED USERS (CLEAN VERSION) ---
        cursor = db.cursor()
        
        # Abbas (Homeowner)
        cursor.execute("SELECT * FROM users WHERE email = 'abbas@student.uum.edu.my'")
        if not cursor.fetchone():
            db.execute("INSERT INTO users (email, password, full_name, role, project_name) VALUES (?, ?, ?, ?, ?)",
                       ('abbas@student.uum.edu.my', 'password123', 'Abbas Abu Dzarr', 'user', 'ASMARINDA12'))

        # Developer
        cursor.execute("SELECT * FROM users WHERE email = 'developer@ecoworld.com'")
        if not cursor.fetchone():
            db.execute("INSERT INTO users (email, password, full_name, role, project_name) VALUES (?, ?, ?, ?, ?)",
                       ('developer@ecoworld.com', 'dev123', 'EcoWorld Contractor', 'developer', 'ALL'))

        # Lawyer
        cursor.execute("SELECT * FROM users WHERE email = 'lawyer@firm.com'")
        if not cursor.fetchone():
            db.execute("INSERT INTO users (email, password, full_name, role, project_name) VALUES (?, ?, ?, ?, ?)",
                       ('lawyer@firm.com', 'law123', 'Pn. Zulaikha', 'lawyer', 'ALL'))

        # Admin
        cursor.execute("SELECT * FROM users WHERE email = 'admin@uum.edu.my'")
        if not cursor.fetchone():
            db.execute("INSERT INTO users (email, password, full_name, role, project_name) VALUES (?, ?, ?, ?, ?)",
                       ('admin@uum.edu.my', 'admin123', 'System Administrator', 'admin', 'ALL'))

        db.commit()

    return db

@bp.teardown_request
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# --- AUTHENTICATION ---

@bp.route('/login', methods=['GET'])
def login_ui():
    return render_template('login.html')

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        full_name = request.form.get('full_name')
        role = request.form.get('role')
        
        # Determine the "Project/Organization" based on Role
        final_project_name = "General" # Default

        if role == 'user':
            # Homeowner Logic
            selected_proj = request.form.get('project_name_select')
            if selected_proj == 'Other':
                final_project_name = request.form.get('custom_project_name')
            else:
                final_project_name = selected_proj
        
        elif role == 'developer':
            # Developer Logic -> Company Name
            final_project_name = request.form.get('developer_company')
            
        elif role == 'lawyer':
            # Lawyer Logic -> Law Firm Name
            final_project_name = request.form.get('law_firm')
        
        db = get_db()
        try:
            db.execute('INSERT INTO users (email, password, full_name, role, project_name) VALUES (?, ?, ?, ?, ?)',
                       (email, password, full_name, role, final_project_name))
            db.commit()
            return redirect(url_for('module1.login_ui'))
        except sqlite3.IntegrityError:
            return "Email already exists! <a href='/login'>Try logging in</a>."
            
    return render_template('register.html')

@bp.route('/auth', methods=['POST'])
def login_auth():
    email = request.form.get('email')
    password = request.form.get('password')
    db = get_db()
    cur = db.execute('SELECT * FROM users WHERE email = ? AND password = ?', (email, password))
    user = cur.fetchone()
    
    if user:
        session['user_id'] = user['id']
        session['user_role'] = user['role']
        session['user_name'] = user['full_name']
        session['user_project'] = user['project_name'] 
        
        # Redirect based on Role
        if user['role'] == 'developer': return redirect(url_for('module1.developer_portal'))
        elif user['role'] == 'lawyer': return redirect(url_for('module1.lawyer_dashboard'))
        elif user['role'] == 'admin': return redirect(url_for('module1.admin_dashboard'))
        else: return redirect(url_for('module1.dashboard'))
    else:
        return "Invalid Credentials. <a href='/login'>Try Again</a>"

@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('module1.login_ui'))

# --- NEW: PROFILE & SETTINGS ROUTES ---

@bp.route('/profile')
def profile():
    if 'user_id' not in session: return redirect(url_for('module1.login_ui'))
    db = get_db()
    
    # 1. Fetch User Data as 'account' (renamed to avoid conflict)
    account_data = db.execute("SELECT * FROM users WHERE id = ?", (session['user_id'],)).fetchone()
    
    # 2. Fetch Activity Stats
    if session.get('user_role') == 'user':
        defects_count = db.execute("SELECT COUNT(*) FROM defects WHERE user_id = ?", (session['user_id'],)).fetchone()[0]
    else:
        defects_count = db.execute("SELECT COUNT(*) FROM defects").fetchone()[0]
    
    # 3. Pass 'user' (String) for Navbar, and 'account' (Object) for Profile Page
    return render_template('profile.html', 
                           user=session.get('user_name'), 
                           account=account_data, 
                           defects_count=defects_count)

@bp.route('/settings')
def settings():
    if 'user_id' not in session: return redirect(url_for('module1.login_ui'))
    return render_template('settings.html', user=session.get('user_name'))

@bp.route('/settings/change_password', methods=['POST'])
def change_password():
    if 'user_id' not in session: return redirect(url_for('module1.login_ui'))
    
    current_pw = request.form.get('current_password')
    new_pw = request.form.get('new_password')
    confirm_pw = request.form.get('confirm_password')
    
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id = ?", (session['user_id'],)).fetchone()
    
    # Validation
    if user['password'] != current_pw:
        flash("Incorrect current password!", "danger")
    elif new_pw != confirm_pw:
        flash("New passwords do not match!", "danger")
    else:
        db.execute("UPDATE users SET password = ? WHERE id = ?", (new_pw, session['user_id']))
        db.commit()
        flash("Password updated successfully!", "success")
        
    return redirect(url_for('module1.settings'))

# --- DASHBOARDS ---

@bp.route('/dashboard')
def dashboard():
    role = session.get('user_role')
    if role == 'developer': return redirect(url_for('module1.developer_portal'))
    if role == 'lawyer': return redirect(url_for('module1.lawyer_dashboard'))
    if 'user_id' not in session: return redirect(url_for('module1.login_ui'))

    db = get_db()
    # Fetch ONLY logged-in user's defects
    cur = db.execute("SELECT * FROM defects WHERE user_id = ? ORDER BY id DESC LIMIT 5", (session['user_id'],))
    recent_defects = cur.fetchall()
    
    return render_template('dashboard.html', user=session.get('user_name'), defects=recent_defects)

@bp.route('/developer-portal')
def developer_portal():
    if session.get('user_role') != 'developer': return redirect(url_for('module1.login_ui'))
    
    db = get_db()
    selected_project = request.args.get('project_name')
    
    # Sidebar Stats
    cur_projects = db.execute("""
        SELECT project_name, 
               COUNT(*) as total, 
               SUM(CASE WHEN status != 'completed' THEN 1 ELSE 0 END) as active_count 
        FROM defects 
        GROUP BY project_name
    """)
    projects_raw = cur_projects.fetchall()
    
    if not selected_project and projects_raw: selected_project = projects_raw[0]['project_name']
    
    # --- UPDATED QUERY: Join Users & Show ALL statuses (including drafts) ---
    query = """
        SELECT defects.*, users.full_name 
        FROM defects 
        LEFT JOIN users ON defects.user_id = users.id
        WHERE 1=1
    """
    params = []
    
    if selected_project:
        query += " AND defects.project_name = ?"
        params.append(selected_project)
    
    cur_defects = db.execute(query, params)
    defects = cur_defects.fetchall()
    
    processed_defects = [dict(d) for d in defects]
    
    def get_severity_score(d):
        desc = d['description'].lower() if d['description'] else ""
        if 'leak' in desc or 'structural' in desc: return 0 
        if 'crack' in desc: return 1
        return 2 
    processed_defects.sort(key=get_severity_score)
    
    # Update Stats to include 'draft' as 'new'
    stats = {
        'new': sum(1 for d in processed_defects if d['status'] in ['locked', 'draft']),
        'in_progress': sum(1 for d in processed_defects if d['status'] == 'in_progress'),
        'completed': sum(1 for d in processed_defects if d['status'] == 'completed'),
        'current_project': selected_project or "All"
    }
    
    return render_template('developer_portal.html', 
                           user=session.get('user_name'), 
                           projects=projects_raw, 
                           defects=processed_defects, 
                           stats=stats)
@bp.route('/lawyer_dashboard')
def lawyer_dashboard():
    if session.get('user_role') != 'lawyer': return redirect(url_for('module1.login_ui'))
    db = get_db()
    cur = db.execute('SELECT * FROM defects')
    cases = cur.fetchall()
    return render_template('module1/lawyer_dashboard.html', cases=cases, user=session.get('user_name'))

@bp.route('/update_status/<int:id>/<string:new_status>')
def update_status(id, new_status):
    if session.get('user_role') != 'developer': return redirect(url_for('module1.login_ui'))
    db = get_db()
    db.execute("UPDATE defects SET status = ? WHERE id = ?", (new_status, id))
    db.commit()
    return redirect(url_for('module1.developer_portal'))

@bp.route('/admin')
def admin_dashboard():
    return render_template('admin_preview.html', user="System Administrator")

# --- UPDATE THIS FUNCTION IN app/module1/routes.py ---

@bp.route('/projects')
def my_projects():
    if session.get('user_role') == 'developer':
        return redirect(url_for('module1.developer_portal'))
    
    if 'user_id' not in session: return redirect(url_for('module1.login_ui'))
    
    db = get_db()
    projects_list = []
    
    # 1. FETCH DATABASE PROJECTS
    # --------------------------
    cur = db.execute("SELECT * FROM defects WHERE user_id = ? ORDER BY created_at DESC", (session['user_id'],))
    rows = cur.fetchall()
    
    # Track filenames we found in DB so we don't list them twice
    db_filenames = set()

    for row in rows:
        db_filenames.add(row['filename'])
        projects_list.append({
            'name': row['project_name'],
            'id': row['id'],
            'status': row['status'].title(),
            'date': row['created_at'].split(' ')[0] if row['created_at'] else 'N/A',
            'unit': row['unit_no'],
            'address': row['description'][:50] + "..." if row['description'] else "No description",
            'defects': 1,
            'filename': row['filename']
        })
    
   

    # 3. RENDER THE LIST
    return render_template('module1/projects.html', 
                           user=session.get('user_name'), 
                           projects=projects_list)