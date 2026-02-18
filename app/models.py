from app.module3.extensions import db
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class Project(db.Model):
    """Represents a Housing Area / Development Project"""
    __tablename__ = 'projects'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True) # e.g. 'Taman Merpauh'
    
    # Developer Details
    developer_name = db.Column(db.String(100))
    developer_ssm = db.Column(db.String(50))
    developer_address = db.Column(db.Text)
    
    # Master 3D Model (Replaces 'Scan' logic for the whole project)
    master_model_path = db.Column(db.String(500)) 
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    users = db.relationship('User', backref='project', lazy=True)
    defects = db.relationship('Defect', backref='project', lazy=True, cascade="all, delete-orphan")

class User(UserMixin, db.Model):
    """Unified User Model"""
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), default='homeowner') # 'homeowner', 'developer', 'lawyer'
    
    # --- Role Specific Fields ---
    
    # Homeowner
    full_name = db.Column(db.String(100)) # As per IC
    ic_number = db.Column(db.String(20))
    phone_number = db.Column(db.String(20))
    correspondence_address = db.Column(db.Text)
    
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=True) # Link to their housing area
    
    # Developer
    company_name = db.Column(db.String(100))
    company_reg_no = db.Column(db.String(50)) # SSM
    company_address = db.Column(db.Text)
    
    # Lawyer
    firm_name = db.Column(db.String(100))
    bar_council_id = db.Column(db.String(50))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def project_name(self):
        # Backward compatibility helper
        return self.project.name if self.project else None

class Defect(db.Model):
    """The Bridge between 3D Data and Reporting"""
    __tablename__ = 'defects'
    id = db.Column(db.Integer, primary_key=True)
    
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    user = db.relationship('User', backref='defects', lazy=True)
    
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=True)
    
    # Module 2 Data (3D & Location)
    image_path = db.Column(db.String(500)) 
    scan_path = db.Column(db.String(500)) # Individual unit scan if applicable, else usage of master
    x_coord = db.Column(db.Float, default=0.0)
    y_coord = db.Column(db.Float, default=0.0)
    z_coord = db.Column(db.Float, default=0.0)
    element = db.Column(db.String(100)) # Wall, Floor, Ceiling
    
    # Module 3 Data (Reporting & Status)
    description = db.Column(db.Text)
    location = db.Column(db.String(100)) # Unit No / Room Name
    defect_type = db.Column(db.String(50), default='Unknown')
    severity = db.Column(db.String(20), default='Medium')
    status = db.Column(db.String(50), default='Pending') # Pending, Verified, Rectified
    estimated_cost = db.Column(db.Float)
    scheduled_date = db.Column(db.Date)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Activity Log Relationship
    activities = db.relationship('ActivityLog', backref='defect', lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            'id': self.id,
            'x': self.x_coord,
            'y': self.y_coord,
            'z': self.z_coord,
            'description': self.description,
            'status': self.status,
            'defect_type': self.defect_type,
            'severity': self.severity,
            'image_path': self.image_path
        }

class ActivityLog(db.Model):
    __tablename__ = 'activity_logs'
    id = db.Column(db.Integer, primary_key=True)
    defect_id = db.Column(db.Integer, db.ForeignKey('defects.id'))
    action = db.Column(db.String(255), nullable=False) 
    old_value = db.Column(db.String(255)) 
    new_value = db.Column(db.String(255)) 
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class ChatHistory(db.Model):
    __tablename__ = 'chat_history'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    user_message = db.Column(db.Text)
    bot_response = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='chats', lazy=True)
    
# Keep Scan for backward compatibility if needed, or remove. 
# Plan says remove, but 'Defect' model above replaces 'Scan' dependency with 'Project'.
