"""File handling utilities for upload, storage, and cleanup operations."""

import os
import shutil
import zipfile
import tempfile
from pathlib import Path
from typing import List, Optional
from PIL import Image
import asyncio
from app.core.config import settings


def create_temp_directory(prefix: str = "aicarrier_") -> Path:
    """
    Create a temporary directory in the configured temp directory.
    
    Args:
        prefix: Prefix for temp directory name
        
    Returns:
        Path to created temporary directory
    """
    # Use configured temp directory instead of system temp
    import uuid
    temp_name = f"{prefix}{uuid.uuid4().hex[:12]}"
    temp_dir = Path(settings.temp_dir) / temp_name
    temp_dir.mkdir(parents=True, exist_ok=True)
    return temp_dir


def cleanup_directory(directory: Path, ignore_errors: bool = True) -> None:
    """
    Remove directory and all its contents.
    
    Args:
        directory: Path to directory to remove
        ignore_errors: Whether to ignore errors during deletion
    """
    try:
        if directory.exists() and directory.is_dir():
            shutil.rmtree(directory, ignore_errors=ignore_errors)
    except Exception as e:
        if not ignore_errors:
            raise


def cleanup_file(file_path: Path, ignore_errors: bool = True) -> None:
    """
    Remove a single file.
    
    Args:
        file_path: Path to file to remove
        ignore_errors: Whether to ignore errors during deletion
    """
    try:
        if file_path.exists() and file_path.is_file():
            file_path.unlink()
    except Exception as e:
        if not ignore_errors:
            raise


def ensure_directory(directory: Path) -> Path:
    """
    Ensure directory exists, create if not.
    
    Args:
        directory: Path to directory
        
    Returns:
        Path to directory
    """
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def get_file_size(file_path: Path) -> int:
    """
    Get file size in bytes.
    
    Args:
        file_path: Path to file
        
    Returns:
        File size in bytes, 0 if file doesn't exist
    """
    if file_path.exists() and file_path.is_file():
        return file_path.stat().st_size
    return 0


def get_image_dimensions(image_path: Path) -> tuple:
    """
    Get width and height of an image.
    
    Args:
        image_path: Path to image file
        
    Returns:
        Tuple of (width, height)
    """
    try:
        with Image.open(image_path) as img:
            return img.size
    except Exception:
        return (0, 0)


def create_zip_archive(files: List[Path], output_path: Path) -> Path:
    """
    Create a ZIP archive from list of files.
    
    Args:
        files: List of file paths to include in archive
        output_path: Path for output ZIP file
        
    Returns:
        Path to created ZIP file
        
    Raises:
        ValueError: If files list is empty or files don't exist
    """
    if not files:
        raise ValueError("No files provided for ZIP archive")
    
    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_path in files:
            if file_path.exists() and file_path.is_file():
                # Store with just filename (no directory structure)
                zipf.write(file_path, file_path.name)
    
    return output_path


def extract_zip_archive(zip_path: Path, output_dir: Path) -> List[Path]:
    """
    Extract ZIP archive to directory.
    
    Args:
        zip_path: Path to ZIP file
        output_dir: Directory to extract to
        
    Returns:
        List of extracted file paths
        
    Raises:
        ValueError: If ZIP file doesn't exist or is invalid
    """
    if not zip_path.exists():
        raise ValueError(f"ZIP file not found: {zip_path}")
    
    if not zipfile.is_zipfile(zip_path):
        raise ValueError(f"Invalid ZIP file: {zip_path}")
    
    output_dir.mkdir(parents=True, exist_ok=True)
    extracted_files = []
    
    with zipfile.ZipFile(zip_path, 'r') as zipf:
        # Security check: prevent path traversal
        for member in zipf.namelist():
            if ".." in member or member.startswith("/"):
                raise ValueError(f"Unsafe file path in ZIP: {member}")
        
        zipf.extractall(output_dir)
        
        for name in zipf.namelist():
            extracted_files.append(output_dir / name)
    
    return extracted_files


async def save_upload_file(upload_file, destination: Path) -> Path:
    """
    Save uploaded file to destination (async).
    
    Args:
        upload_file: FastAPI UploadFile object
        destination: Destination path
        
    Returns:
        Path to saved file
    """
    destination.parent.mkdir(parents=True, exist_ok=True)
    
    with destination.open("wb") as f:
        content = await upload_file.read()
        f.write(content)
    
    return destination


def count_files_in_directory(directory: Path, pattern: str = "*") -> int:
    """
    Count files matching pattern in directory.
    
    Args:
        directory: Path to directory
        pattern: Glob pattern (default: all files)
        
    Returns:
        Number of matching files
    """
    if not directory.exists():
        return 0
    
    return len(list(directory.glob(pattern)))
