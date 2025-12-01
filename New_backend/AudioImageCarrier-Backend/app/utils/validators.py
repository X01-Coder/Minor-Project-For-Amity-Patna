"""Input validation utilities for security and data integrity."""

from pathlib import Path
from typing import Optional, Tuple

# Allowed file extensions
ALLOWED_AUDIO_EXTENSIONS = {
    '.wav', '.mp3', '.flac', '.m4a', '.aac',
    '.ogg', '.opus', '.wma', '.aiff', '.ape'
}

ALLOWED_IMAGE_EXTENSIONS = {'.png', '.tiff', '.tif'}

# Security constants
MAX_FILENAME_LENGTH = 255
MAX_USER_ID_LENGTH = 100
DANGEROUS_CHARS = ['/', '\\', '..', '\x00', '<', '>', ':', '"', '|', '?', '*']


def validate_audio_file(file_path: Path, max_size: Optional[int] = None) -> Tuple[bool, Optional[str]]:
    """
    Validate audio file.
    
    Args:
        file_path: Path to audio file
        max_size: Maximum file size in bytes (optional)
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not file_path.exists():
        return False, "File does not exist"
    
    if not file_path.is_file():
        return False, "Path is not a file"
    
    if file_path.suffix.lower() not in ALLOWED_AUDIO_EXTENSIONS:
        return False, f"Invalid audio format. Allowed: {', '.join(ALLOWED_AUDIO_EXTENSIONS)}"
    
    file_size = file_path.stat().st_size
    
    if file_size == 0:
        return False, "File is empty"
    
    if max_size and file_size > max_size:
        return False, f"File too large: {file_size} bytes (max: {max_size})"
    
    if len(file_path.name) > MAX_FILENAME_LENGTH:
        return False, f"Filename too long (max {MAX_FILENAME_LENGTH} characters)"
    
    return True, None


def validate_zip_file(file_path: Path, max_size: Optional[int] = None) -> Tuple[bool, Optional[str]]:
    """
    Validate ZIP file.
    
    Args:
        file_path: Path to ZIP file
        max_size: Maximum file size in bytes (optional)
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not file_path.exists():
        return False, "File does not exist"
    
    if not file_path.is_file():
        return False, "Path is not a file"
    
    if file_path.suffix.lower() != '.zip':
        return False, "File must be a ZIP archive"
    
    file_size = file_path.stat().st_size
    
    if file_size == 0:
        return False, "File is empty"
    
    if max_size and file_size > max_size:
        return False, f"File too large: {file_size} bytes (max: {max_size})"
    
    return True, None


def validate_image_file(file_path: Path) -> Tuple[bool, Optional[str]]:
    """
    Validate image file.
    
    Args:
        file_path: Path to image file
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not file_path.exists():
        return False, "File does not exist"
    
    if not file_path.is_file():
        return False, "Path is not a file"
    
    if file_path.suffix.lower() not in ALLOWED_IMAGE_EXTENSIONS:
        return False, f"Invalid image format. Allowed: {', '.join(ALLOWED_IMAGE_EXTENSIONS)}"
    
    if file_path.stat().st_size == 0:
        return False, "File is empty"
    
    return True, None


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent path traversal and other attacks.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    # Remove dangerous characters
    sanitized = filename
    for char in DANGEROUS_CHARS:
        sanitized = sanitized.replace(char, '_')
    
    # Limit length
    if len(sanitized) > MAX_FILENAME_LENGTH:
        name, ext = (sanitized.rsplit('.', 1) if '.' in sanitized else (sanitized, ''))
        max_name_len = MAX_FILENAME_LENGTH - len(ext) - 1
        sanitized = f"{name[:max_name_len]}.{ext}" if ext else name[:MAX_FILENAME_LENGTH]
    
    return sanitized


def validate_user_id(user_id: str) -> Tuple[bool, Optional[str]]:
    """
    Validate user ID for security.
    
    Args:
        user_id: User identifier
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not user_id or not user_id.strip():
        return False, "user_id cannot be empty"
    
    if len(user_id) > MAX_USER_ID_LENGTH:
        return False, f"user_id too long (max {MAX_USER_ID_LENGTH} characters)"
    
    # Check for dangerous characters
    for char in DANGEROUS_CHARS:
        if char in user_id:
            return False, f"user_id contains forbidden character: '{char}'"
    
    # Check for control characters
    if any(ord(c) < 32 for c in user_id):
        return False, "user_id contains control characters"
    
    return True, None


def validate_master_key(master_key: str) -> Tuple[bool, Optional[str]]:
    """
    Validate master key format.
    
    Args:
        master_key: Hexadecimal master key
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not master_key:
        return False, "Master key cannot be empty"
    
    master_key = master_key.strip()
    
    if len(master_key) != 64:
        return False, f"Master key must be 64 hex characters (got {len(master_key)})"
    
    try:
        int(master_key, 16)
    except ValueError:
        return False, "Master key must be valid hexadecimal"
    
    return True, None
