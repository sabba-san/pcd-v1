# __init__.py
from flask import Flask, render_template  # <--- Added render_template here
from .routes import bp as module1

def create_app():
    app = Flask(__name__, static_folder='static', template_folder='templates')
    app.register_blueprint(module1)
    
    @app.route('/')
    def index():
        return render_template('index.html')
    
    return app

# <--- Add this line at the very bottom!
app = create_app()