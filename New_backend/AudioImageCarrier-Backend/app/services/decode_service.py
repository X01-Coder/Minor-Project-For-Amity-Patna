"""Decode service - Business logic for image to audio decoding."""

import tempfile
from pathlib import Path
from typing import Dict
import json

from app.core.audio_processor import AudioProcessor
from app.core.config import settings
from app.utils.file_handler import (
    extract_zip_archive,
    get_file_size,
    cleanup_directory,
    create_temp_directory
)
from app.utils.validators import validate_zip_file


class DecodeService:
    """Service for decoding encrypted images to audio files."""
    
    @staticmethod
    def decode_images_to_audio(
        images_zip_path: Path,
        user_id: str,
        master_key: str = None
    ) -> Dict:
        """
        Decode encrypted images to audio file.
        
        Args:
            images_zip_path: Path to ZIP containing images
            user_id: User ID used for encoding
            master_key: Optional master key
            
        Returns:
            Dictionary with decoding results
            
        Raises:
            ValueError: If validation fails
            RuntimeError: If decoding fails
        """
        # Validate ZIP file
        is_valid, error_msg = validate_zip_file(
            images_zip_path,
            max_size=settings.max_upload_size_bytes * 2  # Allow larger ZIPs
        )
        if not is_valid:
            raise ValueError(f"Invalid ZIP file: {error_msg}")
        
        # Create temporary directories
        extract_dir = create_temp_directory(prefix="extract_")
        output_dir = create_temp_directory(prefix="decode_")
        
        try:
            # Extract ZIP
            extracted_files = extract_zip_archive(images_zip_path, extract_dir)
            
            if not extracted_files:
                raise ValueError("ZIP archive is empty")
            
            # Try to get metadata from first image
            metadata = {}
            original_filename = "recovered_audio.wav"
            total_chunks = len([f for f in extracted_files if f.suffix.lower() in {'.png', '.tiff', '.tif'}])
            compressed = False
            
            try:
                from PIL import Image
                import numpy as np
                
                first_image = next((f for f in extracted_files if f.suffix.lower() in {'.png', '.tiff', '.tif'}), None)
                if first_image:
                    img = Image.open(first_image).convert("RGB")
                    arr = np.asarray(img, dtype=np.uint8)
                    flat = arr.reshape(-1, 3).astype(np.uint8).flatten().tobytes()
                    
                    if len(flat) >= 1024:
                        hdr_len = int.from_bytes(flat[0:4], "little")
                        if 0 < hdr_len <= 1024:
                            header_json = flat[4:4+hdr_len]
                            header = json.loads(header_json.decode('utf8'))
                            
                            original_filename = header.get("orig_filename", original_filename)
                            total_chunks = header.get("orig_total_chunks", total_chunks)
                            compressed = header.get("compressed", False)
                            
                            metadata = {
                                "version": header.get("version"),
                                "timestamp": header.get("ts"),
                                "magic": header.get("magic")
                            }
            except Exception:
                pass  # Use defaults if metadata extraction fails
            
            # Decode images to audio
            output_audio_path = output_dir / original_filename
            AudioProcessor.decode_images(
                input_dir=extract_dir,
                output_file=output_audio_path,
                user_id=user_id,
                master_hex=master_key
            )
            
            # Get recovered file size
            recovered_size = get_file_size(output_audio_path)
            
            return {
                "success": True,
                "user_id": user_id,
                "original_filename": original_filename,
                "recovered_size_bytes": recovered_size,
                "total_chunks_decoded": total_chunks,
                "compressed": compressed,
                "metadata": metadata,
                "output_path": output_audio_path,
                "temp_dir": output_dir,
                "extract_dir": extract_dir
            }
            
        except Exception as e:
            cleanup_directory(extract_dir)
            cleanup_directory(output_dir)
            raise RuntimeError(f"Decoding failed: {str(e)}") from e
