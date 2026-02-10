import sys
print(f"Python path: {sys.path}", file=sys.stderr)

from flask import Flask

def create_app():
    app = Flask(__name__)

    with app.app_context():
        # Register blueprints from module1..module4 if present
        for mod in ("module1", "module2", "module3", "module4"):
            try:
                module = __import__(f"app.{mod}.routes", fromlist=["bp"])
                bp = getattr(module, "bp", None)
                if bp:
                    app.register_blueprint(bp)
                else:
                    print(f"No blueprint 'bp' found in app.{mod}.routes", file=sys.stderr)
            except Exception as e:
                print(f"Failed to import/register blueprint for {mod}: {e}", file=sys.stderr)

    return app

app = create_app()
print(f"App created successfully: {app}", file=sys.stderr)