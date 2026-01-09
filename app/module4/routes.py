from flask import Blueprint, render_template, request, jsonify
import os
from groq import Groq

# Try to import the feedback manager (handles if file is missing)
try:
    from .feedback_manager import save_feedback
except ImportError:
    # Fallback if file not found
    def save_feedback(text):
        print(f"Feedback received (simulated): {text}")

# Define the Blueprint
bp = Blueprint('module4', __name__, url_prefix='/module4')

# Initialize Groq Client
client = Groq(
    api_key=os.environ.get("GROQ_API_KEY"),
)

# --- ROUTES ---

@bp.route('/')
def index():
    return render_template('module4/index.html')

@bp.route('/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data.get('message')
    
    if not user_message:
        return jsonify({'error': 'No message provided'}), 400

    try:
        # Call Groq API
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system", 
                    "content": "You are Jian Wei, an expert AI assistant for Malaysian Property Law and Defect Liability Period (DLP). Answer clearly and concisely."
                },
                {
                    "role": "user", 
                    "content": user_message,
                }
            ],
           model="llama-3.1-8b-instant",
        )
        
        bot_reply = chat_completion.choices[0].message.content
        return jsonify({'reply': bot_reply})

    except Exception as e:
        # --- DEBUG MODE: Send the real error to the frontend ---
        print(f"AI Error: {e}")
        return jsonify({'error': f"DEBUG INFO: {str(e)}"}), 500

@bp.route('/feedback', methods=['POST'])
def feedback():
    try:
        data = request.json
        feedback_text = data.get('feedback')
        if feedback_text:
            save_feedback(feedback_text)
            return jsonify({"status": "Feedback saved"})
        return jsonify({"status": "No text provided"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500
