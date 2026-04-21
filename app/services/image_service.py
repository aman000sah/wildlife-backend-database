import os
import uuid
from pathlib import Path

# Local storage folder (we'll use Firebase later)
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

def save_image_locally(image_bytes: bytes, filename: str) -> str:
    """Save image locally and return the file path."""
    ext = filename.split(".")[-1] if "." in filename else "jpg"
    unique_name = f"{uuid.uuid4()}.{ext}"
    file_path = UPLOAD_DIR / unique_name
    
    with open(file_path, "wb") as f:
        f.write(image_bytes)
    
    return str(file_path)