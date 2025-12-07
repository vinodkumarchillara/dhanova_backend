from flask import Blueprint, request, jsonify
from utils.db import db
from utils.serializer import serialize_doc
from bson import ObjectId
from datetime import datetime

residentsbookings = Blueprint('residentsbookings', __name__)
bookings_collection = db["resident_bookings"]
admin_events = db["AdminEvents"]


# ---------------- GET ALL BOOKINGS ----------------
@residentsbookings.route("/get", methods=["GET"])
def get_bookings():
    data = list(bookings_collection.find())
    return jsonify([serialize_doc(b) for b in data]), 200


# ---------------- ADD BOOKING (UNIFIED) ----------------
@residentsbookings.route("/add", methods=["POST"])
def add_booking():
    data = request.get_json()

    required = ["residentName", "flatno", "block", "title", "eventStartDate"]
    for f in required:
        if not data.get(f):
            return jsonify({"error": f"{f} is required"}), 400

    is_multi = data.get("isMultiDay", False)
    requires_hall = data.get("requiresHall", False)

    # Normalize single day
    data["eventEndDate"] = data["eventEndDate"] if is_multi else data["eventStartDate"]

    # ---------------- HALL VALIDATION ----------------
    if requires_hall:

        hall_start = data.get("hallStartDate") or data["eventStartDate"]
        hall_end = data.get("hallEndDate") or data["eventEndDate"]

        if not data.get("hallName"):
            return jsonify({"error": "hallName required"}), 400

        if not data.get("hallStartTime") or not data.get("hallEndTime"):
            return jsonify({"error": "hall times required"}), 400

        # ---- CHECK ADMIN EVENTS CONFLICT ----
        admin_conflict = admin_events.find_one({
            "requiresHall": True,
            "hallName": data["hallName"],
            "eventStartDate": {"$lte": hall_end},
            "eventEndDate": {"$gte": hall_start}
        })

        if admin_conflict:
            return jsonify({
                "error": "Hall booked",
                "conflictType": "admin",
                "eventTitle": admin_conflict.get("title")
            }), 409

        # ---- CHECK RESIDENT BOOKINGS CONFLICT ----
        resident_conflict = bookings_collection.find_one({
            "requiresHall": True,
            "hallName": data["hallName"],
            "eventStartDate": {"$lte": hall_end},
            "eventEndDate": {"$gte": hall_start}
        })

        if resident_conflict:
            return jsonify({
                "error": "Hall booked",
                "conflictType": "resident",
                "residentName": resident_conflict.get("residentName"),
                "eventTitle": resident_conflict.get("title")
            }), 409

    data["status"] = "Pending"
    data["created_at"] = datetime.utcnow()

    saved = bookings_collection.insert_one(data)
    data["_id"] = str(saved.inserted_id)

    return jsonify(data), 201


# ---------------- UPDATE BOOKING (UNIFIED) ----------------
@residentsbookings.route("/update/<id>", methods=["PUT"])
def update_booking(id):
    data = request.get_json()

    # Required unified fields
    required = ["residentName", "flatno", "block", "title", "eventStartDate"]
    for f in required:
        if not data.get(f):
            return jsonify({"error": f"{f} is required"}), 400

    is_multi = data.get("isMultiDay", False)
    requires_hall = data.get("requiresHall", False)

    # Normalize single-day
    data["eventEndDate"] = data["eventEndDate"] if is_multi else data["eventStartDate"]

    # ---------------- HALL VALIDATION ----------------
    if requires_hall:

        hall_start = data.get("hallStartDate") or data["eventStartDate"]
        hall_end = data.get("hallEndDate") or data["eventEndDate"]

        if not data.get("hallName"):
            return jsonify({"error": "hallName required"}), 400

        if not data.get("hallStartTime") or not data.get("hallEndTime"):
            return jsonify({"error": "hall times required"}), 400

        # ---- RESIDENT conflict excluding current booking ----
        resident_conflict = bookings_collection.find_one({
            "_id": {"$ne": ObjectId(id)},
            "requiresHall": True,
            "hallName": data["hallName"],
            "eventStartDate": {"$lte": hall_end},
            "eventEndDate": {"$gte": hall_start}
        })

        if resident_conflict:
            return jsonify({
                "error": "Hall booked",
                "conflictType": "resident",
                "residentName": resident_conflict.get("residentName"),
                "eventTitle": resident_conflict.get("title")
            }), 409

        # ---- ADMIN conflict ----
        admin_conflict = admin_events.find_one({
            "requiresHall": True,
            "hallName": data["hallName"],
            "eventStartDate": {"$lte": hall_end},
            "eventEndDate": {"$gte": hall_start}
        })

        if admin_conflict:
            return jsonify({
                "error": "Hall booked",
                "conflictType": "admin",
                "eventTitle": admin_conflict.get("title")
            }), 409

    # -------- UPDATE --------
    data["updated_at"] = datetime.utcnow()

    bookings_collection.update_one(
        {"_id": ObjectId(id)},
        {"$set": data}
    )

    updated = bookings_collection.find_one({"_id": ObjectId(id)})
    return jsonify(serialize_doc(updated)), 200


# ---------------- APPROVE ----------------
@residentsbookings.route("/approve/<id>", methods=["PATCH"])
def approve_booking(id):
    bookings_collection.update_one(
        {"_id": ObjectId(id)},
        {"$set": {"status": "Approved", "updated_at": datetime.utcnow()}}
    )
    updated = bookings_collection.find_one({"_id": ObjectId(id)})
    return jsonify(serialize_doc(updated)), 200


# ---------------- REJECT ----------------
@residentsbookings.route("/reject/<id>", methods=["PATCH"])
def reject_booking(id):
    bookings_collection.update_one(
        {"_id": ObjectId(id)},
        {"$set": {"status": "Rejected", "updated_at": datetime.utcnow()}}
    )
    updated = bookings_collection.find_one({"_id": ObjectId(id)})
    return jsonify(serialize_doc(updated)), 200


# ---------------- DELETE ----------------
@residentsbookings.route("/delete/<id>", methods=["DELETE"])
def delete_booking(id):
    bookings_collection.delete_one({"_id": ObjectId(id)})
    return jsonify({"message": "Booking deleted"}), 200
