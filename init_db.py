from app import create_app
from app.module2.extensions import db
from app.module2.models import User, Scan, Defect, ActivityLog

app = create_app()

with app.app_context():
    print("--- DATEBASE INIT TOOL ---")
    print(f"Database URI: {app.config['SQLALCHEMY_DATABASE_URI']}")
    
    # Drop all
    print("... Dropping all tables")
    db.drop_all()
    
    # Create all
    print("... Creating all tables")
    db.create_all()
    
    # Seed Data
    print("... Seeding default users")
    
    # 1. Abbas (Homeowner)
    u1 = User(
        email='abbas@student.uum.edu.my', 
        full_name='Abbas Abu Dzarr', 
        role='user', 
        project_name='ASMARINDA12',
        ic_number='990101-01-1234',
        phone_number='012-3456789'
    )
    u1.set_password('password123')
    
    # 2. Developer
    u2 = User(
        email='developer@ecoworld.com', 
        full_name='EcoWorld Contractor', 
        role='developer', 
        project_name='ALL'
    )
    u2.set_password('dev123')
    
    # 3. Admin/Lawyer
    u3 = User(
        email='admin@uum.edu.my', 
        full_name='System Admin', 
        role='admin', 
        project_name='ALL'
    )
    u3.set_password('admin123')
    
    db.session.add_all([u1, u2, u3])
    db.session.commit()
    
    # Seed Sample Scan/Project
    print("... Seeding sample project")
    s1 = Scan(
        name='Default Scan',
        model_path='sisiranRendered.glb',
        user_id=u1.id,
        grant_number='GRN 12345',
        parcel_number='A-85',
        vp_date=None, 
        ccc_date=None,
        bank_name='Maybank',
        inspection_type='self'
    )
    db.session.add(s1)
    db.session.commit()
    
    # Seed Sample Defect
    d1 = Defect(
        user_id=u1.id,
        scan_id=s1.id,
        x=0, y=0, z=0,
        description='Crack on wall',
        location='Master Bedroom',
        status='reported',
        severity='Medium'
    )
    db.session.add(d1)
    db.session.commit()
    
    print("SUCCESS: Database initialized!")
