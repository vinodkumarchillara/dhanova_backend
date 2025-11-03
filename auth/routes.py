from flask import Blueprint, request, jsonify, session
from utils.db import db
from flask_bcrypt import Bcrypt
from bson import ObjectId
from datetime import datetime

auth = Blueprint('auth', __name__)
bcrypt = Bcrypt()

# Use the 'resident' collection inside 'gated_community' database
residents_collection = db["Residents"]

# ---------------- REGISTER ----------------
@auth.route("/register", methods=["POST"])
def register():
    data = request.get_json()

    # ✅ Extract main resident info
    full_name = data.get("fullName")
    gender = data.get("gender")
    dob = data.get("dob")
    phone = data.get("phone")
    alternate_number = data.get("alternateNumber")
    email = data.get("email")
    aadhar = data.get("aadhar")
    address = data.get("address")
    occupation = data.get("occupation")
    ownership_type = data.get("ownershipType")
    tenant_start = data.get("tenantStartDate")
    tenant_end = data.get("tenantEndDate")
    block = data.get("block")
    flat_number = data.get("flatNumber")
    floor = data.get("floor")
    parking_slots = data.get("parkingSlots")
    vehicles = data.get("vehicles")
    ownership_status = data.get("ownershipStatus")

    # ✅ Family and emergency details
    family_members = data.get("familyMembers", [])
    emergency_name = data.get("emergencyName")
    emergency_number = data.get("emergencyNumber")
    emergency_relation = data.get("emergencyRelation")

    role = data.get("role", "resident")

    # 🔹 Basic validation
    if not full_name or not phone or not email:
        return jsonify({"message": "Full name, phone, and email are required"}), 400

    # 🔹 Prevent duplicate users
    existing_user = residents_collection.find_one({
        "$or": [
            {"phone": phone},
            {"email": email}
        ]
    })
    if existing_user:
        return jsonify({"message": "User with same phone or email already exists"}), 400

    # 🔹 Insert data into MongoDB
    resident_data = {
        "fullName": full_name,
        "gender": gender,
        "dob": dob,
        "phone": phone,
        "alternateNumber": alternate_number,
        "email": email,
        "aadhar": aadhar,
        "address": address,
        "occupation": occupation,
        "ownershipType": ownership_type,
        "tenantStartDate": tenant_start,
        "tenantEndDate": tenant_end,
        "block": block,
        "flatNumber": flat_number,
        "floor": floor,
        "parkingSlots": parking_slots,
        "vehicles": vehicles,
        "ownershipStatus": ownership_status,
        "familyMembers": family_members,
        "emergencyContact": {
            "name": emergency_name,
            "number": emergency_number,
            "relation": emergency_relation
        },
        "role": role,
        "createdAt": datetime.utcnow()
    }

    result = residents_collection.insert_one(resident_data)

    return jsonify({
        "message": f"Resident '{full_name}' registered successfully!",
        "residentId": str(result.inserted_id),
        "role": role
    }), 201



# ---------------- LOGIN ----------------

@auth.route("/login", methods=["POST"])
def login():
    print("✅ Login API hit!")
    data = request.get_json()
    identifier = data.get("identifier")  # can be email or phone
    password = data.get("password")

    if not identifier or not password:
        return jsonify({"message": "Email/Phone and password are required"}), 400

    # Find user by email or phone
    user = residents_collection.find_one({
        "$or": [
            {"email": identifier},
            {"phone": identifier}
        ]
    })

    if not user or not bcrypt.check_password_hash(user["password"], password):
        return jsonify({"message": "Invalid email/phone or password"}), 401

    session["user"] = {
        "email": user.get("email"),
        "phone": user.get("phone"),
        "role": user.get("role")
    }

    return jsonify({
        "fullname": user.get("fullname"),
        "role": user.get("role")
    }), 200


    return jsonify({
        "fullname": user.get("fullname"),
        "role": user.get("role")
    }), 200

#LOGOUT ROUTE

@auth.route("/logout", methods=["POST"])
def logout():
    """Clears user session."""
    session.pop("user", None)
    return jsonify({"message": "Logged out successfully"}), 200

# CHECK SESSION ROUTE

@auth.route("/check-session", methods=["GET"])
def check_session():
    """Check if a user session exists."""
    user = session.get("user")
    if not user:
        return jsonify({"message": "No active session"}), 401
    return jsonify({
        "username": user.get("email") or user.get("phone"),
        "role": user["role"],
        "message": "Session active"
    }), 200

# ADMIN: VIEW ALL USERS
@auth.route("/users", methods=["GET"])
def get_all_users():
    """Admins can view all registered users."""
    user = session.get("user")
    if not user or user["role"] != "admin":
        return jsonify({"message": "Access denied! Admins only."}), 403

    users = list(users_collection.find({}, {"_id": 0, "password": 0}))
    return jsonify({"users": users}), 200
