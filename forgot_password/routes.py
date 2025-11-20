from flask import request, jsonify
from flask_bcrypt import Bcrypt
from datetime import datetime, timedelta
from . import forgot_bp
from .utils import generate_otp, send_email
from signup.db import mongo
import threading

bcrypt = Bcrypt()

#------------send otp----------------
@forgot_bp.route("/send-otp", methods=["POST"])
def send_otp():
    data = request.get_json()
    email = data.get("email", "").lower()

    if not email:
        return jsonify({"message": "Email is required"}), 400

    user = mongo.db.users.find_one({"email": email})
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

    mongo.db.otps.replace_one({"email": email}, ordered_fields, upsert=True)

    # 🚀 Send email in background (non-blocking)
    threading.Thread(target=send_email, args=(email, otp)).start()

    # 🚀 Return immediately (frontend will load OTP screen instantly)
    return jsonify({"message": "OTP sent"}), 200






#-----------------verify otp--------------------
@forgot_bp.route("/verify-otp", methods=["POST"])
def verify_otp():
    data = request.get_json()
    email = data.get("email", "").lower()
    otp = data.get("otp")

    otp_entry = mongo.db.otps.find_one({"email": email})

    if not otp_entry:
        return jsonify({"message": "OTP not generated"}), 400

    now = datetime.utcnow()

    # Expired? delete it
    if now > otp_entry["expires_at"]:
        mongo.db.otps.delete_one({"email": email})
        return jsonify({"message": "OTP expired"}), 400

    # Invalid OTP
    if otp_entry["otp"] != otp:
        return jsonify({"message": "Invalid OTP"}), 400

    return jsonify({"message": "OTP verified"}), 200



#-------------reset password------------------------
@forgot_bp.route("/reset-password", methods=["POST"])
def reset_password():
    data = request.get_json()
    email = data.get("email", "").lower()
    new_password = data.get("new_password")

    hashed_pw = bcrypt.generate_password_hash(new_password).decode("utf-8")

    # Update password
    mongo.db.users.update_one(
        {"email": email},
        {"$set": {"password": hashed_pw}}
    )

    # Delete OTP after reset
    mongo.db.otps.delete_one({"email": email})

    return jsonify({"message": "Password reset successful"}), 200

