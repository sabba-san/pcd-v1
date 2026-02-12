# module3/routes.py
from flask import Blueprint, jsonify, redirect
from ..conversation_logger import view_history, clear_history

module3 = Blueprint('module3', __name__)

@module3.route('/dashboard')
def dashboard():
    # Redirect to the main app dashboard
    return redirect("http://localhost:5000/module3/dashboard")

@module3.route('/history', methods=['GET'])
def history():
    return jsonify(view_history())

@module3.route('/clear_history', methods=['POST'])
def clear():
    clear_history()
    return jsonify({"status": "History cleared"})