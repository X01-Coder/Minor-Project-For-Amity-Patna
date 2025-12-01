"""
Audio processor - Core logic wrapper for audio_image_chunked.py script.
Imports and calls functions directly for better performance and error handling.
"""

import sys
from pathlib import Path
from typing import List, Optional
import importlib.util

# Add scripts directory to Python path
SCRIPT_DIR = Path(__file__).parent.parent.parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

# Import the audio_image_chunked module directly
spec = importlib.util.spec_from_file_location(
    "audio_image_chunked",
    SCRIPT_DIR / "audio_image_chunked.py"
)
audio_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audio_module)


class AudioProcessor:
    """Wrapper class for audio-image conversion operations."""
    
    @staticmethod
    def encode_audio(
        input_file: Path,
        output_dir: Path,
        user_id: str,
        master_hex: Optional[str],
        max_chunk_bytes: int,
        compress: bool = True
    ) -> List[Path]:
        """
        Encode audio file to encrypted images.
        
        Args:
            input_file: Path to input audio file
            output_dir: Directory to save output images
            user_id: User ID for key derivation
            master_hex: Master encryption key (hex string)
            max_chunk_bytes: Maximum bytes per image chunk
            compress: Enable compression
            
        Returns:
            List of generated image file paths
            
        Raises:
            RuntimeError: If encoding fails
        """
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Call encode_streamed function directly
            generated_images = audio_module.encode_streamed(
                input_file=input_file,
                out_dir=output_dir,
                user_id=user_id,
                max_chunk_bytes=max_chunk_bytes,
                master_hex=master_hex,
                compress=compress
            )
            
            return generated_images
            
        except Exception as e:
            raise RuntimeError(f"Encoding failed: {str(e)}") from e
    
    @staticmethod
    def decode_images(
        input_dir: Path,
        output_file: Path,
        user_id: str,
        master_hex: Optional[str]
    ) -> Path:
        """
        Decode encrypted images to audio file.
        
        Args:
            input_dir: Directory containing input images
            output_file: Path to save recovered audio file
            user_id: User ID used for encoding
            master_hex: Master encryption key (hex string)
            
        Returns:
            Path to recovered audio file
            
        Raises:
            RuntimeError: If decoding fails
        """
        try:
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Call decode_images_to_file function directly
            audio_module.decode_images_to_file(
                indir=input_dir,
                out_file=output_file,
                user_id=user_id,
                master_hex=master_hex
            )
            
            return output_file
            
        except Exception as e:
            raise RuntimeError(f"Decoding failed: {str(e)}") from e
    
    @staticmethod
    def get_wav_duration(file_path: Path) -> Optional[float]:
        """
        Get duration of WAV file in seconds.
        
        Args:
            file_path: Path to WAV file
            
        Returns:
            Duration in seconds, or None if not a WAV or cannot determine
        """
        try:
            return audio_module.get_wav_duration_seconds(file_path)
        except Exception:
            return None