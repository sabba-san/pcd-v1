import sys
import os
print(f"Python path: {sys.path}", file=sys.stderr)

from flask import Flask

# Allow importing from centralized app models
sys.path.append(os.environ.get("PYTHONPATH_MAIN", "/usr/src/app_main"))

def create_app():
    app = Flask(__name__)
    
    # Configure database
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
        'DATABASE_URL', 
        'postgresql://user:password@flask_db:5432/flaskdb'
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    try:
        from app.module3.extensions import db
        db.init_app(app)
        print("Database initialized successfully", file=sys.stderr)
    except Exception as e:
        print(f"Failed to initialize database: {e}", file=sys.stderr)

    with app.app_context():
        # Register blueprints from micro_app.module3
        for mod in ["module3"]:
            try:
                module = __import__(f"micro_app.{mod}.routes", fromlist=["bp", "routes"])
                bp = getattr(module, "bp", None) or getattr(module, "routes", None)
                if bp:
                    app.register_blueprint(bp, url_prefix=f"/{mod}")
                    print(f"Registered blueprint for {mod}", file=sys.stderr)
                else:
                    print(f"No blueprint 'bp' or 'routes' found in micro_app.{mod}.routes", file=sys.stderr)
            except Exception as e:
                print(f"Failed to import/register blueprint for {mod}: {e}", file=sys.stderr)

    return app

app = create_app()
print(f"App created successfully: {app}", file=sys.stderr)