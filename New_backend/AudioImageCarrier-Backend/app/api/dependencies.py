"""Shared dependencies for API endpoints."""

from fastapi import Depends, Header, HTTPException, status
from app.core.security import verify_api_key


async def get_api_key(x_api_key: str = Header(..., alias="X-API-Key")) -> str:
    """
    Dependency to verify API key from X-API-Key header.
    
    Args:
        x_api_key: API key from request header
        
    Returns:
        Validated API key
        
    Raises:
        HTTPException: If API key is invalid
    """
    try:
        return await verify_api_key(x_api_key)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API key validation failed"
        )