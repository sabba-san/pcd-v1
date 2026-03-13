from app import db
from app.models import User, Project
import sys
import os

try:
    from app import create_app
    app = create_app()
    with app.app_context():
        devs = User.query.filter_by(role='developer').all()
        print("Developers:")
        for d in devs:
            print(f"ID: {d.id}, Name: {d.company_name}, RegNo: {d.company_reg_no}, NRIC: {d.nric}, Addr: {d.company_address}, Phone: {d.contact_number}, Email: {d.fax_email}, BaseEmail: {d.email}")
        
        projs = Project.query.all()
        print("\nProjects:")
        for p in projs:
            print(f"ID: {p.id}, name: {p.name}, dev_name: {p.developer_name}, dev_ssm: {p.developer_ssm}, dev_addr: {p.developer_address}")
except Exception as e:
    print(e)
