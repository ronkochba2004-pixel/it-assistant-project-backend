# db_models.py
from typing import Optional
from datetime import datetime, timezone

from sqlmodel import SQLModel, Field, Relationship


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
    images: list["MessageImageDB"] = Relationship(back_populates="message")

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
    national_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))



class MessageImageDB(SQLModel, table=True):
    __tablename__ = "message_images"

    id: int | None = Field(default=None, primary_key=True)
    message_id: int = Field(foreign_key="messages.message_id")
    url: str
    position: int  # 0..4
    message: MessageDB = Relationship(back_populates="images")
