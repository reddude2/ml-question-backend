"""
Authentication Middleware
Global JWT verification for all requests
"""

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from jose import jwt, JWTError
from core.security import verify_token
import re

# ============================================================================
# PUBLIC PATHS CONFIGURATION
# ============================================================================

# Public endpoints that DON'T need authentication
PUBLIC_PATHS = {
    "/",
    "/health",
    "/api/info",
    "/api/tiers",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/auth/login",
    "/auth/register",
    "/favicon.ico",
    "/materials",
    "/materials/stats/overview",
}

# Regex patterns for public paths
PUBLIC_PATTERNS = [
    r"^/docs.*",
    r"^/redoc.*",
    r"^/openapi\.json.*",
    r"^/materials.*",  # All materials endpoints public
]

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def is_public_path(path: str) -> bool:
    """
    Check if path is public (doesn't require authentication)
    
    Args:
        path: Request URL path
        
    Returns:
        True if path is public, False otherwise
    """
    # Exact match
    if path in PUBLIC_PATHS:
        return True
    
    # Pattern match
    for pattern in PUBLIC_PATTERNS:
        if re.match(pattern, path):
            return True
    
    return False

# ============================================================================
# MIDDLEWARE
# ============================================================================

async def verify_jwt_middleware(request: Request, call_next):
    """
    Global JWT verification middleware
    
    Features:
    - Checks ALL requests for valid JWT token
    - Allows public paths (login, docs, health, materials, etc.)
    - Allows OPTIONS requests (CORS preflight) - RETURNS DIRECTLY!
    - Attaches user_id and role to request.state for use in endpoints
    - Returns proper JSON error responses
    
    Args:
        request: FastAPI Request object
        call_next: Next middleware/endpoint in chain
        
    Returns:
        Response from next middleware/endpoint or error response
    """
    
    path = request.url.path
    method = request.method
    
    # ========================================
    # EXEMPTION 1: CORS Preflight (OPTIONS)
    # ========================================
    # CRITICAL FIX: Return response IMMEDIATELY for OPTIONS
    # DO NOT call call_next(request) - handle it entirely here
    if method == "OPTIONS":
        return JSONResponse(
            status_code=200,
            content={"status": "ok", "method": "OPTIONS"},
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, PATCH, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization, Accept, Origin, User-Agent, X-Requested-With",
                "Access-Control-Max-Age": "3600",
                "Access-Control-Allow-Credentials": "true",
            }
        )
    
    # ========================================
    # EXEMPTION 2: Public paths
    # ========================================
    # Allow public paths (no authentication required)
    if is_public_path(path):
        response = await call_next(request)
        return response
    
    # ========================================
    # PROTECTED ROUTES: Require JWT
    # ========================================
    # All other paths require authentication
    auth_header = request.headers.get("Authorization")
    
    # Check if Authorization header exists
    if not auth_header:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "status": "error",
                "message": "Missing authorization header",
                "detail": "Token tidak ditemukan. Silakan login terlebih dahulu.",
                "path": path
            },
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Check Authorization header format
    if not auth_header.startswith("Bearer "):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "status": "error",
                "message": "Invalid authorization header format",
                "detail": "Gunakan format: Bearer <token>",
                "path": path
            },
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Extract token
    try:
        token = auth_header.split(" ")[1]
    except IndexError:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "status": "error",
                "message": "Invalid authorization header",
                "detail": "Token tidak valid",
                "path": path
            },
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Verify token
    try:
        payload = verify_token(token)
        user_id = payload.get("sub")
        role = payload.get("role", "user")
        tier = payload.get("tier", "free")
        
        if not user_id:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "status": "error",
                    "message": "Invalid token payload",
                    "detail": "Token tidak memiliki user ID",
                    "path": path
                },
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # Attach user info to request state
        # Endpoints can access via: request.state.user_id, request.state.role, request.state.tier
        request.state.user_id = user_id
        request.state.role = role
        request.state.tier = tier
        
    except JWTError as e:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "status": "error",
                "message": "Invalid or expired token",
                "detail": f"Token error: {str(e)}",
                "path": path
            },
            headers={"WWW-Authenticate": "Bearer"}
        )
    except HTTPException as e:
        return JSONResponse(
            status_code=e.status_code,
            content={
                "status": "error",
                "message": "Authentication failed",
                "detail": e.detail,
                "path": path
            },
            headers={"WWW-Authenticate": "Bearer"}
        )
    except Exception as e:
        # Catch any unexpected errors
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": "error",
                "message": "Authentication error",
                "detail": f"Unexpected error: {str(e)}",
                "path": path
            }
        )
    
    # Continue to endpoint
    try:
        response = await call_next(request)
        return response
    except Exception as e:
        # Catch errors from downstream
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": "error",
                "message": "Internal server error",
                "detail": str(e),
                "path": path
            }
        )