import sys
sys.path.append('/usr/src/app_main')
from app import create_app
from app.models import User, Project
app = create_app()
with app.app_context():
    devs = User.query.filter_by(role='developer').all()
    for d in devs:
        print(f"ID: {d.id}, project_id: {d.project_id}")
