from app.module3.extensions import db
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class Project(db.Model):
    __tablename__ = 'projects'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    
    developer_name = db.Column(db.Text)
    developer_ssm = db.Column(db.Text)
    developer_address = db.Column(db.Text)
    
    master_model_path = db.Column(db.String(500))
    
    # Timestamps
    from datetime import datetime
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    users = db.relationship('User', backref='project', lazy=True)
    claims = db.relationship('TribunalClaim', backref='project', lazy=True, cascade="all, delete-orphan")
    defects = db.relationship('Defect', backref='project', lazy=True, cascade="all, delete-orphan")

class User(UserMixin, db.Model):
    """Unified User Model"""
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50))
    
    # Legal/Homeowner
    full_name = db.Column(db.Text)
    ic_number = db.Column(db.Text)
    phone_number = db.Column(db.Text)
    correspondence_address = db.Column(db.Text)
    unit_no = db.Column(db.String(50))
    
    # Tribunal Info
    tribunal_city = db.Column(db.String(100))
    tribunal_state = db.Column(db.String(100))
    
    # Other Roles
    company_name = db.Column(db.String(100))
    company_reg_no = db.Column(db.String(50))
    firm_name = db.Column(db.String(100))
    
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=True)

    # Relationships
    claims = db.relationship('TribunalClaim', backref='user', lazy=True)
    defects = db.relationship('Defect', backref='user', lazy=True)
    reports = db.relationship('GeneratedReport', backref='user', lazy=True)
    chats = db.relationship('ChatHistory', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def project_name(self):
        return self.project.name if self.project else None

class TribunalClaim(db.Model):
    __tablename__ = 'tribunal_claims'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=True)
    
    claim_number = db.Column(db.String(100), unique=True)
    total_claim_amount = db.Column(db.Float, default=0.0)
    filing_date = db.Column(db.Date)
    status = db.Column(db.String(50), default='Draft')
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    defects = db.relationship('Defect', backref='claim', lazy=True)
    reports = db.relationship('GeneratedReport', backref='claim', lazy=True)

class Defect(db.Model):
    __tablename__ = 'defects'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=True)
    claim_id = db.Column(db.Integer, db.ForeignKey('tribunal_claims.id'), nullable=True)
    
    # 3D Data
    image_path = db.Column(db.String(500))
    scan_path = db.Column(db.String(500))
    x_coord = db.Column(db.Float)
    y_coord = db.Column(db.Float)
    z_coord = db.Column(db.Float)
    element = db.Column(db.String(100))
    location = db.Column(db.String(255))
    
    # Reporting Data
    title = db.Column(db.Text)
    description = db.Column(db.Text)
    status = db.Column(db.String(50), default='Pending')
    defect_type = db.Column(db.String(100))
    severity = db.Column(db.String(50))
    estimated_cost = db.Column(db.Float)
    scheduled_date = db.Column(db.Date)
    
    reported_date = db.Column(db.Date)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'x_coord': self.x_coord,
            'y_coord': self.y_coord,
            'z_coord': self.z_coord,
            'title': self.title,
            'description': self.description,
            'status': self.status,
            'defect_type': self.defect_type,
            'severity': self.severity,
            'image_path': self.image_path,
            'element': self.element,
            'location': self.location
        }

class GeneratedReport(db.Model):
    __tablename__ = 'generated_reports'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    claim_id = db.Column(db.Integer, db.ForeignKey('tribunal_claims.id'), nullable=True)
    
    report_type = db.Column(db.String(100))
    file_path = db.Column(db.String(500))
    generated_at = db.Column(db.DateTime, default=datetime.utcnow)

class ChatHistory(db.Model):
    __tablename__ = 'chat_history'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    user_message = db.Column(db.Text)
    bot_response = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
