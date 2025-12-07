from flask import Blueprint, request, jsonify, session
from utils.db import db
from utils.serializer import serialize_doc
from bson import ObjectId
from datetime import datetime, timedelta
from dateutil.parser import parse

amenities = Blueprint('amenities', __name__)
halls_collection = db["halls"]
admin_events = db["AdminEvents"]
resident_bookings = db["resident_bookings"]
# ➤ GET all halls
@amenities.route("/halls", methods=["GET"])
def get_halls():
    halls = list(halls_collection.find())
    halls = [serialize_doc(h) for h in halls]
    return jsonify(halls), 200

# ➤ GET single hall
@amenities.route("/halls/<id>", methods=["GET"])
def get_hall(id):
    hall = halls_collection.find_one({"_id": ObjectId(id)})
    if not hall:
        return jsonify({"error": "Hall not found"}), 404
    return jsonify(serialize_doc(hall)), 200

# ➤ ADD new hall
@amenities.route("/halls", methods=["POST"])
def add_hall():
    data = request.json

    new_hall = {
        "name": data.get("name"),
        "capacity": data.get("capacity"),
        "location": data.get("location"),
        "amenities": data.get("amenities", []),
        "status": "Available",
        "bookings": []
    }

    result = halls_collection.insert_one(new_hall)
    new_hall["_id"] = str(result.inserted_id)

    return jsonify(new_hall), 201

# ➤ UPDATE hall
@amenities.route("/halls/<id>", methods=["PUT"])
def update_hall(id):
    data = request.json

    update_data = {k: v for k, v in data.items() if v is not None}

    halls_collection.update_one({"_id": ObjectId(id)}, {"$set": update_data})
    updated = halls_collection.find_one({"_id": ObjectId(id)})

    return jsonify(serialize_doc(updated)), 200

# ➤ DELETE hall
@amenities.route("/halls/<id>", methods=["DELETE"])
def delete_hall(id):
    halls_collection.delete_one({"_id": ObjectId(id)})
    return jsonify({"message": "Hall deleted"}), 200

# ➤ ADD booking date
@amenities.route("/halls/<id>/book", methods=["POST"])
def add_booking(id):
    data = request.json
    new_date = data.get("date")

    hall = halls_collection.find_one({"_id": ObjectId(id)})

    if not hall:
        return jsonify({"error": "Hall not found"}), 404

    # Prevent duplicate booking
    if new_date in hall["bookings"]:
        return jsonify({"error": "Date already booked"}), 400

    halls_collection.update_one(
        {"_id": ObjectId(id)},
        {"$push": {"bookings": new_date}, "$set": {"status": "Booked"}}
    )

    updated = halls_collection.find_one({"_id": ObjectId(id)})
    return jsonify(serialize_doc(updated)), 200



@amenities.route("/hall-names", methods=["GET"])
def get_hall_names():
    halls = halls_collection.find({}, {"name": 1})   # fetch only name field
    result = [{"_id": str(h["_id"]), "name": h["name"]} for h in halls]
    return jsonify(result), 200


def get_date_range(start, end):
    """Return list of YYYY-MM-DD strings between two dates"""
    dates = []
    current = start
    while current <= end:
        dates.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)
    return dates

@amenities.route("/halls/bookings/<hall_name>", methods=["GET"])
def get_hall_bookings(hall_name):
    try:
        hall_name = hall_name.strip()
        final_bookings = []

        # Helper: expand multi-day → list of dates
        def expand_dates(start, end):
            dates = []
            start_d = datetime.strptime(start, "%Y-%m-%d")
            end_d = datetime.strptime(end, "%Y-%m-%d")
            total_days = (end_d - start_d).days

            for i in range(total_days + 1):
                d = start_d + timedelta(days=i)
                dates.append(d.strftime("%Y-%m-%d"))
            return dates

        # ---------------------------------------------------
        # FETCH ADMIN EVENTS
        # ---------------------------------------------------
        admin_events = list(db.AdminEvents.find({
            "hallName": hall_name,
            "requiresHall": True,
            "status": {"$in": ["approved", "Approved"]}
        }))

        # PROCESS ADMIN EVENTS
        for ev in admin_events:
            start = ev.get("hallStartDate")
            end = ev.get("hallEndDate")
            title = ev.get("title", "Admin Event")

            if not start or not end:
                continue

            dates = expand_dates(start, end)

            for d in dates:
                final_bookings.append({
                    "date": d,
                    "eventName": title,
                    "source": "admin"
                })

        # ---------------------------------------------------
        # FETCH RESIDENT BOOKINGS
        # ---------------------------------------------------
        resident_events = list(db.resident_bookings.find({
            "hallName": hall_name,
            "requiresHall": True,
            "status": {"$in": ["approved", "Approved", "Pending", "pending"]}
        }))

        # PROCESS RESIDENT BOOKINGS
        for ev in resident_events:
            start = ev.get("hallStartDate")
            end = ev.get("hallEndDate")
            title = ev.get("title", "Resident Event")
            resident_name = ev.get("residentName", "Unknown")

            if not start or not end:
                continue

            dates = expand_dates(start, end)

            for d in dates:
                final_bookings.append({
                    "date": d,
                    "eventName": title,
                    "residentName": resident_name,  # ✔ Included only for residents
                    "source": "resident"
                })

        # Sort by date
        final_bookings = sorted(final_bookings, key=lambda x: x["date"])

        return jsonify({"bookings": final_bookings})

    except Exception as e:
        print("ERROR:", e)
        return jsonify({"error": str(e)}), 500
