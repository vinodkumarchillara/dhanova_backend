from flask import request, jsonify
from flask_bcrypt import Bcrypt
from . import signup_bp
from .db import mongo

bcrypt = Bcrypt()

@signup_bp.route("/create", methods=["POST"])
def signup_user():
    data = request.get_json()

    firstname = data.get("Firstname")
    lastname = data.get("Lastname")
    email = data.get("Email")
    password = data.get("Password")
    phone = data.get("phone")
    Address=data.get("Address")
    Bloodgroup=data.get("Bloodgroup")
    Aadhaar=data.get("Aadhaar")
    PAN=data.get("PAN")

    # Validate required fields
    if not firstname or not lastname or not email or not password or not phone:
        return jsonify({"message": "All fields are required"}), 400

    if len(password) < 6:
        return jsonify({"message": "Password must be at least 6 characters"}), 400

    users = mongo.db.users

    # Check if email exists
    if users.find_one({"email": email.lower()}):
        return jsonify({"message": "Email already registered"}), 400

    hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")

    user = {
        "firstname": firstname,
        "lastname": lastname,
        "fullname": f"{firstname} {lastname}",
        "email": email.lower(),
        "password": hashed_password,
        "phone": phone,
        "Address":Address,
        "Bloodgroup":Bloodgroup,
        "Aadhaar":Aadhaar,
        "PAN":PAN,

        "role": "admin"     # Recommended default
    }

    users.insert_one(user)

    return jsonify({"message": "Signup successful!"}), 201
