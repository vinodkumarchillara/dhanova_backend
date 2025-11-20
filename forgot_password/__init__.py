from flask import Blueprint

forgot_bp = Blueprint("forgot_bp", __name__)

from .routes import *

