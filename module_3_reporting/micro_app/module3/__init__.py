from flask import Blueprint

# Initialize the Blueprint
import os
module3_bp = Blueprint('module3', __name__, template_folder=os.path.join(os.path.dirname(__file__), 'templates'))

# IMPORT ROUTES AT THE BOTTOM
# This is crucial so that module3_bp is created before routes.py tries to use it
from . import routes