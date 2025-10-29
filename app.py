# # app.py
from appholder import application as app
from auth.routes import auth

# Register Blueprints
app.register_blueprint(auth, url_prefix="/api/auth")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
