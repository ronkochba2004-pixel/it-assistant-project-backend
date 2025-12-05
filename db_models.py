# db_models.py
from typing import Optional
from datetime import datetime, timezone

from sqlmodel import SQLModel, Field


class ChatDB(SQLModel, table=True):
    __tablename__ = "chats"

    chat_id: Optional[int] = Field(default=None, primary_key=True)
    title: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_activity_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class MessageDB(SQLModel, table=True):
    __tablename__ = "messages"

    message_id: Optional[int] = Field(default=None, primary_key=True)
    chat_id: int = Field(foreign_key="chats.chat_id")
    sender: str
    text: str
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

