from flask import Blueprint, render_template, request, jsonify

# Define the Blueprint with the static folder registered
# No static_folder needed since we are using the global app/static
bp = Blueprint('module4', __name__, url_prefix='/module4')

# --- ROUTE 1: Render the Chat Interface ---
@bp.route('/chat', methods=['GET'])
def chat_ui():
    # This loads the HTML file you just created
    return render_template('chatbot.html')

# --- ROUTE 2: The AI Processing Logic ---
@bp.route('/response', methods=['POST'])
def chat_response():
    # 1. Get the user's message from the JSON packet
    data = request.get_json()
    user_message = data.get('message', '').lower()

    # 2. Ask the "Knowledge Base" for an answer
    bot_reply = get_dlp_law_advice(user_message)

    # 3. Send the answer back to the HTML
    return jsonify({'reply': bot_reply})

# --- THE KNOWLEDGE BASE (The Brain) ---
# This function analyzes the sentence and finds the matching legal rule.
def get_dlp_law_advice(text):
    
    # TOPIC 1: Duration / Time
    if any(word in text for word in ['how long', 'duration', 'time', 'months', 'period', 'warranty', 'expire']):
        return "Under the Housing Development Act (HDA), the Defect Liability Period (DLP) lasts for <b>24 months</b> starting from the date you receive your keys (Vacant Possession)."

    # TOPIC 2: Cracks (Structural vs Cosmetic)
    elif 'crack' in text:
        return """
        Regarding cracks, the law distinguishes between two types:
        <ul>
            <li><b>Hairline Cracks:</b> Usually cosmetic. The developer must patch and repaint them.</li>
            <li><b>Structural Cracks:</b> These are wider than 0.3mm or go through the wall. This is a serious safety issue requiring a structural engineer's assessment.</li>
        </ul>
        """

    # TOPIC 3: Leaks / Water Issues
    elif any(word in text for word in ['leak', 'water', 'roof', 'ceiling', 'damp', 'stain']):
        return "Water leakages are a serious defect. Under Clause 26 of the Sale & Purchase Agreement, the developer must rectify any roof leaks or inter-floor leakages occurring during the DLP."

    # TOPIC 4: Who Pays? (Cost)
    elif any(word in text for word in ['who pays', 'cost', 'pay', 'responsible', 'bill', 'fee']):
        return "During the 24-month Defect Liability Period, the <b>Developer</b> is fully responsible for the cost of materials and labor to repair defects. You should <b>not</b> pay for these repairs."

    # TOPIC 5: Procedure (How to report)
    elif any(word in text for word in ['how to', 'procedure', 'step', 'process', 'report', 'submit']):
        return "<b>Standard Procedure:</b><br>1. Inspect your unit thoroughly.<br>2. Mark defects with masking tape.<br>3. Submit the official Complaint Form to the developer.<br>4. The developer has <b>30 days</b> to complete repairs."

    # TOPIC 6: Late Repairs
    elif any(word in text for word in ['late', 'slow', 'delay', 'ignore', '30 days']):
        return "If the developer fails to repair within 30 days, you have the right to hire your own contractor and claim the cost from the developer's retention sum (held by lawyers)."

    # Greetings
    elif any(word in text for word in ['hello', 'hi', 'hey', 'greetings']):
        return "Hello! I am ready to answer your questions about Malaysian Property Law."

    # FALLBACK (If AI doesn't understand)
    else:
        return "I am specifically trained on the <b>Housing Development Act (DLP)</b>. <br><br>Could you rephrase your question? Try asking about <b>'cracks'</b>, <b>'leaks'</b>, or <b>'warranty period'</b>."