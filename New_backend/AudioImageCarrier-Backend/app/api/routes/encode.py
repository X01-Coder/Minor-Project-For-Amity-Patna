"""Encode endpoint - Convert audio to encrypted images."""

import tempfile
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
import shutil

from app.api.dependencies import get_api_key
from app.services.encode_service import EncodeService
from app.utils.validators import sanitize_filename, validate_user_id, validate_master_key
from app.utils.file_handler import cleanup_directory, cleanup_file
from app.core.config import settings

router = APIRouter()


def cleanup_resources(temp_upload_path: Path = None, result_temp_dir: Path = None):
    """Background task to cleanup temporary files."""
    if temp_upload_path and temp_upload_path.exists():
        cleanup_file(temp_upload_path)
    if result_temp_dir and result_temp_dir.exists():
        cleanup_directory(result_temp_dir)


@router.post(
    "/encode",
    summary="Encode audio file to encrypted images",
    description="""
    Upload an audio file and receive a ZIP archive containing encrypted PNG images.
    
    **Security:** Each user should have a unique master_key. Using shared keys is insecure!
    
    **Parameters:**
    - **file**: Audio file (WAV, MP3, FLAC, M4A, etc.)
    - **user_id**: User identifier for encryption key derivation (e.g., "alice", "user123")
    - **master_key** (optional): 64-character hex master key (uses env var if not provided)
    - **max_chunk_bytes** (optional): Maximum bytes per image (default: 50MB)
    - **compress** (optional): Enable zstd compression (default: true)
    - **delete_source** (optional): Delete uploaded file after encoding (default: false)
    
    **Returns:** ZIP file containing encrypted PNG images
    
    **Example:**
    ```bash
    curl -X POST "http://localhost:8000/api/v1/encode" \\
      -H "X-API-Key: your-api-key" \\
      -F "file=@audio.wav" \\
      -F "user_id=alice" \\
      -F "compress=true" \\
      -o encrypted_images.zip
    ```
    """
)
async def encode_audio(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Audio file to encode"),
    user_id: str = Form(..., description="User ID for encryption"),
    master_key: str = Form(None, description="Master key (64 hex chars)"),
    max_chunk_bytes: int = Form(None, description="Max bytes per chunk"),
    compress: bool = Form(True, description="Enable compression"),
    delete_source: bool = Form(False, description="Delete source after encoding"),
    api_key: str = Depends(get_api_key)
):
    """Encode audio file to encrypted images."""
    
    temp_upload_path = None
    result_data = None
    
    try:
        # Validate inputs
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")
        
        # Validate user_id
        is_valid, error = validate_user_id(user_id)
        if not is_valid:
            raise HTTPException(status_code=400, detail=f"Invalid user_id: {error}")
        
        # Validate master_key if provided
        if master_key:
            is_valid, error = validate_master_key(master_key)
            if not is_valid:
                raise HTTPException(status_code=400, detail=f"Invalid master_key: {error}")
        
        # Sanitize filename
        safe_filename = sanitize_filename(file.filename)
        
        # Save uploaded file temporarily with unique name
        import uuid
        temp_name = f"upload_{uuid.uuid4().hex[:8]}_{safe_filename}"
        temp_upload_path = Path(settings.upload_dir) / temp_name
        temp_upload_path.parent.mkdir(parents=True, exist_ok=True)
        
        with temp_upload_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Encode audio to images
        result_data = EncodeService.encode_audio_to_images(
            audio_file_path=temp_upload_path,
            user_id=user_id,
            master_key=master_key,
            max_chunk_bytes=max_chunk_bytes,
            compress=compress,
            delete_source=delete_source
        )
        
        # Get ZIP file path
        zip_path = result_data["zip_path"]
        
        # Schedule cleanup after response is sent
        background_tasks.add_task(
            cleanup_resources,
            temp_upload_path if not delete_source else None,
            result_data["temp_dir"]
        )
        
        # Return ZIP file
        return FileResponse(
            path=zip_path,
            media_type="application/zip",
            filename=result_data["zip_filename"],
            headers={
                "X-Total-Images": str(result_data["total_images"]),
                "X-Original-Size": str(result_data["original_size_bytes"]),
                "X-Compressed": str(result_data["compressed"]),
                "X-User-ID": user_id
            }
        )
        
    except ValueError as e:
        # Cleanup on error
        if temp_upload_path:
            cleanup_file(temp_upload_path)
        if result_data and "temp_dir" in result_data:
            cleanup_directory(result_data["temp_dir"])
        raise HTTPException(status_code=400, detail=str(e))
    
    except Exception as e:
        # Cleanup on error
        if temp_upload_path:
            cleanup_file(temp_upload_path)
        if result_data and "temp_dir" in result_data:
            cleanup_directory(result_data["temp_dir"])
        raise HTTPException(status_code=500, detail=f"Encoding failed: {str(e)}")
