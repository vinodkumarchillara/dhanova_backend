from flask import Blueprint, request, jsonify, session
from utils.db import db
from bson import ObjectId

residentsbookings = Blueprint('residentsbookings', __name__)
bookings_collection = db["resident_bookings"]



def serialize(b):
    b["_id"] = str(b["_id"])
    return b


# ------------ GET ALL BOOKINGS --------------
@residentsbookings.route("/get", methods=["GET"])
def get_bookings():
    data = list(bookings_collection.find())
    return jsonify([serialize(b) for b in data])


# ------------ ADD NEW BOOKING ---------------
@residentsbookings.route("/add", methods=["POST"])
def add_booking():
    new_booking = request.json

    new_booking["status"] = "Pending"

    result = bookings_collection.insert_one(new_booking)
    new_booking["_id"] = str(result.inserted_id)

    return jsonify(new_booking), 201


# ------------ UPDATE BOOKING ----------------
@residentsbookings.route("/update/<id>", methods=["PUT"])
def update_booking(id):
    data = request.json
    bookings_collection.update_one(
        {"_id": ObjectId(id)},
        {"$set": data}
    )
    return jsonify({"message": "Booking updated successfully"})


# ------------ APPROVE BOOKING ---------------
@residentsbookings.route("/approve/<id>", methods=["PATCH"])
def approve_booking(id):
    bookings_collection.update_one(
        {"_id": ObjectId(id)},
        {"$set": {"status": "Approved"}}
    )
    return jsonify({"message": "Booking approved"})

# ------------ REJECT BOOKING ----------------
@residentsbookings.route("/reject/<id>", methods=["PATCH"])
def reject_booking(id):
    bookings_collection.update_one(
        {"_id": ObjectId(id)},
        {"$set": {"status": "Rejected"}}
    )
    return jsonify({"message": "Booking rejected"})


# ------------ DELETE BOOKING ----------------
@residentsbookings.route("/delete/<id>", methods=["DELETE"])
def delete_booking(id):
    bookings_collection.delete_one({"_id": ObjectId(id)})
    return jsonify({"message": "Booking deleted"})
