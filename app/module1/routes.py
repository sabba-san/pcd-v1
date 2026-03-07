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
bp = Blueprint('module1', __name__, url_prefix='/module1')

# Initialize Groq Client
client = Groq(
    api_key=os.environ.get("GROQ_API_KEY"), #nnti letak api key here
)

# --- ROUTES ---

@bp.route('/')
def index():
    return render_template('module1/index.html')

@bp.route('/chat', methods=['POST'])
def chat():
    # ACCEPT JSON for API
    data = request.get_json(force=True, silent=True)
    if not data:
        return jsonify({'error': 'No JSON data provided'}), 400
        
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
            # Use a variable or config for model name if possible, hardcoded for now as in original
            model="llama-3.1-8b-instant",
        )
        
        bot_reply = chat_completion.choices[0].message.content
        
        # Save to ChatHistory
        try:
            from app.module3.extensions import db
            from app.models import ChatHistory
            from flask_login import current_user
            if current_user.is_authenticated:
                new_chat = ChatHistory(user_id=current_user.id, user_message=user_message, bot_response=bot_reply)
                db.session.add(new_chat)
                db.session.commit()
        except Exception as db_err:
            print(f"Error saving chat history: {db_err}")
            
        return jsonify({'reply': bot_reply})

    except Exception as e:
        # --- DEBUG MODE: Send the real error to the frontend ---
        print(f"AI Error: {e}")
        return jsonify({'error': f"DEBUG INFO: {str(e)}"}), 500

@bp.route('/history', methods=['GET'])
def get_history():
    from flask_login import current_user
    from app.models import ChatHistory
    if not current_user.is_authenticated:
        return jsonify({"error": "Unauthorized"}), 401
    
    chats = ChatHistory.query.filter_by(user_id=current_user.id).order_by(ChatHistory.timestamp.asc()).all()
    history = []
    for chat in chats:
        history.append({
            "user": chat.user_message,
            "bot": chat.bot_response,
            "timestamp": chat.timestamp.isoformat() if chat.timestamp else None
        })
    return jsonify(history)

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
