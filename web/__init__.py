"""Web UI package for AIBI - Flask blueprints and session management"""

from flask import Blueprint

# Create blueprints for registration in main.py
web_bp = Blueprint('web', __name__, template_folder='../templates', static_folder='../static')
api_bp = Blueprint('api', __name__, url_prefix='/api')

__all__ = ['web_bp', 'api_bp']
