from flask import Blueprint

residentsbookings_bp = Blueprint('residentsbookings_bp', __name__)

from . import routes
