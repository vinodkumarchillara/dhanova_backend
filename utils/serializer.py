from bson import ObjectId

def serialize_doc(doc):
    """Convert MongoDB ObjectId → string for any document."""
    if not doc:
        return doc

    doc["_id"] = str(doc["_id"])

    # Convert nested ObjectIds if they exist
    for key, value in doc.items():
        if isinstance(value, ObjectId):
            doc[key] = str(value)
        elif isinstance(value, list):
            doc[key] = [str(v) if isinstance(v, ObjectId) else v for v in value]

    return doc
