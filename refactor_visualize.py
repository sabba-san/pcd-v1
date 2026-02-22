import os
import re

html_path = 'app/templates/module3/visualize.html'
js_dir = 'app/static/module3/js'
js_path = os.path.join(js_dir, 'visualize.js')

os.makedirs(js_dir, exist_ok=True)

with open(html_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# find <script> section (the last one starting around line 1274)
start_idx = -1
end_idx = -1
for i, line in enumerate(lines):
    if line.strip() == '<script>':
        start_idx = i
    elif line.strip() == '</script>':
        end_idx = i

if start_idx != -1 and end_idx != -1 and end_idx > start_idx + 10:
    js_lines = lines[start_idx+1:end_idx]
    
    js_content = "".join(js_lines)
    
    # Repace Jinja in JS content
    # 1. replace {% if model_url %} with if (window.APP_CONFIG.modelUrl) {
    js_content = js_content.replace("{% if model_url %}", "if (window.APP_CONFIG.modelUrl) {")
    js_content = js_content.replace("{% if not model_url %}", "if (!window.APP_CONFIG.modelUrl) {")
    js_content = js_content.replace("{% else %}", "} else {")
    js_content = js_content.replace("{% endif %}", "}")
    
    # 2. replace {{ model_url }}
    js_content = js_content.replace("'{{ model_url }}'", "window.APP_CONFIG.modelUrl")
    js_content = js_content.replace("{{ model_url }}", "window.APP_CONFIG.modelUrl")
    
    # 3. replace {{ scan_id }}
    js_content = js_content.replace("{{ scan_id }}", "' + window.APP_CONFIG.scanId + '")
    # Need to be careful with template strings or string concatenation
    # Let's use ES6 template literals or simply string concatenation.
    # Original: fetch('/module3/api/scans/{{ scan_id }}/defects')
    # Becomes: fetch('/module3/api/scans/' + window.APP_CONFIG.scanId + '/defects')
    
    with open(js_path, 'w', encoding='utf-8') as f:
        f.write(js_content)
        
    # Now replace the script block in HTML
    new_script_html = """        <script>
            window.APP_CONFIG = {
                modelUrl: "{{ model_url | default('') }}",
                scanId: "{{ scan_id | default('') }}"
            };
        </script>
        <script src="{{ url_for('static', filename='module3/js/visualize.js') }}"></script>
"""
    new_html = "".join(lines[:start_idx]) + new_script_html + "".join(lines[end_idx+1:])
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(new_html)
    print("Refactoring complete.")
else:
    print("Could not find the script boundaries properly.")
