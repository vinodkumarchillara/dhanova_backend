from flask import Blueprint, request, jsonify, session
from utils.db import db
from flask_bcrypt import Bcrypt
from bson import ObjectId
from datetime import datetime
from bson import errors as bson_errors
from utils.cloudinary_helper import upload_to_cloudinary
from config import CLOUDINARY_CONFIG  
import uuid
import traceback
import json
from flask import session


auth = Blueprint('auth', __name__)
bcrypt = Bcrypt()
users_collection = db["users"]

adminevents = Blueprint("adminevents", __name__)
events_collection = db["AdminEvents"]

# ✅ Helper function to generate unique event IDs
def generate_event_id(event_title):
    """Generate a unique Event ID like EVTXYZ20251107123045"""
    prefix = "EVT"
    title_part = ''.join(filter(str.isalnum, event_title[:3].upper()))
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    return f"{prefix}{title_part}{timestamp}"

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


# ---------------- ADMIN: VIEW ALL USERS ----------------
@auth.route("/users", methods=["GET"])
def get_all_users():
    """Admins can view all registered users."""
    user = session.get("user")
    if not user or user["role"] != "admin":
        return jsonify({"message": "Access denied! Admins only."}), 403

    users = list(users_collection.find({}, {"_id": 0, "password": 0}))
    return jsonify({"users": users}), 200



#-----------------Edit resident----------------------
@auth.route("/residents/<resident_id>", methods=["PUT"])
def update_resident_details(resident_id):
    """Update resident profile details (Full Name, Phone, etc.)"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"message": "No data received"}), 400

        print(f"➡️ Updating resident: {resident_id}")
        print(f"➡️ Data received: {data}")

        # ✅ Get currently logged-in user from session
        updated_by = "System"
        if "user" in session:
            user = session.get("user")
            updated_by = (
                user.get("email") or 
                user.get("username") or 
                user.get("phone") or 
                "Unknown"
            )

        # ✅ Validate residentId format if needed
        # (If residentId is a string like R-101, skip ObjectId conversion)
        result = users_collection.update_one(
            {"residentId": resident_id},  # match by your unique residentId
            {"$set": {
                **data,
                "updatedBy": updated_by,   # 👈 add this field
                "updatedAt": datetime.utcnow()  # 👈 track timestamp
            }}
        )

        if result.matched_count == 0:
            return jsonify({"message": "Resident not found"}), 404

        print(f"✅ Resident updated successfully by {updated_by}")
        return jsonify({"message": f"Resident updated successfully by {updated_by}!"}), 200

    except Exception as e:
        print("❌ Error updating resident:", e)
        traceback.print_exc()
        return jsonify({"message": "Server error while updating resident"}), 500




# ============================================================
# ✅ 2️⃣ UPDATE RESIDENT STATUS (Verified / Unverified)
# ============================================================
@auth.route("/residents/update-status/<resident_id>", methods=["PUT"])
def update_resident_status(resident_id):
    """Update resident verification status"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"message": "Missing request body"}), 400

        new_status = data.get("status")
        if new_status not in ["verified", "unverified"]:
            return jsonify({"message": "Invalid status value"}), 400

        print(f"➡️ Updating status for residentId: {resident_id} to {new_status}")

        # 🔧 No ObjectId conversion here — use custom residentId
        result = users_collection.update_one(
            {"residentId": resident_id},
            {"$set": {"status": new_status}}
        )

        if result.matched_count == 0:
            print("❌ Resident not found in DB")
            return jsonify({"message": "Resident not found"}), 404

        print(f"✅ Status updated to '{new_status}'")
        return jsonify({"message": f"Resident status updated to '{new_status}'"}), 200

    except Exception as e:
        print("❌ Error updating resident status:", e)
        traceback.print_exc()
        return jsonify({"message": "Server error while updating resident status"}), 500



# ============================================================
# ✅ 3️⃣ DELETE RESIDENT
# ============================================================
@auth.route("/residents/<residentId>", methods=["DELETE"])
def delete_resident(residentId):
    """Delete a resident by residentId"""
    try:
        print(f"➡️ Attempting to delete resident (residentId): {residentId}")

        result = users_collection.delete_one({"residentId": residentId})

        if result.deleted_count == 0:
            print("❌ Resident not found in DB")
            return jsonify({"message": "Resident not found"}), 404

        print(f"✅ Resident {residentId} deleted successfully")
        return jsonify({"message": "Resident deleted successfully"}), 200

    except Exception as e:
        print("❌ Error deleting resident:", e)
        traceback.print_exc()
        return jsonify({"message": "Server error while deleting resident"}), 500





