import time
from app import create_app
from app.module3.extensions import db
from app.models import User, Project, Defect, ChatHistory

app = create_app()

def setup_database():
    with app.app_context():
        print("Waiting for database connection...")
        # Simple retry logic could be added here if needed, but Docker depends_on helps
        
        print("Dropping old tables (if any)...")
        db.drop_all()
        
        print("Creating new tables from app.models...")
        db.create_all()
        print("Tables created.")
        
        # --- SEED DATA ---
        print("Seeding data...")
        
        # 1. Projects
        p1 = Project(name="ASMARINDA12", developer_name="EcoWorld", master_model_path="uploads/master_asmarinda.glb")
        p2 = Project(name="SISIRAN 2", developer_name="IOI Properties")
        p3 = Project(name="TAMAN MERPAUH", developer_name="Merpauh Dev")
        
        db.session.add_all([p1, p2, p3])
        db.session.commit()
        
        # 2. Users
        # Admin/Developer
        dev = User(
            username="dev_contractor", 
            email="dev@ecoworld.com", 
            role="developer",
            company_name="EcoWorld Sdn Bhd",
            company_reg_no="123456-X"
        )
        dev.set_password("dev123")
        
        # Lawyer
        law = User(
            username="zulaikha_law", 
            email="lawyer@firm.com", 
            role="lawyer",
            firm_name="Zulaikha & Partners",
            bar_council_id="BC/Z/999"
        )
        law.set_password("law123")
        
        # Homeowner (Abbas)
        abbas = User(
            username="abbas",
            email="abbas@student.uum.edu.my",
            role="user",
            full_name="Abbas Abu Dzarr",
            project_id=p1.id, # Link to Asmarinda
            ic_number="900101-14-1234"
        )
        abbas.set_password("password123")
        
        db.session.add_all([dev, law, abbas])
        db.session.commit()
        
        print("✓ Database setup complete with Seed Data.")

if __name__ == "__main__":
    setup_database()