from flask import Blueprint, request, jsonify, session
from utils.db import db
from flask_bcrypt import Bcrypt
from bson import ObjectId
from datetime import datetime ,timedelta
from bson import errors as bson_errors
from utils.cloudinary_helper import upload_to_cloudinary
from config import CLOUDINARY_CONFIG  
import uuid
import traceback
import json
from flask import session
from .mail_utils import generate_otp, send_email
import threading


auth = Blueprint('auth', __name__)
bcrypt = Bcrypt()
users_collection = db["users"]

adminevents = Blueprint("adminevents", __name__)
events_collection = db["AdminEvents"]
otps_collection = db["otps"]




# Function to generate resident id
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





# ---------------- LOGIN ----------------
@auth.route("/login", methods=["POST"])
def login():
    print("✅ Login API hit!")
    data = request.get_json()
    print("🧠 Received data:", data)
    email_or_phone = data.get("emailOrPhone")
    password = data.get("password")

    if not email_or_phone or not password:
        return jsonify({"message": "Email/Phone and password are required"}), 400

    # 🔍 Find user by email or phone
    user = users_collection.find_one({
        "$or": [
            {"email": email_or_phone},
            {"phone": email_or_phone}
        ]
    })

    if not user or not bcrypt.check_password_hash(user["password"], password):
        return jsonify({"message": "Invalid email/phone or password"}), 401

    # ✅ Store user in session (optional)
    session["user"] = {
        "email": user.get("email"),
        "role": user.get("role"),
        "fullname": user.get("fullname")
    }

    # ✅ Return structured user info
    return jsonify({
        "message": "Login successful",
        "user": {
            "fullname": user.get("fullname"),
            "email": user.get("email"),
            "role": user.get("role")
        }
    }), 200


# ---------------- LOGOUT ----------------
@auth.route("/logout", methods=["POST"])
def logout():
    """Clears user session."""
    session.pop("user", None)
    return jsonify({"message": "Logged out successfully"}), 200


@auth.route("/create", methods=["POST"])
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

    

    # Check if email exists
    if users_collection.find_one({"email": email.lower()}):
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

    users_collection.insert_one(user)

    return jsonify({"message": "Signup successful!"}), 201




#------------send otp----------------
@auth.route("/send-otp", methods=["POST"])
def send_otp():
    data = request.get_json()
    email = data.get("email", "").lower()

    if not email:
        return jsonify({"message": "Email is required"}), 400

    user = users_collection.find_one({"email": email})
    if not user:
        return jsonify({"message": "No account found"}), 404

    fullname = user.get("fullname", "")
    otp = generate_otp()
    now = datetime.utcnow()

    ordered_fields = {
        "email": email,
        "fullname": fullname,
        "otp": otp,
        "expires_at": now + timedelta(minutes=5)
    }

    otps_collection.replace_one({"email": email}, ordered_fields, upsert=True)

    # 🚀 Send email in background (non-blocking)
    threading.Thread(target=send_email, args=(email, otp)).start()

    # 🚀 Return immediately (frontend will load OTP screen instantly)
    return jsonify({"message": "OTP sent"}), 200






#-----------------verify otp--------------------
@auth.route("/verify-otp", methods=["POST"])
def verify_otp():
    data = request.get_json()
    email = data.get("email", "").lower()
    otp = data.get("otp")

    otp_entry = otps_collection.find_one({"email": email})

    if not otp_entry:
        return jsonify({"message": "OTP not generated"}), 400

    now = datetime.utcnow()

    # Expired? delete it
    if now > otp_entry["expires_at"]:
        otps_collection.delete_one({"email": email})
        return jsonify({"message": "OTP expired"}), 400

    # Invalid OTP
    if otp_entry["otp"] != otp:
        return jsonify({"message": "Invalid OTP"}), 400

    return jsonify({"message": "OTP verified"}), 200



#-------------reset password------------------------
@auth.route("/reset-password", methods=["POST"])
def reset_password():
    data = request.get_json()
    email = data.get("email", "").lower()
    new_password = data.get("new_password")

    hashed_pw = bcrypt.generate_password_hash(new_password).decode("utf-8")

    # Update password
    users_collection.update_one(
        {"email": email},
        {"$set": {"password": hashed_pw}}
    )

    # Delete OTP after reset
    otps_collection.delete_one({"email": email})

    return jsonify({"message": "Password reset successful"}), 200



# ---------------- CHECK SESSION ----------------
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




