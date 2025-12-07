# db_models.py
from typing import Optional
from datetime import datetime, timezone

from sqlmodel import SQLModel, Field


class ChatDB(SQLModel, table=True):
    __tablename__ = "chats"

    chat_id: Optional[int] = Field(default=None, primary_key=True)
    title: Optional[str] = None
    user_id: Optional[int] = Field(default=None, foreign_key="users.user_id")
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

class CompanyDB(SQLModel, table=True):
    __tablename__ = "companies"

    company_id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class UserDB(SQLModel, table=True):
    __tablename__ = "users"

    user_id: Optional[int] = Field(default=None, primary_key=True)
    company_id: int = Field(foreign_key="companies.company_id")
    email: str
    first_name: str
    last_name: str
    role: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))