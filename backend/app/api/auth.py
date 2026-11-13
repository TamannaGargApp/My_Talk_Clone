from datetime import datetime, timedelta, timezone
import secrets
from urllib.parse import urlencode
from authlib.integrations.httpx_client import OAuth2Client
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from pymongo.errors import DuplicateKeyError
from app.config import get_settings
from app.database.mongodb import get_db
from app.models.schemas import LoginRequest, OAuthExchangeRequest, RegisterRequest
from app.utils.security import create_token, current_user_id, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


def public_user(user):
    return {"id": str(user["_id"]), "name": user["name"], "email": user["email"]}


@router.post("/register", status_code=201)
def register(payload: RegisterRequest):
    db = get_db()
    user = {"name": payload.name.strip(), "email": payload.email.lower(),
            "password_hash": hash_password(payload.password), "created_at": datetime.now(timezone.utc)}
    try:
        result = db.users.insert_one(user)
    except DuplicateKeyError:
        raise HTTPException(status_code=409, detail="Email already registered") from None
    user["_id"] = result.inserted_id
    return {"token": create_token(str(result.inserted_id)), "user": public_user(user)}


@router.post("/login")
def login(payload: LoginRequest):
    user = get_db().users.find_one({"email": payload.email.lower()})
    if not user or not user.get("password_hash") or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return {"token": create_token(str(user["_id"])), "user": public_user(user)}


@router.get("/me")
def me(user_id: str = Depends(current_user_id)):
    try:
        user = get_db().users.find_one({"_id": ObjectId(user_id)})
    except Exception:
        user = None
    if not user:
        raise HTTPException(status_code=401, detail="Account not found")
    return public_user(user)


@router.get("/google/start")
def google_start():
    cfg = get_settings()
    if not cfg.google_client_id or not cfg.google_client_secret:
        raise HTTPException(status_code=503, detail="Google sign-in not configured")
    state = secrets.token_urlsafe(32)
    get_db().oauth_codes.insert_one({"_id": f"state:{state}",
        "expires_at": datetime.now(timezone.utc) + timedelta(minutes=10)})
    params = {"client_id": cfg.google_client_id, "redirect_uri": cfg.google_redirect_uri,
              "response_type": "code", "scope": "openid email profile", "state": state,
              "prompt": "select_account"}
    return RedirectResponse("https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params))


@router.get("/google/callback")
async def google_callback(code: str = "", state: str = ""):
    cfg = get_settings()
    db = get_db()
    if not code or not state or not db.oauth_codes.find_one_and_delete({"_id": f"state:{state}"}):
        raise HTTPException(status_code=400, detail="Invalid OAuth state")
    async with OAuth2Client(client_id=cfg.google_client_id,
                            client_secret=cfg.google_client_secret) as client:
        token = await client.fetch_token(
            "https://oauth2.googleapis.com/token", code=code,
            redirect_uri=cfg.google_redirect_uri,
            grant_type="authorization_code",
        )
        response = await client.get("https://openidconnect.googleapis.com/v1/userinfo",
                                    token=token)
        response.raise_for_status()
        info = response.json()
    if not info.get("email_verified") or not info.get("sub"):
        raise HTTPException(status_code=401, detail="Google email not verified")
    email = info["email"].lower()
    user = db.users.find_one({"google_sub": info["sub"]})
    if not user:
        existing = db.users.find_one({"email": email})
        if existing:
            # Do not silently link an existing password account based only on matching email.
            raise HTTPException(status_code=409, detail="Account already exists. Sign in with password.")
        try:
            user_id = db.users.insert_one({"name": info.get("name", "Google user"),
                "email": email, "google_sub": info["sub"],
                "created_at": datetime.now(timezone.utc)}).inserted_id
        except DuplicateKeyError:
            raise HTTPException(status_code=409, detail="Email already registered") from None
    else:
        user_id = user["_id"]
    one_time_code = secrets.token_urlsafe(32)
    db.oauth_codes.insert_one({"_id": f"exchange:{one_time_code}", "user_id": str(user_id),
        "expires_at": datetime.now(timezone.utc) + timedelta(minutes=2)})
    return RedirectResponse(cfg.frontend_url.rstrip("/") + "/index.html#oauth=" + one_time_code)


@router.post("/google/exchange")
def google_exchange(payload: OAuthExchangeRequest):
    record = get_db().oauth_codes.find_one_and_delete({"_id": f"exchange:{payload.code}"})
    if not record or record["expires_at"].replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Google login code expired")
    user = get_db().users.find_one({"_id": ObjectId(record["user_id"])})
    if not user:
        raise HTTPException(status_code=401, detail="Account not found")
    return {"token": create_token(str(user["_id"])), "user": public_user(user)}
