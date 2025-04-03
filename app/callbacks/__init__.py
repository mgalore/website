from flask import Blueprint

bp = Blueprint('callbacks', __name__)

# Import routes after blueprint creation to avoid circular imports
from . import routes 