import cloudinary
import cloudinary.uploader

def upload_to_cloudinary(file, resident_id, subfolder):
    """
    Upload a file to Cloudinary in this structure:
    residents/<resident_id>/<subfolder>/
    Returns a dict with URL and public_id if successful.
    """
    if not file:
        return None

    try:
        folder_path = f"residents/{resident_id}/{subfolder}"
        upload_result = cloudinary.uploader.upload(
            file,
            folder=folder_path,
            resource_type="auto"  # auto-detect image/pdf/video/etc
        )
        return {
            "url": upload_result.get("secure_url"),
            "public_id": upload_result.get("public_id")
        }
    except Exception as e:
        print(f"❌ Cloudinary upload failed for {folder_path}: {str(e)}")
        return None
