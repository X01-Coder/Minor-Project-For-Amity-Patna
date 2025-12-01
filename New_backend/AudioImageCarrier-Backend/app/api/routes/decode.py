"""Decode endpoint - Convert encrypted images back to audio."""

import tempfile
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
import shutil

from app.api.dependencies import get_api_key
from app.services.decode_service import DecodeService
from app.utils.validators import sanitize_filename, validate_user_id, validate_master_key
from app.utils.file_handler import cleanup_directory, cleanup_file
from app.core.config import settings

router = APIRouter()


def cleanup_resources(temp_zip_path: Path = None, extract_dir: Path = None, temp_dir: Path = None):
    """Background task to cleanup temporary files."""
    if temp_zip_path and temp_zip_path.exists():
        cleanup_file(temp_zip_path)
    if extract_dir and extract_dir.exists():
        cleanup_directory(extract_dir)
    if temp_dir and temp_dir.exists():
        cleanup_directory(temp_dir)


@router.post(
    "/decode",
    summary="Decode encrypted images to audio file",
    description="""
    Upload a ZIP archive containing encrypted PNG images and receive the recovered audio file.
    
    **Security:** You MUST use the same user_id and master_key that were used during encoding!
    
    **Parameters:**
    - **images**: ZIP file containing encrypted PNG images (from encode endpoint)
    - **user_id**: User identifier used during encoding (must match!)
    - **master_key** (optional): 64-character hex master key (uses env var if not provided)
    
    **Returns:** Recovered audio file
    
    **Example:**
    ```bash
    curl -X POST "http://localhost:8000/api/v1/decode" \\
      -H "X-API-Key: your-api-key" \\
      -F "images=@encrypted_images.zip" \\
      -F "user_id=alice" \\
      -o recovered_audio.wav
    ```
    """
)
async def decode_images(
    background_tasks: BackgroundTasks,
    images: UploadFile = File(..., description="ZIP file containing encrypted images"),
    user_id: str = Form(..., description="User ID used for encoding"),
    master_key: str = Form(None, description="Master key (64 hex chars)"),
    api_key: str = Depends(get_api_key)
):
    """Decode encrypted images to audio file."""
    
    temp_zip_path = None
    result_data = None
    
    try:
        # Validate inputs
        if not images.filename:
            raise HTTPException(status_code=400, detail="No filename provided")
        
        if not images.filename.endswith('.zip'):
            raise HTTPException(status_code=400, detail="File must be a ZIP archive")
        
        # Validate user_id
        is_valid, error = validate_user_id(user_id)
        if not is_valid:
            raise HTTPException(status_code=400, detail=f"Invalid user_id: {error}")
        
        # Validate master_key if provided
        if master_key:
            is_valid, error = validate_master_key(master_key)
            if not is_valid:
                raise HTTPException(status_code=400, detail=f"Invalid master_key: {error}")
        
        # Save uploaded ZIP temporarily
        safe_filename = sanitize_filename(images.filename)
        import uuid
        temp_name = f"upload_{uuid.uuid4().hex[:8]}_{safe_filename}"
        temp_zip_path = Path(settings.upload_dir) / temp_name
        temp_zip_path.parent.mkdir(parents=True, exist_ok=True)
        
        with temp_zip_path.open("wb") as buffer:
            shutil.copyfileobj(images.file, buffer)
        
        # Decode images to audio
        result_data = DecodeService.decode_images_to_audio(
            images_zip_path=temp_zip_path,
            user_id=user_id,
            master_key=master_key
        )
        
        # Get output audio path
        output_path = result_data["output_path"]
        
        # Schedule cleanup after response is sent
        background_tasks.add_task(
            cleanup_resources,
            temp_zip_path,
            result_data.get("extract_dir"),
            result_data.get("temp_dir")
        )
        
        # Return audio file
        return FileResponse(
            path=output_path,
            media_type="audio/wav",
            filename=result_data["original_filename"],
            headers={
                "X-Total-Chunks": str(result_data["total_chunks_decoded"]),
                "X-File-Size": str(result_data["recovered_size_bytes"]),
                "X-Compressed": str(result_data["compressed"]),
                "X-User-ID": user_id
            }
        )
        
    except ValueError as e:
        # Cleanup on error
        if temp_zip_path:
            cleanup_file(temp_zip_path)
        if result_data:
            if "extract_dir" in result_data:
                cleanup_directory(result_data["extract_dir"])
            if "temp_dir" in result_data:
                cleanup_directory(result_data["temp_dir"])
        raise HTTPException(status_code=400, detail=str(e))
    
    except Exception as e:
        # Cleanup on error
        if temp_zip_path:
            cleanup_file(temp_zip_path)
        if result_data:
            if "extract_dir" in result_data:
                cleanup_directory(result_data["extract_dir"])
            if "temp_dir" in result_data:
                cleanup_directory(result_data["temp_dir"])
        raise HTTPException(status_code=500, detail=f"Decoding failed: {str(e)}")
