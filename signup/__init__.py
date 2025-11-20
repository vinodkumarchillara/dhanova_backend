from flask import Blueprint

signup_bp = Blueprint("signup_bp", __name__)

from . import route   # <-- DO NOT use import *
