import sys
import os

files = [
    "app/module2/developer/routes.py",
    "app/module3/developer/routes.py",
    "app/module3/utils.py"
]

for filepath in files:
    if not os.path.exists(filepath):
        continue
    with open(filepath, "r") as f:
        content = f.read()

    # Replace imports
    content = content.replace("from app.models import Scan, Defect", "from app.models import Project, Defect")
    content = content.replace("from app.module2.models import Scan, User, Defect", "from app.models import Project, User, Defect")
    
    # Replace Scan class usages
    content = content.replace("Scan.", "Project.")
    content = content.replace("Scan,", "Project,")
    content = content.replace("Scan(", "Project(")
    content = content.replace("Scan ", "Project ")
    
    # Replace scan object / variable usages
    content = content.replace("scan_id", "project_id")
    content = content.replace("scan.", "project.")
    content = content.replace("scan=", "project=")
    content = content.replace("scan,", "project,")
    content = content.replace("scan ", "project ")
    content = content.replace("scans=", "projects=")
    content = content.replace("scans.", "projects.")
    content = content.replace("scans ", "projects ")
    content = content.replace("in scans:", "in projects:")
    content = content.replace("scans)", "projects)")
    content = content.replace("scan_data", "project_data")
    content = content.replace("for scan,", "for project,")
    content = content.replace("scans =", "projects =")
    content = content.replace("filtered_scans", "filtered_projects")
    content = content.replace("export_scan_csv", "export_project_csv")
    content = content.replace("view_scan", "view_project")
    content = content.replace("/scan/", "/project/")

    with open(filepath, "w") as f:
        f.write(content)

print("Done replacing.")
