"""
POST /chat — the shopping-assistant endpoint.

All the orchestration (input guards -> agent -> output guard -> response shaping)
lives in backend/chatbot/pipeline.py, so the exact same pipeline backs the
standalone chatbot POC. This module is only the HTTP layer.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import asyncio
from ..config import settings, is_placeholder

class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)

# Split so the read replica / write replica of the deployment can each mount only
# the half it serves. The monolith (main.py) mounts both. The chatbot only reads
# from MongoDB, so it lives on the read side; write_router stays empty.
read_router = APIRouter(prefix="/chat", tags=["Chatbot"])
write_router = APIRouter(prefix="/chat", tags=["Chatbot"])


@read_router.post("")
async def chat_bot(data: ChatRequest):
    """
    Accept ``{"message": "..."}`` and return either a plain-text reply or a list
    of matching products: ``{"type": "text" | "products", "message", "data"}``.
    """
    if is_placeholder(settings.groq_api_key) and is_placeholder(settings.portkey_api_key):
        raise HTTPException(503, "Shopping assistant is not configured; please browse the catalog")
    from ..chatbot.pipeline import run_chat
    try:
        return await asyncio.wait_for(run_chat(data.message), timeout=30)
    except asyncio.TimeoutError:
        raise HTTPException(504, "Shopping assistant timed out; please try again")
