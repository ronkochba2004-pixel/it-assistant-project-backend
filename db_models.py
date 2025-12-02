# db_models.py
from typing import Optional
from datetime import datetime

from sqlmodel import SQLModel, Field


class Chat(SQLModel, table=True):
    __tablename__ = "chats"  

    chat_id: Optional[int] = Field(default=None, primary_key=True)
    title: Optional[str] = None
    created_at: Optional[datetime] = None 


class Message(SQLModel, table=True):
    __tablename__ = "messages"  

    message_id: Optional[int] = Field(default=None, primary_key=True)
    chat_id: int = Field(foreign_key="chats.chat_id")
    sender: str
    text: str
    timestamp: int 
