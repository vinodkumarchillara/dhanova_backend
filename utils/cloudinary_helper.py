import cloudinary
import cloudinary.uploader


def upload_to_cloudinary(file, folder_name):
    """
    Uploads a file to Cloudinary under a specific folder.
    Returns the secure URL if successful, else None.
    """
    if not file:
        return None  # No file uploaded

    try:
        upload_result = cloudinary.uploader.upload(
            file,
            folder=folder_name,
            resource_type="auto"  # auto-detects image/pdf/video, etc.
        )
        return upload_result.get("secure_url")

    except Exception as e:
        print(f"❌ Cloudinary upload failed for folder '{folder_name}': {str(e)}")
        return None
