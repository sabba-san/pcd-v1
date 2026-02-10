from app.module2.extensions import db
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin, db.Model):
    """User accounts for all roles"""
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(100))
    role = db.Column(db.String(50), default='user')
    project_name = db.Column(db.String(100))
    # DLP-Advisor Fields
    ic_number = db.Column(db.String(20))
    phone_number = db.Column(db.String(20))
    employment_details = db.Column(db.String(100))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Scan(db.Model):
    """Represents a Project / Defect Claim File"""
    __tablename__ = 'scans'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False) # Project Name
    model_path = db.Column(db.String(500)) 
    created_at = db.Column(db.DateTime, default=db.func.now())
    
    # DLP-Advisor Fields
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True) # Link to Owner
    grant_number = db.Column(db.String(50))
    parcel_number = db.Column(db.String(50))
    vp_date = db.Column(db.Date)
    ccc_date = db.Column(db.Date)
    bank_name = db.Column(db.String(100))
    inspection_type = db.Column(db.String(20)) # 'self' or 'professional'
    assessor_details = db.Column(db.Text) # JSON or text details if professional

    defects = db.relationship('Defect', backref='scan', lazy=True)

class Defect(db.Model):
    __tablename__ = 'defects'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True) # Linked to User
    scan_id = db.Column(db.Integer, db.ForeignKey('scans.id'), nullable=False)
    x = db.Column(db.Float, nullable=False)
    y = db.Column(db.Float, nullable=False)
    z = db.Column(db.Float, nullable=False)
    element = db.Column(db.String(255)) 
    location = db.Column(db.String(100)) 
    defect_type = db.Column(db.String(50), default='Unknown') 
    severity = db.Column(db.String(20), default='Medium') 
    priority = db.Column(db.String(20), default='Medium') 
    description = db.Column(db.Text) 
    status = db.Column(db.String(50), default='Reported') 
    image_path = db.Column(db.String(500)) 
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=db.func.now())
    activities = db.relationship('ActivityLog', backref='defect', lazy=True)

class ActivityLog(db.Model):
    __tablename__ = 'activity_logs'
    id = db.Column(db.Integer, primary_key=True)
    defect_id = db.Column(db.Integer, db.ForeignKey('defects.id'))
    scan_id = db.Column(db.Integer, db.ForeignKey('scans.id'))
    action = db.Column(db.String(255), nullable=False) 
    old_value = db.Column(db.String(255)) 
    new_value = db.Column(db.String(255)) 
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    scan = db.relationship('Scan', backref='activities')
    updated_at = db.Column(db.DateTime, default=db.func.now(), onupdate=db.func.now())