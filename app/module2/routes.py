import os
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app.module3.extensions import db
from app.models import Defect, Project, DefectImage

# Define the Blueprint
bp = Blueprint('module2', __name__, url_prefix='/module2')

@bp.route('/insert_defect', methods=['GET', 'POST'])
@login_required
def insert_defect():
    if request.method == 'POST':
        try:
            # 1. Handle File Upload
            lidar_file = request.files.get('lidar_file')
            lidar_path = None
            
            if lidar_file and lidar_file.filename:
                # Save the new file
                filename = secure_filename(lidar_file.filename)
                # Ensure uploads directory exists
                upload_folder = os.path.join(current_app.root_path, 'static', 'uploads')
                os.makedirs(upload_folder, exist_ok=True)
                
                # Save file
                file_full_path = os.path.join(upload_folder, filename)
                lidar_file.save(file_full_path)
                lidar_path = f"uploads/{filename}"
                
            # 2. Get Coordinates from Form
            try:
                x = float(request.form.get('x', 0))
                y = float(request.form.get('y', 0))
                z = float(request.form.get('z', 0))
            except (ValueError, TypeError):
                x, y, z = 0.0, 0.0, 0.0

            # 3. Create the defect
            # Link to User's Project
            project_id = current_user.project_id
            
            if not project_id:
                # Auto-create project for unlinked user (fallback)
                from datetime import datetime
                project_name = f"{current_user.full_name or current_user.email}'s Park"
                
                new_project = Project(
                    name=project_name
                )
                db.session.add(new_project)
                db.session.flush()
                
                current_user.project_id = new_project.id
                project_id = new_project.id
                db.session.commit()
                flash(f"Assigned to project: {project_name}", "info")
            
            new_defect = Defect(
                project_id=project_id,
                user_id=current_user.id,
                description=request.form.get('description'),
                location=request.form.get('unit_no'),
                status='Reported',
                x_coord=x, y_coord=y, z_coord=z,
                scan_path=lidar_path # Saving the uploaded scan here
            )
            
            db.session.add(new_defect)
            db.session.flush() # Get ID
            
            # Handle multiple images
            uploaded_images = request.files.getlist('images')
            for img_file in uploaded_images:
                if img_file and img_file.filename:
                    img_filename = secure_filename(img_file.filename)
                    # Use unique names
                    from datetime import datetime
                    time_prefix = datetime.now().strftime('%Y%m%d%H%M%S_')
                    img_filename = time_prefix + img_filename
                    upload_folder = os.path.join(current_app.root_path, 'static', 'uploads')
                    os.makedirs(upload_folder, exist_ok=True)
                    
                    img_full_path = os.path.join(upload_folder, img_filename)
                    img_file.save(img_full_path)
                    
                    db.session.add(DefectImage(
                        defect_id=new_defect.id,
                        image_path=f"uploads/{img_filename}"
                    ))
            
            db.session.commit()
            
            # 5. Trigger the success message
            flash('Defect claim submitted successfully!', 'success')
            return redirect(url_for('module3.dashboard')) # Redirect to Dashboard (in Module 3 now)
            
        except Exception as e:
            db.session.rollback()
            print(f"DATABASE ERROR: {e}")
            flash(f'Error saving defect: {str(e)}', 'danger')
            return redirect(url_for('module2.insert_defect'))

    # GET Request: Fetch existing data for visualization
    # Use User's Project Master Model if available, or last defect's scan? 
    # Logic: Show Project Master Model.
    
    project = Project.query.get(current_user.project_id) if current_user.project_id else None
    
    defects = []
    model_url = None
    project_id = None
    
    if project:
        project_id = project.id
        # Use Master Model if exists
        if project.master_model_path:
             model_url = url_for('static', filename=project.master_model_path)
        
        # Fetch actual defects for this project
        defects_query = Defect.query.filter_by(project_id=project.id).all()
        # Serialize for JS
        defects = [d.to_dict() for d in defects_query]

    return render_template('module2/insert_defect.html', 
                          defects=defects, 
                          model_url=model_url, 
                          scan_id=project_id) # scan_id -> project_id in template logic eventually

@bp.route('/api/defect/add', methods=['POST'])
def api_add_defect():
    try:
        # 1. Validate File
        if 'file' not in request.files:
            return jsonify({'status': 'error', 'message': 'No file part'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'status': 'error', 'message': 'No selected file'}), 400
            
        if file:
            # 2. Save File
            filename = secure_filename(file.filename)
            upload_folder = os.path.join(current_app.root_path, 'static', 'uploads')
            os.makedirs(upload_folder, exist_ok=True)
            
            file_path = os.path.join(upload_folder, filename)
            file.save(file_path)
            
            # 3. Handle User Association
            user_id = request.form.get('user_id')
            user = None
            if user_id:
                 user = User.query.get(user_id)
            elif current_user.is_authenticated:
                 user = current_user
            
            project_id = user.project_id if user else None

            # Auto-create project for API calls if missing
            if user and not project_id:
                from datetime import datetime
                project_name = f"{user.full_name or user.email}'s Project ({datetime.now().strftime('%H%M%S')})"
                new_project = Project(name=project_name)
                db.session.add(new_project)
                db.session.flush()
                user.project_id = new_project.id
                project_id = new_project.id
                db.session.commit()

            # 5. Create Defect
            new_defect = Defect(
                project_id=project_id,
                user_id=user.id if user else None,
                description=request.form.get('description'),
                location=request.form.get('location'),
                status='Reported',
                x_coord=0, y_coord=0, z_coord=0,
                image_path=f"uploads/{filename}" # Save image path
            )
            
            db.session.add(new_defect)
            db.session.flush() # Get ID
            

            db.session.commit()
            
            return jsonify({
                'status': 'success', 
                'message': 'Defect added successfully', 
                'defect_id': new_defect.id,
                'project_id': project_id
            }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500