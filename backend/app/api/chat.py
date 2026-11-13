from datetime import datetime, timezone
import logging
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException
from pymongo import DESCENDING
from app.database.mongodb import get_db
from app.models.schemas import ChatRequest
from app.services.gemini_service import generate_reply
from app.utils.security import bearer, current_user_id

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/chat", tags=["chat"])


def optional_user(credentials=Depends(bearer)):
    if credentials is None:
        return None
    return current_user_id(credentials)


@router.post("")
def chat(payload: ChatRequest, user_id: str | None = Depends(optional_user)):
    db = get_db()
    session_id = payload.session_id or str(uuid4())
    history = []
    if user_id:
        docs = list(db.conversations.find({"user_id": user_id, "session_id": session_id})
                    .sort("created_at", DESCENDING).limit(12))
        history = [{"role": d["role"], "content": d["content"]} for d in reversed(docs)]
    try:
        answer = generate_reply(payload.message, history)
    except Exception:
        logger.exception("Gemini request failed")
        raise HTTPException(status_code=502, detail="AI service unavailable. Try again shortly.") from None
    if user_id:
        now = datetime.now(timezone.utc)
        db.conversations.insert_many([
            {"user_id": user_id, "session_id": session_id, "role": "user",
             "content": payload.message, "created_at": now},
            {"user_id": user_id, "session_id": session_id, "role": "assistant",
             "content": answer, "created_at": datetime.now(timezone.utc)},
        ])
    return {"reply": answer, "session_id": session_id, "saved": bool(user_id)}


@router.get("/history")
def history(user_id: str = Depends(current_user_id)):
    docs = get_db().conversations.find({"user_id": user_id}).sort("created_at", DESCENDING).limit(100)
    return [{"session_id": d["session_id"], "role": d["role"], "content": d["content"],
             "created_at": d["created_at"].isoformat()} for d in docs]
