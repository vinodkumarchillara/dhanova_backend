from flask import Blueprint, request, jsonify, session
from utils.db import db
from flask_bcrypt import Bcrypt
from bson import ObjectId
from datetime import datetime
from utils.cloudinary_helper import upload_to_cloudinary
from config import CLOUDINARY_CONFIG  
import uuid

auth = Blueprint('auth', __name__)
bcrypt = Bcrypt()
users_collection = db["users"]

#Function to generate resident id
def generate_resident_id(flat_number, phone):
    """
    Generates a unique Resident ID in the format:
    RES<FlatNumber><Last4DigitsOfPhone>
    Example: RESA1033210
    """
    try:
        if flat_number and phone:
            return f"RES{flat_number}{str(phone)[-4:]}"  
        elif flat_number:
            return f"RES{flat_number}0000"
        else:
            return None
    except Exception as e:
        raise ValueError(f"Error generating resident ID: {str(e)}")


# REGISTER ROUTE
@auth.route("/register", methods=["POST"])
def register():
    """Registers a new resident with Cloudinary photo/id proof uploads."""

    # Extract form data (multipart/form-data)
    full_name = request.form.get("fullName")
    gender = request.form.get("gender")
    dob = request.form.get("dob")
    phone = request.form.get("phone")
    alternate_number = request.form.get("alternateNumber")
    email = request.form.get("email")
    aadhar = request.form.get("aadhar")
    address = request.form.get("address")
    occupation = request.form.get("occupation")
    ownership_type = request.form.get("ownershipType")
    tenant_start = request.form.get("tenantStartDate")
    tenant_end = request.form.get("tenantEndDate")
    block = request.form.get("block")
    flat_number = request.form.get("flatNumber")
    floor = request.form.get("floor")
    parking_slots = request.form.get("parkingSlots")
    vehicles = request.form.get("vehicles")
    ownership_status = request.form.get("ownershipStatus")
    role = request.form.get("role", "resident")

    emergency_name = request.form.get("emergencyName")
    emergency_number = request.form.get("emergencyNumber")
    emergency_relation = request.form.get("emergencyRelation")

    # Uploaded files
    photo = request.files.get("photo")
    id_proof = request.files.get("idProof")
    
    #  Basic validation
    if not full_name or not phone or not email:
        return jsonify({"message": "Full name, phone, and email are required"}), 400

    # Duplicate check
    existing_user = users_collection.find_one({
        "$or": [
            {"phone": phone},
            {"email": email},
            {"aadhar": aadhar},
            {
                "$and": [
                    {"flatNumber": flat_number},
                    {"ownershipType": "Owner"}
                ]
            }
        ]
    })

    if existing_user:
        conflict_field = None
        if existing_user.get("phone") == phone:
            conflict_field = "phone number"
        elif existing_user.get("email") == email:
            conflict_field = "email address"
        elif existing_user.get("aadhar") == aadhar:
            conflict_field = "Aadhar number"
        elif (
            existing_user.get("flatNumber") == flat_number
            and existing_user.get("ownershipType") == "Owner"
        ):
            conflict_field = "flat (already owned by another resident)"
        return jsonify({
            "message": f"Resident with the same {conflict_field} already exists."
        }), 400

    # Generate Resident ID
    try:
        resident_id = generate_resident_id(flat_number, phone)
    except ValueError as e:
        return jsonify({"message": str(e)}), 500

    #  Upload files using helper
    photo_url = upload_to_cloudinary(photo, "residents/photos")
    id_proof_url = upload_to_cloudinary(id_proof, "residents/id_proofs")

    # Optional: Handle upload failures
    if photo and not photo_url:
        return jsonify({"message": "Photo upload failed!"}), 500
    if id_proof and not id_proof_url:
        return jsonify({"message": "ID proof upload failed!"}), 500

    # Save resident data to MongoDB
    resident_data = {
        "residentId": resident_id,
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
        "photo": photo_url,
        "idProof": id_proof_url,
        "emergencyContact": {
            "name": emergency_name,
            "number": emergency_number,
            "relation": emergency_relation
        },
        "role": role,
        "createdAt": datetime.utcnow()
    }

    users_collection.insert_one(resident_data)

    return jsonify({
        "message": f"Resident '{full_name}' registered successfully!",
        "residentId": resident_id,
        "photoURL": photo_url,
        "idProofURL": id_proof_url,
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
    user = users_collection.find_one({
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
