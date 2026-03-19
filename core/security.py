"""
Security Module
Password hashing and JWT token management
"""

import bcrypt
from datetime import datetime, timezone, timedelta
from jose import JWTError, jwt
import os

SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 7

# ============================================================================
# PASSWORD HASHING
# ============================================================================

def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt
    
    Args:
        password: Plain text password
    
    Returns:
        str: Hashed password
    """
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')

def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt (alias for hash_password)
    
    This is an alias for hash_password() to maintain compatibility
    with different parts of the codebase.
    
    Args:
        password: Plain text password
    
    Returns:
        str: Hashed password
    """
    return hash_password(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash
    
    Args:
        plain_password: Plain text password to verify
        hashed_password: Hashed password from database
    
    Returns:
        bool: True if password matches, False otherwise
    """
    try:
        password_bytes = plain_password.encode('utf-8')
        hashed_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception as e:
        print(f"❌ Password verification error: {e}")
        return False

# ============================================================================
# JWT TOKEN MANAGEMENT
# ============================================================================

def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    """
    Create JWT access token
    
    Args:
        data: Data to encode in token (usually {"sub": user_id})
        expires_delta: Optional custom expiration time
    
    Returns:
        str: Encoded JWT token
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    
    to_encode.update({"exp": expire})
    
    try:
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    except Exception as e:
        print(f"❌ Token creation error: {e}")
        raise

def verify_token(token: str) -> dict:
    """
    Verify and decode JWT token
    
    Args:
        token: JWT token string
    
    Returns:
        dict: Decoded token payload
    
    Raises:
        JWTError: If token is invalid or expired
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        print(f"❌ Token verification error: {e}")
        raise

def decode_token(token: str) -> dict:
    """
    Decode JWT token without verification (for debugging)
    
    Args:
        token: JWT token string
    
    Returns:
        dict: Decoded token payload
    
    Note:
        This does NOT verify the token signature.
        Use only for debugging purposes.
    """
    try:
        payload = jwt.decode(
            token, 
            SECRET_KEY, 
            algorithms=[ALGORITHM],
            options={"verify_signature": False}
        )
        return payload
    except Exception as e:
        print(f"❌ Token decode error: {e}")
        return None

# ============================================================================
# PASSWORD GENERATION
# ============================================================================

def generate_password(length: int = 12) -> str:
    """
    Generate random secure password
    
    Args:
        length: Length of password (default: 12)
    
    Returns:
        str: Randomly generated password
    """
    import secrets
    import string
    
    # Include letters, digits, and some special characters
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    
    # Ensure password has at least one of each type
    password = [
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.digits),
        secrets.choice("!@#$%^&*")
    ]
    
    # Fill the rest randomly
    password += [secrets.choice(alphabet) for i in range(length - 4)]
    
    # Shuffle to avoid predictable patterns
    secrets.SystemRandom().shuffle(password)
    
    return ''.join(password)

# ============================================================================
# TOKEN UTILITIES
# ============================================================================

def get_token_expiry(token: str) -> datetime:
    """
    Get expiration time from token
    
    Args:
        token: JWT token string
    
    Returns:
        datetime: Token expiration time (UTC)
    """
    try:
        payload = decode_token(token)
        if payload and 'exp' in payload:
            return datetime.fromtimestamp(payload['exp'], tz=timezone.utc)
        return None
    except Exception:
        return None

def is_token_expired(token: str) -> bool:
    """
    Check if token is expired
    
    Args:
        token: JWT token string
    
    Returns:
        bool: True if expired, False otherwise
    """
    try:
        expiry = get_token_expiry(token)
        if expiry:
            return datetime.now(timezone.utc) > expiry
        return True
    except Exception:
        return True