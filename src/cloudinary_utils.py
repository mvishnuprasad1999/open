import cloudinary
import cloudinary.uploader
from src.db_core.setting import setup


cloudinary.config(
    cloud_name=setup.CLOUDINARY_NAME,
    api_key=setup.CLOUDINARY_APIKEY,
    api_secret=setup.CLOUDINARY_API_KEY_SECRET
)


def upload_image(file=None, path: str = None):
    try:
        if file:
            # FastAPI UploadFile
            result = cloudinary.uploader.upload(file.file)

        elif path:
            # Local file path
            result = cloudinary.uploader.upload(path)

        else:
            raise ValueError("Provide either file or path")

        return {
            "url": result.get("secure_url"),
            "public_id": result.get("public_id")
        }

    except Exception as e:
        raise Exception(f"Cloudinary upload failed: {str(e)}")