from flask import Flask
from app.db import close_db 
def create_app():
    app = Flask(__name__)
    
    # REQUIRED for session to work (keeps users logged in)
    app.config['SECRET_KEY'] = 'dev_secret_key_123'
     
    # --- ADD THIS LINE HERE ---
    # Database init (Legacy Raw SQL)
    from app.db import init_app
    init_app(app)
    
    # Database init (SQLAlchemy)
    from app.module3.extensions import db
    # Configure DB Connection for SQLAlchemy
    app.config['SQLALCHEMY_DATABASE_URI'] = f"postgresql://user:password@flask_db:5432/flaskdb"
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    
    # --- FLASK LOGIN SETUP ---
    from flask_login import LoginManager
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)
    
    from app.module3.models import User
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    # -------------------------
    # --------------------------
    

    
    # 1. Register Login / Dashboard
    # --- SERVICE ISOLATION ---
    import os
    service_type = os.getenv('SERVICE_TYPE', 'web') # Default to 'web'
    
    if service_type == 'chatbot':
        # 1. Register Chatbot (Module 1)
        from app.module1.routes import bp as module1_bp
        app.register_blueprint(module1_bp)
        print("Starting CHATBOT Service (Module 1 only)")
        
    else:
        # Default / Web Service
        # --- NEW: Register Auth (Login/Register) ---
        from app.auth.routes import bp as auth_bp
        app.register_blueprint(auth_bp)
        # -------------------------------------------
        
        # 2. Register Defect Form (Module 2)
        from app.module2.routes import bp as module2_bp
        app.register_blueprint(module2_bp)

        # 3. Register Reporting & Dashboard (Module 3)
        from app.module3.routes import bp as module3_bp
        app.register_blueprint(module3_bp)
        
        print("Starting WEB Service (Modules 2 & 3)")

    # Root Redirect
    from flask import redirect, url_for
    @app.route('/')
    def index():
        if service_type == 'chatbot':
             return "Chatbot Service Running"
        return redirect(url_for('auth.login'))  # <--- Make sure this says 'auth.login'
    
    return app