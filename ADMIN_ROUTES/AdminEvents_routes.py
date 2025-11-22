from flask import Blueprint, request, jsonify, session
from utils.db import db
from datetime import datetime ,timedelta
from bson import ObjectId
from bson import errors as bson_errors

adminevents = Blueprint('adminevents', __name__)
events_collection = db["AdminEvents"]



# ✅ Helper function to generate unique event IDs
def generate_event_id(event_title):
    """Generate a unique Event ID like EVTXYZ20251107123045"""
    prefix = "EVT"
    title_part = ''.join(filter(str.isalnum, event_title[:3].upper()))
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    return f"{prefix}{title_part}{timestamp}"


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


