from app import create_app
from app.module3.extensions import db
from app.models import User, Project, Defect, ActivityLog

app = create_app()

with app.app_context():
    # 1. Setup Data
    print("Setting up test data...")
    u = User.query.filter_by(username='test_user_count').first()
    if u:
        db.session.delete(u)
    
    p = Project.query.filter_by(name='Test Project Count').first()
    if p:
        db.session.delete(p)
        
    db.session.commit()
    
    p = Project(name='Test Project Count')
    db.session.add(p)
    db.session.commit()
    
    u = User(username='test_user_count', email='test_count@example.com', role='user')
    u.set_password('password')
    u.project_id = p.id
    db.session.add(u)
    db.session.commit()
    
    # 2. Add Defect
    print("Adding defect...")
    d = Defect(project_id=p.id, user_id=u.id, description="Test Defect", status="New")
    db.session.add(d)
    db.session.commit()
    
    # Verify Count
    defects = Defect.query.filter_by(project_id=p.id).all()
    count_1 = len(defects)
    print(f"Defect Count after Add: {count_1}")
    
    if count_1 != 1:
        print("FAIL: Count should be 1")
    
    # 3. List Projects Logic
    print("Testing List Projects Logic...")
    proj = Project.query.get(p.id)
    defects_query = Defect.query.filter_by(project_id=proj.id).all()
    print(f"List Projects Defect Count: {len(defects_query)}")
    
    # 4. Delete Defect
    print("Deleting defect...")
    # Mimic delete_defect route logic
    ActivityLog.query.filter_by(defect_id=d.id).delete()
    db.session.delete(d)
    db.session.commit()
    
    # Verify Count
    defects_after = Defect.query.filter_by(project_id=p.id).all()
    count_2 = len(defects_after)
    print(f"Defect Count after Delete: {count_2}")
    
    if count_2 != 0:
        print("FAIL: Count should be 0")
    else:
        print("SUCCESS: Count updated correctly")
        
    # Cleanup
    db.session.delete(u)
    db.session.delete(p)
    db.session.commit()
