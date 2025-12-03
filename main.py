from datetime import time
from fastapi import FastAPI, HTTPException, Depends
from sqlmodel import Session, select

from models import MessageInput, Chat, Message, ChatSummary, CreateChatInput
from db import get_session
from db_models import ChatDB, MessageDB

app = FastAPI()


@app.get("/")
def root():
    return {"message": "Backend is working!"}


@app.post("/create_chat", response_model=ChatSummary)
def create_chat(data: CreateChatInput, session: Session = Depends(get_session)):
    """Create a new chat row in the database and return its summary."""
    chat = ChatDB(title=data.title)
    session.add(chat)
    session.commit()
    session.refresh(chat)  # reload from DB so chat_id and created_at are set

    return ChatSummary(chat_id=chat.chat_id, title=chat.title)


@app.post("/send_message", response_model=Message)
def send_message(
    data: MessageInput,
    session: Session = Depends(get_session),
):
    # Make sure the chat exists
    chat = session.get(ChatDB, data.chat_id)
    if chat is None:
        raise HTTPException(status_code=404, detail="Chat not found")

    # timestamp generated automatically by default_factory in MessageDB
    message_db = MessageDB(
        chat_id=data.chat_id,
        sender=data.sender,
        text=data.text,
    )

    session.add(message_db)
    session.commit()
    session.refresh(message_db)

    # Convert datetime → milliseconds for API
    timestamp_ms = int(message_db.timestamp.timestamp() * 1000)

    return Message(
        message_id=message_db.message_id,
        sender=message_db.sender,
        text=message_db.text,
        timestamp=timestamp_ms,
    )




@app.get("/chats/{chat_id}/messages", response_model=list[Message])
def get_messages(chat_id: int, session: Session = Depends(get_session)):
    """Return all messages of a specific chat."""
    # Ensure the chat exists
    chat = session.get(ChatDB, chat_id)
    if chat is None:
        raise HTTPException(status_code=404, detail="Chat not found")

    statement = (
        select(MessageDB)
        .where(MessageDB.chat_id == chat_id)
        .order_by(MessageDB.timestamp)
    )
    result = session.exec(statement)
    messages_db = result.all()

    return [
        Message(
            message_id=m.message_id,
            sender=m.sender,
            text=m.text,
            timestamp=int(m.timestamp.timestamp() * 1000),
        )
        for m in messages_db
    ]


@app.get("/chats", response_model=list[ChatSummary])
def get_all_chats(session: Session = Depends(get_session)):
    """Return all existing chats as summaries from the database."""
    statement = select(ChatDB).order_by(ChatDB.created_at)
    result = session.exec(statement)
    chats_db = result.all()

    return [
        ChatSummary(chat_id=chat.chat_id, title=chat.title)
        for chat in chats_db
    ]




@app.delete("/chats/{chat_id}")
def delete_chat(chat_id: int, session: Session = Depends(get_session)):
    """Delete a chat and all its messages."""
    chat = session.get(ChatDB, chat_id)
    print("Chat from DB:", chat)
    if chat is None:
        raise HTTPException(status_code=404, detail="Chat not found")

    session.delete(chat)
    session.commit()

    return {"success": True}