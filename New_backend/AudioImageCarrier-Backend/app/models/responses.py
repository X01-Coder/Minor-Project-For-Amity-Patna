from pydantic import BaseModel
from typing import List, Optional

class EncodeResponse(BaseModel):
    images_zip: str
    temp_dir: str

class DecodeResponse(BaseModel):
    audio_file: str

class ErrorResponse(BaseModel):
    detail: str

class UserParameterExplanation(BaseModel):
    user: str
    explanation: str = "The user parameter is used to derive a unique encryption key for each user. This ensures that even if two users use the same master key, their encrypted data remains secure and distinct."