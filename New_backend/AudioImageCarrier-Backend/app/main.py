"""Main FastAPI application."""

from datetime import datetime
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pathlib import Path

from app.core.config import settings
from app.api.routes import encode, decode

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="""
    🎵 **AudioImageCarrier API** - Secure Audio Steganography
    
    Convert audio files to encrypted PNG images and back. Perfect for secure audio storage and transmission.
    
    ## Features
    - 🔐 AES-256-GCM encryption with user-specific keys
    - 📦 Automatic chunking for large files
    - 🗜️ Optional zstd compression
    - 🎨 Steganography via PNG images
    - 🔑 Master key + user ID authentication
    
    ## Authentication
    All endpoints require an API key in the `X-API-Key` header.
    
    ## User ID Explanation
    The `user_id` parameter (e.g., "alice") is used for:
    - **Key Derivation**: Generate unique encryption keys per user
    - **Security**: Different users cannot decrypt each other's files
    - **Access Control**: Must use same user_id for encode and decode
    
    Example: If you encode with `user_id="alice"`, you must decode with `user_id="alice"`.
    
    ## Security Warning
    ⚠️ Each user MUST have a unique `master_key` in production! Shared keys allow users to decrypt each other's files.
    """,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create storage directories on startup
@app.on_event("startup")
async def startup_event():
    """Create required directories on application startup."""
    try:
        upload_path = Path(settings.upload_dir)
        temp_path = Path(settings.temp_dir)
        
        upload_path.mkdir(parents=True, exist_ok=True)
        temp_path.mkdir(parents=True, exist_ok=True)
        
        print(f"✅ {settings.app_name} v{settings.app_version} started")
        print(f"📁 Upload directory: {settings.upload_dir}")
        print(f"📁 Temp directory: {settings.temp_dir}")
    except Exception as e:
        print(f"⚠️ Warning: Could not create directories: {e}")
        # Continue anyway - directories might already exist or be read-only

# Include routers
app.include_router(encode.router, prefix="/api/v1", tags=["Encode"])
app.include_router(decode.router, prefix="/api/v1", tags=["Decode"])


@app.get("/", tags=["Health"])
async def root():
    """Root endpoint - API information."""
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "docs": "/docs",
        "endpoints": {
            "encode": "/api/v1/encode",
            "decode": "/api/v1/decode"
        }
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": settings.app_version,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unexpected errors."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": "InternalServerError",
            "message": str(exc),
            "timestamp": datetime.utcnow().isoformat()
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )