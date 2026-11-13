from datetime import datetime, timezone
import logging
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException
from pymongo import ASCENDING, DESCENDING
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
        db.conversations.insert_many([
            {"user_id": user_id, "session_id": session_id, "role": "user",
             "content": payload.message, "created_at": datetime.now(timezone.utc)},
            {"user_id": user_id, "session_id": session_id, "role": "assistant",
             "content": answer, "created_at": datetime.now(timezone.utc)},
        ])
    return {"reply": answer, "session_id": session_id, "saved": bool(user_id)}


@router.get("/history")
def history(user_id: str = Depends(current_user_id)):
    docs = get_db().conversations.find({"user_id": user_id}).sort("created_at", DESCENDING).limit(100)
    return [{"session_id": d["session_id"], "role": d["role"], "content": d["content"],
             "created_at": d["created_at"].isoformat()} for d in docs]


@router.get("/sessions")
def list_sessions(user_id: str = Depends(current_user_id)):
    pipeline = [
        {"$match": {"user_id": user_id}},
        {"$sort": {"created_at": ASCENDING, "_id": ASCENDING}},
        {"$group": {
            "_id": "$session_id",
            "first_user_message": {"$first": {"$cond": [{"$eq": ["$role", "user"]}, "$content", None]}},
            "last_at": {"$max": "$created_at"},
            "message_count": {"$sum": 1},
        }},
        {"$sort": {"last_at": DESCENDING}},
        {"$limit": 100},
    ]
    # A session normally begins with a user message. Fall back to a generic title for older records.
    return [{"session_id": d["_id"],
             "title": (d.get("first_user_message") or "Conversation")[:75],
             "updated_at": d["last_at"].isoformat(),
             "message_count": d["message_count"]}
            for d in get_db().conversations.aggregate(pipeline)]


# @router.get("/sessions/{session_id}")
# def get_session(session_id: str, user_id: str = Depends(current_user_id)):
#     db = get_db()
#     query = {"user_id": user_id, "session_id": session_id}
#     docs = list(db.conversations.find(query).sort("created_at", DESCENDING).limit(200))
#     if not docs:
#         raise HTTPException(status_code=404, detail="Conversation not found")
#     docs.reverse()
#     return [{"role": d["role"], "content": d["content"],
#              "created_at": d["created_at"].isoformat()} for d in docs]

@router.get("/sessions/{session_id}")
def get_conversation(
    session_id: str,
    user_id: str = Depends(current_user_id)
):
    db = get_db()

    docs = list(
        db.conversations.find({
            "user_id": user_id,
            "session_id": session_id
        }).sort([
            ("created_at", 1),
            ("_id", 1)
        ])
    )

    if not docs:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found"
        )

    return [
        {
            "session_id": doc["session_id"],
            "role": doc["role"],
            "content": doc["content"],
            "created_at": doc["created_at"].isoformat()
        }
        for doc in docs
    ]


@router.delete("/sessions/{session_id}")
def delete_session(session_id: str, user_id: str = Depends(current_user_id)):
    result = get_db().conversations.delete_many({"user_id": user_id, "session_id": session_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"deleted": True}
