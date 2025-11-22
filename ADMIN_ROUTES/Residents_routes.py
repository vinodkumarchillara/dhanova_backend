from flask import Blueprint, request, jsonify, session
from utils.db import db
from datetime import datetime ,timedelta
import traceback



admin = Blueprint('admin', __name__)

users_collection = db["users"]


# ---------------- ADMIN: VIEW ALL USERS ----------------
@admin.route("/residents", methods=["GET"])
def get_all_users():
    """Admins can view all registered users."""
    user = session.get("user")
    if not user or user["role"] != "admin":
        return jsonify({"message": "Access denied! Admins only."}), 403

    users = list(users_collection.find({}, {"_id": 0, "password": 0}))
    return jsonify({"users": users}), 200


#-----------------Edit resident----------------------
@admin.route("/residents/<resident_id>", methods=["PUT"])
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
@admin.route("/residents/update-status/<resident_id>", methods=["PUT"])
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
@admin.route("/residents/<residentId>", methods=["DELETE"])
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



