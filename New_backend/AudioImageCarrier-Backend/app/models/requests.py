from pydantic import BaseModel
from typing import Optional

class EncodeRequest(BaseModel):
    audio_file: bytes  # The audio file to be encoded
    user: str          # User ID for key derivation
    master_key: Optional[str] = None  # Master key in hexadecimal format (optional)

class DecodeRequest(BaseModel):
    image_files: bytes  # The ZIP file containing the PNG images
    user: str           # User ID used for encryption
    master_key: Optional[str] = None  # Master key in hexadecimal format (optional)