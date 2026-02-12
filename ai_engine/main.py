from flask import Flask, request, jsonify
import sys
import os

# Add the 'fyo_version1' directory to the path so we can import from it
sys.path.append(os.path.join(os.path.dirname(__file__), 'fyo_version1'))

try:
    from app.chatbot_core import process_query, analyze_legal_text
except ImportError as e:
     print(f"Error importing chatbot_core: {e}")
     process_query = None

app = Flask(__name__)

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"}), 200

@app.route('/api/chat', methods=['POST'])
def chat():
    if not process_query:
         return jsonify({'error': 'Chatbot core not initialized correctly.'}), 500

    data = request.get_json(force=True, silent=True)
    if not data:
        return jsonify({'error': 'No JSON data provided'}), 400
        
    user_message = data.get('message')
    
    if not user_message:
        return jsonify({'error': 'No message provided'}), 400

    try:
        response = process_query(user_message)
        return jsonify({'response': response}) # Changed key from 'reply' to 'response' as requested
    except Exception as e:
        print(f"AI Error: {e}")
        return jsonify({'error': f"AI Service Error: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002)