# ---------------- CREATE ADMIN EVENT ----------------
@adminevents.route("/create", methods=["POST"])
def create_event():
    data = request.get_json()

    event_title = data.get("event_title")
    description = data.get("description")
    event_date = data.get("event_date")
    event_time = data.get("event_time")
    requires_hall = data.get("requires_community_hall", False)

    # ✅ Get creator email from session
    created_by = "System"
    if "user" in session:
        creator = session.get("user")
        created_by = creator.get("email", "Unknown")

    # Validation
    if not event_title or not event_date or not event_time:
        return jsonify({"error": "Missing required fields"}), 400

    # ✅ Generate custom event_id
    event_id = generate_event_id(event_title)

    # ✅ Build event document
    event_data = {
        "event_id": event_id,
        "event_title": event_title,
        "description": description,
        "event_date": event_date,
        "event_time": event_time,
        "requires_community_hall": requires_hall,
        "created_by": created_by,
        "created_at": datetime.utcnow(),
        "updated_by": created_by,
        "updated_at": datetime.utcnow(),
        "status": "pending",
    }

    if requires_hall:
        event_data["hall_name"] = data.get("hall_name", "")
        event_data["hall_timings"] = data.get("hall_timings", "")
        event_data["notes"] = data.get("notes", "")

    result = events_collection.insert_one(event_data)

    return jsonify({
        "message": "Admin event created successfully",
        "event_id": event_id
    }), 201


# ---------------- GET ALL EVENTS ----------------
@adminevents.route("/list", methods=["GET"])
def get_all_events():
    events = list(events_collection.find())
    for event in events:
        event["_id"] = str(event["_id"])
    return jsonify({
        "total_events": len(events),
        "events": events
    }), 200


# ---------------- GET EVENT BY CUSTOM ID ----------------
@adminevents.route("/<event_id>", methods=["GET"])
def get_event(event_id):
    try:
        # First try custom event_id
        event = events_collection.find_one({"event_id": event_id})

        # Fallback: Try ObjectId
        if not event:
            try:
                object_id = ObjectId(event_id)
                event = events_collection.find_one({"_id": object_id})
            except bson_errors.InvalidId:
                return jsonify({"error": "Invalid event ID format"}), 400

        if not event:
            return jsonify({"error": "Event not found"}), 404

        event["_id"] = str(event["_id"])
        return jsonify(event), 200

    except Exception as e:
        print("❌ Error fetching event:", e)
        return jsonify({"error": "Server error fetching event"}), 500


# ---------------- UPDATE EVENT BY CUSTOM ID ----------------
@adminevents.route("/update/<event_id>", methods=["PUT"])
def update_event(event_id):
    try:
        data = request.get_json()

        # ✅ Get updater email from session
        updated_by = "System"
        if "user" in session:
            user = session.get("user")
            updated_by = user.get("email", "Unknown")

        data["updated_at"] = datetime.utcnow()
        data["updated_by"] = updated_by

        # Try to update by event_id first
        result = events_collection.update_one(
            {"event_id": event_id},
            {"$set": data}
        )

        # Fallback: Try ObjectId if no match
        if result.matched_count == 0:
            try:
                object_id = ObjectId(event_id)
                result = events_collection.update_one(
                    {"_id": object_id}, {"$set": data}
                )
            except bson_errors.InvalidId:
                return jsonify({"error": "Invalid event ID format"}), 400

        if result.matched_count == 0:
            return jsonify({"error": "Event not found"}), 404

        return jsonify({"message": "Event updated successfully"}), 200

    except Exception as e:
        print("❌ Error updating event:", e)
        return jsonify({"error": "Server error updating event"}), 500


# ---------------- DELETE EVENT BY CUSTOM ID ----------------
@adminevents.route("/delete/<event_id>", methods=["DELETE"])
def delete_event(event_id):
    try:
        print(f"➡️ Attempting to delete event with ID: {event_id}")

        # Try delete by custom event_id first
        result = events_collection.delete_one({"event_id": event_id})

        # Fallback: Try by MongoDB ObjectId
        if result.deleted_count == 0:
            try:
                object_id = ObjectId(event_id)
                result = events_collection.delete_one({"_id": object_id})
            except bson_errors.InvalidId:
                print("❌ Invalid event ID format")
                return jsonify({"error": "Invalid event ID format"}), 400

        if result.deleted_count == 0:
            print("❌ Event not found")
            return jsonify({"error": "Event not found"}), 404

        print(f"✅ Event {event_id} deleted successfully")
        return jsonify({"message": "Event deleted successfully"}), 200

    except Exception as e:
        print("❌ Error deleting event:", e)
        return jsonify({"error": "Server error while deleting event"}), 500



