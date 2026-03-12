import re

nabilah_path = '/home/abbas/development/pcd/rujukan nabilah/routes.py'
module_3_path = '/home/abbas/development/pcd/module_3_reporting/micro_app/module3/routes.py'

with open(nabilah_path, 'r') as f:
    nabilah_code = f.read()

with open(module_3_path, 'r') as f:
    module_3_code = f.read()

# 1. Extract Nabilah's precise painting logic
n_start_marker = "    # ============================================\n    # PAGE 1: BORANG 1 HEADER & PARTIES"
n_end_marker = "    return send_file("

n_start_idx = nabilah_code.find(n_start_marker)
n_end_idx = nabilah_code.find(n_end_marker) + len(n_end_marker)
n_end_full_idx = nabilah_code.find(")\n", n_end_idx) + 2

nabilah_pdf_logic = nabilah_code[n_start_idx:n_end_full_idx]

# Insert digital validation hash into footers
nabilah_pdf_logic = nabilah_pdf_logic.replace("draw_footer(pdf, width, labels)", "draw_footer(pdf, width, labels, digital_hash)")

# Fix Image Rendering Logic in Nabilah's block to use real DB paths from module 3
nabilah_image_block = """        # ---- Bukti Kecacatan ----
        image_path = os.path.join(evidence_dir, f"defect_{defect['id']}.jpg")
        if os.path.exists(image_path):"""
module_3_image_block = """        # ---- Bukti Kecacatan ----
        image_path = None
        if defect.get('image_path'):
            image_path_candidate = os.path.join("/usr/src/app_main/app/static/", defect['image_path'].lstrip('/'))
            if os.path.exists(image_path_candidate):
                 image_path = image_path_candidate

        if not image_path:
             alt_image = os.path.join(evidence_dir, f"defect_{defect['id']}.jpg")
             if os.path.exists(alt_image):
                 image_path = alt_image
                 
        if image_path:"""
nabilah_pdf_logic = nabilah_pdf_logic.replace(nabilah_image_block, module_3_image_block)

# 2. Add Developer / Legal specific layouts from module 3 to Nabilah's logic
# Nabilah only handled Homeowner styling on Page 1 (Borang 1). 
# Our real data has Developer and Legal. If role != Homeowner, we skip Borang 1 and show a generic header. Let's look at what we had in module 3.
dev_legal_headers = """    # ============================================
    # PAGE 1: HEADER & PARTIES
    # ============================================
    if role == "Homeowner":
"""
nabilah_borang1 = nabilah_pdf_logic[:nabilah_pdf_logic.find("    # ============================================\n    # PAGE 2: RINGKASAN & SENARAI KECACATAN")]
nabilah_borang1 = nabilah_borang1.replace("    # ============================================\n    # PAGE 1: BORANG 1 HEADER & PARTIES\n    # ============================================\n    ", dev_legal_headers)

# Indent Borang 1 block by 4 spaces
nabilah_borang1_indented = ""
for line in nabilah_borang1.split('\\n'):
    if line.startswith(dev_legal_headers.split('\\n')[0]):
        nabilah_borang1_indented += line + '\\n'
        continue
    if "if role == \"Homeowner\":" in line:
        pass # already added
        nabilah_borang1_indented += line + '\\n'
        continue
        
# A safer way to indent the Borang 1 code
lines = nabilah_pdf_logic.split('\\n')
new_pdf_logic = []
in_page_1 = False
for line in lines:
    if line == "    # ============================================":
        if not in_page_1:
           in_page_1 = True
    if line == "    # ============================================" and in_page_1 and "PAGE 2" in new_pdf_logic[-1] if len(new_pdf_logic) else False:
        pass
        
