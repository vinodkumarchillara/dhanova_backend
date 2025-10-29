from flask import Flask
from flask_session import Session
from flask_cors import CORS

application = Flask(__name__)
application.secret_key = "supersecretkey"

application.config["SESSION_PERMANENT"] = False
application.config["SESSION_TYPE"] = "filesystem"

Session(application)
CORS(application, supports_credentials=True)
