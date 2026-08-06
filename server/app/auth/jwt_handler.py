import os
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from jose import JWTError, jwt

load_dotenv(verbose=True)

secret_key = os.getenv("JWT_SECRET")
hashing_algorithm = os.getenv("JWT_ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "43200"))


def create_access_token(data: dict) -> str:
    """Generate a JWT token with an expiration time."""
    to_encode = data.copy()
    expire_minutes = int(os.getenv("JWT_EXPIRE_MINUTES", "43200"))
    expire = datetime.now(timezone.utc) + timedelta(minutes=expire_minutes)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=hashing_algorithm)
    return encoded_jwt


def decode_jwt_token(token: str) -> str | None:
    """Decode a JWT token and return the subject (email/username)."""
    try:
        decoded_token = jwt.decode(token, secret_key, algorithms=[hashing_algorithm])
        email: str = decoded_token.get("sub")
        return email
    except JWTError:
        return None
