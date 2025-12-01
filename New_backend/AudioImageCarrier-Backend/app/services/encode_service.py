"""Encode service - Business logic for audio to image encoding."""

import tempfile
from pathlib import Path
from typing import Dict

from app.core.audio_processor import AudioProcessor
from app.core.config import settings
from app.utils.file_handler import (
    create_zip_archive,
    get_image_dimensions,
    get_file_size,
    cleanup_directory,
    create_temp_directory
)
from app.utils.validators import validate_audio_file


class EncodeService:
    """Service for encoding audio files to encrypted images."""
    
    @staticmethod
    def encode_audio_to_images(
        audio_file_path: Path,
        user_id: str,
        master_key: str = None,
        max_chunk_bytes: int = None,
        compress: bool = True,
        delete_source: bool = False
    ) -> Dict:
        """
        Encode audio file to encrypted images.
        
        Args:
            audio_file_path: Path to audio file
            user_id: User ID for encryption
            master_key: Optional master key
            max_chunk_bytes: Max bytes per chunk
            compress: Enable compression
            delete_source: Delete source after encoding
            
        Returns:
            Dictionary with encoding results
            
        Raises:
            ValueError: If validation fails
            RuntimeError: If encoding fails
        """
        # Validate audio file
        is_valid, error_msg = validate_audio_file(
            audio_file_path,
            max_size=settings.max_upload_size_bytes
        )
        if not is_valid:
            raise ValueError(f"Invalid audio file: {error_msg}")
        
        # Set defaults
        if max_chunk_bytes is None:
            max_chunk_bytes = settings.default_max_chunk_bytes
        
        # Create temporary directory for images
        temp_dir = create_temp_directory(prefix="encode_")
        
        try:
            # Get original file info
            original_size = get_file_size(audio_file_path)
            original_filename = audio_file_path.name
            
            # Check if WAV and get duration
            duration = None
            if audio_file_path.suffix.lower() == '.wav':
                duration = AudioProcessor.get_wav_duration(audio_file_path)
            
            # Encode to images
            image_paths = AudioProcessor.encode_audio(
                input_file=audio_file_path,
                output_dir=temp_dir,
                user_id=user_id,
                master_hex=master_key,
                max_chunk_bytes=max_chunk_bytes,
                compress=compress
            )
            
            # Collect image information
            images_info = []
            for idx, img_path in enumerate(image_paths):
                width, height = get_image_dimensions(img_path)
                size = get_file_size(img_path)
                
                images_info.append({
                    "filename": img_path.name,
                    "size_bytes": size,
                    "width": width,
                    "height": height,
                    "chunk_index": idx,
                    "total_chunks": len(image_paths)
                })
            
            # Create ZIP archive
            zip_filename = f"{audio_file_path.stem}_images.zip"
            zip_path = temp_dir / zip_filename
            create_zip_archive(image_paths, zip_path)
            zip_size = get_file_size(zip_path)
            
            # Prepare metadata
            metadata = {
                "audio_format": audio_file_path.suffix.lower(),
                "total_chunks": len(image_paths),
            }
            if duration is not None:
                metadata["duration_seconds"] = round(duration, 2)
            
            # Delete source if requested
            if delete_source:
                try:
                    audio_file_path.unlink()
                    metadata["source_deleted"] = True
                except Exception as e:
                    metadata["source_delete_error"] = str(e)
            
            return {
                "success": True,
                "user_id": user_id,
                "original_filename": original_filename,
                "original_size_bytes": original_size,
                "total_images": len(image_paths),
                "images": images_info,
                "zip_filename": zip_filename,
                "zip_path": zip_path,
                "zip_size_bytes": zip_size,
                "master_key_used": "provided" if master_key else "environment",
                "compressed": compress,
                "metadata": metadata,
                "temp_dir": temp_dir
            }
            
        except Exception as e:
            cleanup_directory(temp_dir)
            raise RuntimeError(f"Encoding failed: {str(e)}") from e
