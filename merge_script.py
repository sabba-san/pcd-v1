import re

nabilah_path = '/home/abbas/development/pcd/rujukan nabilah/routes.py'
module_3_path = '/home/abbas/development/pcd/module_3_reporting/micro_app/module3/routes.py'

with open(nabilah_path, 'r') as f:
    n_code = f.read()

with open(module_3_path, 'r') as f:
    m3_code = f.read()

# === Extract Nabilah's Layout ===
n_start_marker = "    # ============================================\n    # PAGE 1: BORANG 1 HEADER & PARTIES"
n_end_marker = "    # Filename based on role\n"

n_start_idx = n_code.find(n_start_marker)
n_end_idx = n_code.find(n_end_marker)

n_pdf_logic = n_code[n_start_idx:n_end_idx]

# Inject digital validation hash variable into draw_footer calls
n_pdf_logic = n_pdf_logic.replace("draw_footer(pdf, width, labels)", "draw_footer(pdf, width, labels, digital_hash)")

# Replace the Bukti Kecacatan image loading logic to load real DB images
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
n_pdf_logic = n_pdf_logic.replace(nabilah_image_block, module_3_image_block)


# Now we also need to respect Module 3's "if role == 'Homeowner':" for Page 1, because Nabilah didn't have specific Developer logic
m3_page1_start = m3_code.find("    # PAGE 1\n    if role == \"Homeowner\":\n")
m3_page1_end = m3_code.find("    pdf.setFont(\"Helvetica-Bold\", 10)\n    if language == \"en\":\n        pdf.drawString(50, y, \"Claim Summary:\")")

m3_page1_logic = m3_code[m3_page1_start:m3_page1_end]

# In n_pdf_logic, where does Page 2 start?
n_page2_start = n_pdf_logic.find("    # ============================================\n    # PAGE 2: RINGKASAN & SENARAI KECACATAN\n    # ============================================\n")

n_page2_logic = n_pdf_logic[n_page2_start:]

# We need to indent n_page2_logic's draw_footer calls inside loops, but they are already fine.
# Wait, let's just use m3_page1_logic + n_page2_logic!
# Because m3_page1_logic already exactly copied Nabilah's homeowner page 1 inside `if role == 'Homeowner'`, and has the `else` for Developer!
# Let's verify if m3_page1_logic is identical to Nabilah's logic for Homeowner.
# Actually, the user says: "Ensure the AI Conclusion, AI Disclaimer, Digital Validation Hash, and Signature sections are perfectly restored at the end of the document."
# Those sections are in Page 2 onwards! 
# Page 2 in module_3: it has `# Defect List`, `# AI REPORT SECTION`.
# Let's just swap m3's Page 2 onwards with Nabilah's Page 2 onwards + Hash injected.

combined_logic = m3_page1_logic + n_page2_logic

# Find where to replace in module 3
m3_replace_start = m3_page1_start
m3_replace_end = m3_code.find("    if role == \"Legal\": filename = labels[\"legal_filename\"]")

m3_code_new = m3_code[:m3_replace_start] + combined_logic + "    " + m3_code[m3_replace_end:]

with open(module_3_path, 'w') as f:
    f.write(m3_code_new)

print("Replace done!")
