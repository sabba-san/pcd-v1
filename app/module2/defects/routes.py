from flask import Blueprint, jsonify, request, send_from_directory, abort, render_template, url_for, current_app
from flask_login import login_required, current_user
from app.module3.extensions import db
from app.models import Defect, Project
from app.utils import load_upload_metadata
import os
from datetime import datetime

defects_bp = Blueprint('defects', __name__)

# Exempt JSON API endpoints from CSRF since they are called via JavaScript fetch()
# Forms that submit via HTML (with CSRF tokens) are NOT exempted

@defects_bp.route('/projects', methods=['GET'])
@login_required
def list_projects():
    """List all projects in the database"""
    projects = Project.query.order_by(Project.created_at.desc()).all()
    
    # Enhance project data with defect counts and metadata
    project_list = []
    for project in projects:
        defect_count = Defect.query.filter_by(project_id=project.id).count()
        
        metadata = load_upload_metadata(project.id)
        
        project_list.append({
            'id': project.id,
            'name': project.name,
            'created_at': project.created_at,
            'defect_count': defect_count,
            'model_path': project.master_model_path,
            'metadata': metadata
        })
    
    return render_template('defects/projects.html', projects=project_list)

@defects_bp.route('/scans/<int:scan_id>/visualize', methods=['GET'])
@login_required
def visualize_scan(scan_id):
    project = Project.query.get_or_404(scan_id)
    defects = Defect.query.filter_by(project_id=scan_id).all()
    model_url = url_for('defects.serve_model', scan_id=scan_id) if project.master_model_path else None
    project.model_path = project.master_model_path
    
    upload_metadata = load_upload_metadata(scan_id)
    
    return render_template('defects/visualization.html', 
                          scan=project, 
                          scan_id=scan_id, 
                          model_url=model_url, 
                          defects=defects,
                          upload_metadata=upload_metadata)

@defects_bp.route('/scans/<int:scan_id>/defects', methods=['GET'])
@login_required
def get_scan_defects(scan_id):
    project = Project.query.get_or_404(scan_id)
    defects = Defect.query.filter_by(project_id=scan_id).all()
    
    metadata = load_upload_metadata(scan_id)
    upload_date = metadata.get('scan_date') if metadata else None
    
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
        'created_at': upload_date if upload_date else (d.created_at.strftime('%Y-%m-%d') if d.created_at else None)
    } for d in defects]
    return jsonify(defect_list)

@defects_bp.route('/defect/<int:defect_id>', methods=['GET'])
@login_required
def get_defect_details(defect_id):
    defect = Defect.query.get_or_404(defect_id)
    image_url = None
    if defect.images:
        image_url = f'/defects/image/{defect_id}'
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

@defects_bp.route('/defect/<int:defect_id>/status', methods=['PUT'])
@login_required
def update_defect_status(defect_id):
    defect = Defect.query.get_or_404(defect_id)
    data = request.get_json()
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

@defects_bp.route('/defect/<int:defect_id>', methods=['DELETE'])
@login_required
def delete_defect(defect_id):
    defect = Defect.query.get_or_404(defect_id)
    db.session.delete(defect)
    db.session.commit()
    return jsonify({'message': 'Defect deleted successfully'})

@defects_bp.route('/scans/<int:scan_id>/defects', methods=['POST'])
@login_required
def create_defect(scan_id):
    project = Project.query.get_or_404(scan_id)
    data = request.get_json()
    defect = Defect(
        project_id=scan_id,
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

@defects_bp.route('/scans/<int:scan_id>/model', methods=['GET'])
@login_required
def serve_model(scan_id):
    project = Project.query.get_or_404(scan_id)
    if not project.master_model_path:
        abort(404)
    upload_dir = os.path.join(current_app.root_path, 'static')
    response = send_from_directory(upload_dir, project.master_model_path)
    response.headers['Content-Type'] = 'model/gltf-binary'
    return response

@defects_bp.route('/defects/image/<int:defect_id>', methods=['GET'])
@login_required
def serve_defect_image(defect_id):
    defect = Defect.query.get_or_404(defect_id)
    if not defect.images:
        abort(404)
    image_path = defect.images[0].image_path
    upload_dir = os.path.join(current_app.root_path, 'static')
    return send_from_directory(upload_dir, image_path)

@defects_bp.route('/project/<int:scan_id>', methods=['GET'])
@login_required
def view_project(scan_id):
    project = Project.query.get_or_404(scan_id)
    defects = Defect.query.filter_by(project_id=scan_id).all()
    model_url = url_for('defects.serve_model', scan_id=scan_id) if project.master_model_path else None
    project.model_path = project.master_model_path
    
    upload_metadata = load_upload_metadata(scan_id)
    
    return render_template('defects/project_detail.html', 
                          scan=project, 
                          scan_id=scan_id, 
                          model_url=model_url, 
                          defects=defects,
                          upload_metadata=upload_metadata)