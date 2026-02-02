import os
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv

load_dotenv()

class CloudinaryTool:

    def __init__(self):
        cloudinary.config(
            cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
            api_key=os.getenv("CLOUDINARY_API_KEY"),
            api_secret=os.getenv("CLOUDINARY_API_SECRET"),
            secure=True
        )
        self.configured = self._check_configuration()
    
    def _check_configuration(self) -> bool:
        cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME")
        api_key = os.getenv("CLOUDINARY_API_KEY")
        api_secret = os.getenv("CLOUDINARY_API_SECRET")
        
        if not all([cloud_name, api_key, api_secret]):
            print("WARNING: Cloudinary not configured")
            print("Set CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, and CLOUDINARY_API_SECRET in .env")
            return False
        
        return True
    
    def upload_image(self, file_path: str, folder: str = "estate_scout", public_id: str = None) -> dict:

        if not self.configured:
            return {
                "success": False,
                "error": "Cloudinary not configured",
                "url": None
            }
        
        if not os.path.exists(file_path):
            return {
                "success": False,
                "error": f"File not found: {file_path}",
                "url": None
            }
        
        try:
            print(f"Uploading image to Cloudinary: {file_path}")
            
            upload_options = {
                "folder": folder,
                "resource_type": "image",
                "quality": "auto:good",
                "fetch_format": "auto",
            }
            
            if public_id:
                upload_options["public_id"] = public_id
            
            result = cloudinary.uploader.upload(file_path, **upload_options)
            
            print(f"Image uploaded successfully")
            print(f"URL: {result['secure_url']}")
            print(f"Public ID: {result['public_id']}")
            
            return {
                "success": True,
                "url": result['secure_url'],
                "public_id": result['public_id'],
                "thumbnail_url": result.get('thumbnail_url'),
                "width": result.get('width'),
                "height": result.get('height')
            }
            
        except Exception as e:
            print(f"Error uploading to Cloudinary: {e}")
            return {
                "success": False,
                "error": str(e),
                "url": None
            }
    
    def delete_image(self, public_id: str) -> bool:
        if not self.configured:
            return False
        
        try:
            result = cloudinary.uploader.destroy(public_id)
            return result.get('result') == 'ok'
        except Exception as e:
            print(f"Error deleting from Cloudinary: {e}")
            return False
    
    def get_image_url(self, public_id: str, transformation: dict = None) -> str:
        
        if not self.configured:
            return None
        
        try:
            url, options = cloudinary.utils.cloudinary_url(
                public_id,
                **transformation if transformation else {}
            )
            return url
        except Exception as e:
            print(f"Error generating URL: {e}")
            return None
