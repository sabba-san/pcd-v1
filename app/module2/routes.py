from flask import Blueprint, jsonify, request, send_from_directory, abort, render_template, url_for, current_app, redirect, flash
from flask_login import login_required, current_user
from app.module3.extensions import db
from app.models import Defect, Project
import os
from datetime import datetime

# Define the Blueprint
bp = Blueprint('module2', __name__, url_prefix='/module2')

# Exempt JSON API endpoints from CSRF since they are called via JavaScript fetch()
# Forms that submit via HTML (with CSRF tokens) are NOT exempted

@bp.route('/projects', methods=['GET'])
@login_required
def list_projects():
    """List all projects in the database"""
    projects = Project.query.order_by(Project.created_at.desc()).all()

    # Enhance project data with defect counts
    projects_list = []
    for proj in projects:
        defect_count = Defect.query.filter_by(project_id=proj.id).count()

        projects_list.append({
            'id': proj.id,
            'name': proj.name,
            'created_at': proj.created_at,
            'defect_count': defect_count,
            'model_path': proj.master_model_path,
            'metadata': None  # Placeholder for metadata
        })

    return render_template('module2/projects.html', projects=projects_list)

@bp.route('/projects/<int:project_id>/visualize', methods=['GET'])
@login_required
def visualize_project(project_id):
    project = Project.query.get_or_404(project_id)
    defects = Defect.query.filter_by(project_id=project_id).all()
    model_url = url_for('module2.serve_model', project_id=project_id) if project.master_model_path else None

    # The visualization template is shared with scan-based views, so provide
    # the expected scan context and upload metadata placeholders.
    scan = project
    setattr(scan, 'model_path', project.master_model_path)
    upload_metadata = None

    return render_template('module2/visualization.html',
                          project=project,
                          project_id=project_id,
                          scan=scan,
                          scan_id=project_id,
                          model_url=model_url,
                          defects=defects,
                          upload_metadata=upload_metadata)

@bp.route('/projects/<int:project_id>/defects', methods=['GET'])
@login_required
def get_project_defects(project_id):
    project = Project.query.get_or_404(project_id)
    defects = Defect.query.filter_by(project_id=project_id).all()

    defect_list = [{
        'defectId': d.id,
        'x': d.x_coord,
        'y': d.y_coord,
        'z': d.z_coord,
        'element': d.element,
        'location': d.location,
        'defect_type': d.defect_type,
        'severity': d.severity,
        'status': d.status,
        'description': d.description,
        'created_at': d.created_at.strftime('%Y-%m-%d') if d.created_at else None
    } for d in defects]
    return jsonify(defect_list)

@bp.route('/defect/<int:defect_id>', methods=['GET'])
@login_required
def get_defect_details(defect_id):
    defect = Defect.query.get_or_404(defect_id)
    image_url = None
    if defect.images:
        image_url = f'/module2/image/{defect_id}'
    return jsonify({
        'id': defect.id,
        'element': defect.element,
        'location': defect.location,
        'defect_type': defect.defect_type,
        'severity': defect.severity,
        'description': defect.description,
        'x': defect.x_coord,
        'y': defect.y_coord,
        'z': defect.z_coord,
        'status': defect.status,
        'imageUrl': image_url,
        'notes': defect.notes
    })

@bp.route('/defect/<int:defect_id>/status', methods=['PUT'])
@login_required
def update_defect_status(defect_id):
    defect = Defect.query.get_or_404(defect_id)
    data = request.get_json()
    # Only developers can change the status
    if 'status' in data and current_user.role == 'developer':
        defect.status = data['status']
    if 'notes' in data:
        defect.notes = data['notes']
    if 'location' in data:
        defect.location = data['location']
    if 'defect_type' in data:
        defect.defect_type = data['defect_type']
    if 'severity' in data:
        defect.severity = data['severity']
    db.session.commit()
    return jsonify({'message': 'Defect updated successfully', 'status': defect.status})

@bp.route('/defect/<int:defect_id>', methods=['DELETE'])
@login_required
def delete_defect(defect_id):
    defect = Defect.query.get_or_404(defect_id)
    db.session.delete(defect)
    db.session.commit()
    return jsonify({'message': 'Defect deleted successfully'})

@bp.route('/projects/<int:project_id>/defects', methods=['POST'])
def create_defect(project_id):
    project = Project.query.get_or_404(project_id)
    data = request.get_json()
    defect = Defect(
        project_id=project_id,
        user_id=current_user.id if current_user.is_authenticated else None,
        x_coord=data.get('x', 0),
        y_coord=data.get('y', 0),
        z_coord=data.get('z', 0),
        element=data.get('element', ''),
        location=data.get('location', ''),
        defect_type=data.get('defect_type', 'Unknown'),
        severity=data.get('severity', 'Medium'),
        description=data.get('description', ''),
        status=data.get('status', 'Reported'),
        notes=data.get('notes', '')
    )
    db.session.add(defect)
    db.session.commit()
    return jsonify({'message': 'Defect created', 'defectId': defect.id}), 201

@bp.route('/projects/<int:project_id>/model', methods=['GET'])
@login_required
def serve_model(project_id):
    project = Project.query.get_or_404(project_id)
    if not project.master_model_path:
        abort(404)
    upload_dir = os.path.join(current_app.root_path, 'static')
    response = send_from_directory(upload_dir, project.master_model_path)
    response.headers['Content-Type'] = 'model/gltf-binary'
    return response

@bp.route('/image/<int:defect_id>', methods=['GET'])
@login_required
def serve_defect_image(defect_id):
    defect = Defect.query.get_or_404(defect_id)
    if not defect.images:
        abort(404)
    # Assuming first image
    image_path = defect.images[0].image_path
    upload_dir = os.path.join(current_app.root_path, 'static')
    return send_from_directory(upload_dir, image_path)

@bp.route('/insert_defect', methods=['GET', 'POST'])
@login_required
def insert_defect():
    """Legacy route for defect insertion - redirects to project list"""
    if request.method == 'POST':
        # Handle POST as before, but simplified
        try:
            x = float(request.form.get('x', 0))
            y = float(request.form.get('y', 0))
            z = float(request.form.get('z', 0))

            project_id = current_user.project_id
            if not project_id:
                flash("No project assigned. Please contact administrator.", "error")
                return redirect(url_for('module2.list_projects'))

            new_defect = Defect(
                project_id=project_id,
                user_id=current_user.id,
                description=request.form.get('description'),
                location=request.form.get('unit_no'),
                status='Reported',
                x_coord=x, y_coord=y, z_coord=z
            )
            db.session.add(new_defect)
            db.session.flush() # Get ID before commit

            # Handle 3D Lidar File
            lidar_file = request.files.get('lidar_file')
            if lidar_file and lidar_file.filename:
                import uuid
                from werkzeug.utils import secure_filename
                filename = secure_filename(lidar_file.filename)
                unique_filename = f"{uuid.uuid4().hex}_{filename}"
                upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'models')
                os.makedirs(upload_folder, exist_ok=True)
                file_path = os.path.join(upload_folder, unique_filename)
                lidar_file.save(file_path)
                new_defect.scan_path = f"uploads/models/{unique_filename}"

            db.session.commit()
            flash('Defect submitted successfully!', 'success')
            return redirect(url_for('module3.dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'danger')
            return redirect(url_for('module2.insert_defect'))

    # GET: Render the defect insertion form page directly
    return render_template('module2/insert_defect.html', defects=[])