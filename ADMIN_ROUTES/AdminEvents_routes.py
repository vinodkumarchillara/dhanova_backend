from flask import Blueprint, request, jsonify, session
from utils.db import db
from datetime import datetime
from bson import ObjectId

adminevents = Blueprint('adminevents', __name__)

events_collection = db["AdminEvents"]
resident_bookings = db["resident_bookings"]


# ------------------ Helper: Generate Unique Event ID ------------------
def generate_event_id(title):
    prefix = "EVT"
    clean = ''.join(filter(str.isalnum, title[:3].upper()))
    ts = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    return f"{prefix}{clean}{ts}"


# ============================================================================
# ✅ CREATE EVENT (SAFE + UNIFIED)
# ============================================================================
@adminevents.route("/create", methods=["POST"])
def create_event():
    data = request.get_json()

    required = ["title", "eventStartDate", "eventStartTime", "eventEndTime"]
    for f in required:
        if not data.get(f):
            return jsonify({"error": f"{f} is required"}), 400

    is_multi = data.get("isMultiDay", False)
    requires_hall = data.get("requiresHall", False)

    start_date = data["eventStartDate"]
    end_date = data.get("eventEndDate") if is_multi else start_date

    created_by = session.get("user", {}).get("email", "System")

    # ---------------- HALL VALIDATION ----------------
    if requires_hall:

        hall_start = data.get("hallStartDate") or start_date
        hall_end = data.get("hallEndDate") or end_date

        if not data.get("hallName"):
            return jsonify({"error": "hallName required"}), 400

        if not data.get("hallStartTime") or not data.get("hallEndTime"):
            return jsonify({"error": "Hall times required"}), 400

        # Check admin events conflict
        conflict_admin = events_collection.find_one({
            "requiresHall": True,
            "hallName": data["hallName"],
            "eventStartDate": {"$lte": hall_end},
            "eventEndDate": {"$gte": hall_start}
        })

        if conflict_admin:
            return jsonify({
                "error": "Hall booked by admin",
                "eventTitle": conflict_admin["title"]
            }), 409

        # Check resident booking conflict
        conflict_resident = resident_bookings.find_one({
            "requiresHall": True,
            "hallName": data["hallName"],
            "eventStartDate": {"$lte": hall_end},
            "eventEndDate": {"$gte": hall_start}
        })

        if conflict_resident:
            return jsonify({
                "error": "Hall booked by resident",
                "residentName": conflict_resident.get("residentName"),
                "eventTitle": conflict_resident.get("title"),
            }), 409

    # ---------------- Create Event ----------------
    event_id = generate_event_id(data["title"])

    doc = {
        "event_id": event_id,
        "title": data["title"],
        "description": data.get("description", ""),
        "isMultiDay": is_multi,
        "eventStartDate": start_date,
        "eventEndDate": end_date,
        "eventStartTime": data["eventStartTime"],
        "eventEndTime": data["eventEndTime"],
        "requiresHall": requires_hall,
        "status": "pending",
        "created_by": created_by,
        "created_at": datetime.utcnow(),
        "updated_by": created_by,
        "updated_at": datetime.utcnow(),
    }

    if requires_hall:
        doc.update({
            "hallName": data["hallName"],
            "hallNotes": data.get("hallNotes", ""),
            "hallStartDate": data.get("hallStartDate") or start_date,
            "hallEndDate": data.get("hallEndDate") or end_date,
            "hallStartTime": data["hallStartTime"],
            "hallEndTime": data["hallEndTime"],
        })

    events_collection.insert_one(doc)

    return jsonify({"message": "Admin Event Created", "event_id": event_id}), 201



# ============================================================================
# ✅ GET ALL EVENTS
# ============================================================================
@adminevents.route("/list", methods=["GET"])
def get_events():
    events = list(events_collection.find())
    for e in events:
        e["_id"] = str(e["_id"])
    return jsonify({"events": events}), 200



# ============================================================================
# ✅ GET SINGLE EVENT
# ============================================================================
@adminevents.route("/<id>", methods=["GET"])
def get_event(id):
    event = events_collection.find_one({"event_id": id}) or \
            events_collection.find_one({"_id": ObjectId(id)})

    if not event:
        return jsonify({"error": "Event not found"}), 404

    event["_id"] = str(event["_id"])
    return jsonify(event), 200



# ============================================================================
# ✅ UPDATE EVENT (SAFE UPDATE + MERGE OLD + NEW)
# ============================================================================
@adminevents.route("/update/<id>", methods=["PUT"])
def update_event(id):
    new = request.get_json()

    # --- Fetch existing event ---
    old = events_collection.find_one({"_id": ObjectId(id)})
    if not old:
        return jsonify({"error": "Event not found"}), 404

    # --- Merge old + new values ---
    data = {**old, **new}

    is_multi = data.get("isMultiDay", False)
    requires_hall = data.get("requiresHall", False)

    start_date = data.get("eventStartDate")
    end_date = data.get("eventEndDate") if is_multi else start_date

    # Update metadata
    data["updated_by"] = session.get("user", {}).get("email", "System")
    data["updated_at"] = datetime.utcnow()

    # ---------------- HALL VALIDATION ----------------
    if requires_hall:

        hall_start = data.get("hallStartDate") or start_date
        hall_end = data.get("hallEndDate") or end_date

        if not data.get("hallName"):
            return jsonify({"error": "hallName required"}), 400

        # Check resident conflict
        conflict_resident = resident_bookings.find_one({
            "requiresHall": True,
            "hallName": data["hallName"],
            "eventStartDate": {"$lte": hall_end},
            "eventEndDate": {"$gte": hall_start},
        })

        if conflict_resident:
            return jsonify({
                "error": "Hall booked by resident",
                "eventTitle": conflict_resident.get("title"),
                "residentName": conflict_resident.get("residentName"),
            }), 409

        # Check admin conflict excluding self
        conflict_admin = events_collection.find_one({
            "_id": {"$ne": ObjectId(id)},
            "requiresHall": True,
            "hallName": data["hallName"],
            "eventStartDate": {"$lte": hall_end},
            "eventEndDate": {"$gte": hall_start},
        })

        if conflict_admin:
            return jsonify({
                "error": "Hall booked by admin",
                "eventTitle": conflict_admin.get("title"),
            }), 409

    # ---------------- UPDATE EVENT ----------------
    data["_id"] = ObjectId(id)
    events_collection.replace_one({"_id": ObjectId(id)}, data)

    return jsonify({"message": "Event updated"}), 200



# ============================================================================
# ✅ DELETE EVENT
# ============================================================================
@adminevents.route("/delete/<id>", methods=["DELETE"])
def delete_event(id):
    result = events_collection.delete_one({"_id": ObjectId(id)})

    if result.deleted_count == 0:
        return jsonify({"error": "Event not found"}), 404

    return jsonify({"message": "Event deleted"}), 200
