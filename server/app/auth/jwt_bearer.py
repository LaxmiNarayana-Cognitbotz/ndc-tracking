from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt as jose_jwt

from app.auth.jwt_handler import decode_jwt_token, hashing_algorithm, secret_key


class JWTBearer(HTTPBearer):
    def __init__(self, auto_error: bool = True):
        super(JWTBearer, self).__init__(auto_error=auto_error)

    async def __call__(self, request: Request):
        try:
            credentials: HTTPAuthorizationCredentials = await super(JWTBearer, self).__call__(request)
        except HTTPException as e:
            if not self.auto_error:
                return None
            raise e

        if credentials:
            if not credentials.scheme == "Bearer":
                raise HTTPException(status_code=403, detail="Invalid authentication scheme.")
            if not self.verify_jwt(credentials.credentials):
                raise HTTPException(status_code=403, detail="Invalid token or expired token.")
            return credentials.credentials
        else:
            raise HTTPException(status_code=403, detail="Invalid authorization credentials.")

    # verify the jwt token
    def verify_jwt(self, jwt_token: str) -> bool:
        try:
            payload = decode_jwt_token(jwt_token)
            return payload is not None
        except Exception:
            return False


jwt_scheme = JWTBearer()


def get_current_user(token: str = Depends(jwt_scheme)) -> dict:
    """Validate JWT and return payload. Raises 403 if invalid."""
    email = decode_jwt_token(token)
    if not email:
        raise HTTPException(status_code=403, detail="Invalid token or expired token.")
        
    try:
        payload = jose_jwt.decode(token, secret_key, algorithms=[hashing_algorithm])
        return payload
    except Exception:
        return {"sub": email, "role": "admin"}
