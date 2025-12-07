from appholder import application as app
from auth.routes import auth
from ADMIN_ROUTES.Residents_routes import admin
from ADMIN_ROUTES.AdminEvents_routes import adminevents
from ADMIN_ROUTES.ResidentBookings_routes import residentsbookings
from ADMIN_ROUTES.Amenities import amenities
from flask_cors import CORS





CORS(app, supports_credentials=True, origins=["http://localhost:3000"])



app.register_blueprint(auth, url_prefix="/api/auth")
app.register_blueprint(admin,url_prefix="/api/admin")
app.register_blueprint(adminevents,url_prefix="/api/adminevents")
app.register_blueprint(residentsbookings, url_prefix="/api/residentbookings")
app.register_blueprint(amenities,url_prefix="/api/amenities")


if __name__ == "__main__":
    app.run(debug=True, port=5000)
