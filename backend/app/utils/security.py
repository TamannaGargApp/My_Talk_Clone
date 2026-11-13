from datetime import datetime, timedelta, timezone
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pwdlib import PasswordHash
from app.config import get_settings

password_hash = PasswordHash.recommended()
bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return password_hash.verify(password, hashed)


def create_token(user_id: str) -> str:
    cfg = get_settings()
    if len(cfg.jwt_secret) < 32:
        raise RuntimeError("JWT_SECRET must be at least 32 characters")
    expiry = datetime.now(timezone.utc) + timedelta(minutes=cfg.jwt_expire_minutes)
    return jwt.encode({"sub": user_id, "exp": expiry}, cfg.jwt_secret, algorithm="HS256")


def current_user_id(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> str:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Sign in required")
    try:
        return jwt.decode(credentials.credentials, get_settings().jwt_secret, algorithms=["HS256"])["sub"]
    except (jwt.PyJWTError, KeyError):
        raise HTTPException(status_code=401, detail="Invalid or expired session") from None