# ---------------- REGISTER ----------------
# ---------------- REGISTER ----------------
@auth.route("/register", methods=["POST"])
def register():
    """Registers a new resident with Cloudinary photo/id proof uploads."""
    try:
        # Identify who created the record
        created_by = "System"
        if "user" in session:
            creator = session.get("user")
            created_by = (
                creator.get("username")
                or creator.get("email")
                or creator.get("phone")
            )

        # Extract form data
        full_name = request.form.get("fullName")
        gender = request.form.get("gender")
        dob = request.form.get("dob")
        phone = request.form.get("phone")
        alternate_number = request.form.get("alternateNumber")
        email = request.form.get("email")

        # ✅ Password fields
        password = request.form.get("password")
        confirm_password = request.form.get("confirmPassword")

        if not password:
            return jsonify({"message": "Password is required"}), 400
        if confirm_password and password != confirm_password:
            return jsonify({"message": "Passwords do not match"}), 400

        hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")

        # Remaining personal info
        aadhar = request.form.get("aadhar")
        address = request.form.get("address")
        occupation = request.form.get("occupation")
        ownership_type = request.form.get("ownershipType")
        tenant_start = request.form.get("tenantStartDate")
        tenant_end = request.form.get("tenantEndDate")
        block = request.form.get("block")
        flat_number = request.form.get("flatNumber")
        floor = request.form.get("floor")
        parking_slots = int(request.form.get("parkingSlots", 0))
        role = request.form.get("role", "resident")

       # ✅ Generate unique residentId
        def generate_resident_id(full_name, phone):
            """
            Generate readable resident ID like RES-CHA3210
            (3 letters from name + last 4 digits of phone)
            """
            try:
                name_part = (
                    "".join(filter(str.isalpha, full_name[:3].upper()))
                    if full_name
                    else "USR"
                )
                phone_suffix = str(phone)[-4:] if phone else "0000"
                return f"RES-{name_part}{phone_suffix}"
            except Exception as e:
                print("❌ Error generating residentId:", e)
                return f"RES-UNKNOWN-{uuid.uuid4().hex[:6].upper()}"

        resident_id = generate_resident_id(full_name, phone)

        # ✅ Emergency contact
        emergency_name = request.form.get("emergencyName")
        emergency_number = request.form.get("emergencyNumber")
        emergency_relation = request.form.get("emergencyRelation")

        # ✅ Family members
        family_members = []
        if "familyMembers" in request.form:
            try:
                family_members = json.loads(request.form["familyMembers"])
                print("👨‍👩‍👧 Parsed family members:", family_members)
            except Exception as e:
                print("❌ Error parsing familyMembers:", e)

        # ✅ Vehicles
        vehicles = []
        if "vehicles" in request.form:
            try:
                vehicles = json.loads(request.form["vehicles"])
                print("🚗 Parsed vehicles:", vehicles)
            except Exception as e:
                print("❌ Error parsing vehicles:", e)

        # ✅ Uploaded files
        photo = request.files.get("photo")
        id_proof = request.files.get("idProof")

        # ✅ Required fields validation
        if not full_name or not phone or not email:
            missing = [f for f in ["fullName", "phone", "email"] if not request.form.get(f)]
            return jsonify({"message": f"Missing required fields: {', '.join(missing)}"}), 400

        if flat_number:
            flat_number = flat_number.strip().upper()

        # ✅ Duplicate check
        duplicate_query = {
            "$or": [{"phone": phone}, {"email": email}, {"residentId": resident_id}]
        }
        if aadhar:
            duplicate_query["$or"].append({"aadhar": aadhar})

        existing_user = users_collection.find_one(duplicate_query)

        if existing_user:
            conflict_field = None
            if existing_user.get("phone") == phone:
                conflict_field = "phone number"
            elif existing_user.get("email") == email:
                conflict_field = "email address"
            elif existing_user.get("aadhar") == aadhar:
                conflict_field = "Aadhar number"
            elif existing_user.get("residentId") == resident_id:
                conflict_field = "Resident ID"
            return jsonify({
                "message": f"Resident with the same {conflict_field} already exists."
            }), 400

        # ✅ Upload to Cloudinary
        try:
            photo_url = upload_to_cloudinary(photo, "residents/photos") if photo else None
            id_proof_url = upload_to_cloudinary(id_proof, "residents/id_proofs") if id_proof else None
        except Exception as e:
            print("❌ Cloudinary upload failed:", e)
            return jsonify({"message": "Cloudinary upload error"}), 500

        # ✅ Build final MongoDB document
        resident_data = {
            "residentId": resident_id,  # ✅ Added here
            "fullName": full_name,
            "gender": gender,
            "dob": dob,
            "phone": phone,
            "alternateNumber": alternate_number,
            "email": email,
            "password": hashed_password,
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
            "photo": photo_url,
            "idProof": id_proof_url,
            "emergencyContact": {
                "name": emergency_name,
                "number": emergency_number,
                "relation": emergency_relation,
            },
            "familyMembers": family_members,
            "vehicles": vehicles,
            "role": role,
            "status": "unverified",
            "createdBy": created_by,
            "createdAt": datetime.utcnow(),
        }

        # ✅ Save to MongoDB
        users_collection.insert_one(resident_data)
        print(f"✅ Resident '{full_name}' registered successfully with ID {resident_id}")

        return jsonify({
            "message": f"Resident '{full_name}' registered successfully!",
            "residentId": resident_id,
            "photoURL": photo_url,
            "idProofURL": id_proof_url,
            "role": role,
            "status": "unverified",
            "createdBy": created_by,
        }), 201

    except Exception as e:
        print("❌ Server error:", e)
        traceback.print_exc()
        return jsonify({"message": "Server error while registering resident"}), 500














