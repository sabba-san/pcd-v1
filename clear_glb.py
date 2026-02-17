from app import create_app
from app.module3.extensions import db
from app.models import Project
import os

app = create_app()

with app.app_context():
    print("Starting GLB cleanup...")
    projects = Project.query.all()
    count = 0
    
    # 1. Clear Project Models
    print(f"Found {len(projects)} projects.")
    for p in projects:
        if p.master_model_path:
            # Construct full path. DB stores relative path like 'uploads/file.glb'
            # app.root_path is /usr/src/app/app
            full_path = os.path.join(app.root_path, 'static', p.master_model_path)
            print(f"Processing Project [{p.name}]: {p.master_model_path}")
            
            if os.path.exists(full_path):
                try:
                    os.remove(full_path)
                    print(f"  [DELETED] {full_path}")
                except Exception as e:
                    print(f"  [ERROR] Could not delete {full_path}: {e}")
            else:
                print(f"  [NOT FOUND] File does not exist at {full_path}")
            
            p.master_model_path = None
            count += 1
            
    # 2. Commit DB Changes
    db.session.commit()
    print(f"Successfully removed GLB references from {count} projects.")
    
    # 3. Optional: Clean up any orphaned files in uploads directory
    uploads_dir = os.path.join(app.root_path, 'static', 'uploads')
    if os.path.exists(uploads_dir):
        print(f"Scanning {uploads_dir} for orphaned .glb files...")
        for filename in os.listdir(uploads_dir):
            if filename.endswith('.glb'):
                file_path = os.path.join(uploads_dir, filename)
                try:
                    os.remove(file_path)
                    print(f"  [ORPHAN REMOVED] {filename}")
                except Exception as e:
                    print(f"  [ERROR] Could not remove orphan {filename}: {e}")
