from appholder import application as app
from auth.routes import auth, adminevents
from signup import signup_bp
from signup.db import init_db
from flask_cors import CORS
from forgot_password.routes import forgot_bp
from residentsbookings import residentsbookings_bp



CORS(app, supports_credentials=True, origins=["http://localhost:3000"])

init_db(app)

app.register_blueprint(auth, url_prefix="/api/auth")
app.register_blueprint(adminevents, url_prefix="/api/adminevents")
app.register_blueprint(signup_bp, url_prefix="/api/signup")
app.register_blueprint(forgot_bp, url_prefix="/api/forgot-password")
app.register_blueprint(residentsbookings_bp, url_prefix="/api/residentbookings")


if __name__ == "__main__":
    app.run(debug=True, port=5000)
