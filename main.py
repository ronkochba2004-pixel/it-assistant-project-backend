from datetime import time
from sqlite3 import IntegrityError
from fastapi import FastAPI, HTTPException, Depends
from sqlmodel import Session, select

from models import MessageInput, Chat, Message, ChatSummary, CreateChatInput, RenameChatInput, CreateUserInput, UserSummary, CompanySummary
from db import get_session
from db_models import ChatDB, MessageDB, CompanyDB, UserDB

app = FastAPI()


@app.get("/")
def root():
    return {"message": "Backend is working!"}


from datetime import datetime, timezone

@app.post("/create_chat", response_model=ChatSummary)
def create_chat(data: CreateChatInput, session: Session = Depends(get_session)):
    """Create a new chat row in the database and return its summary."""
    now_utc = datetime.now(timezone.utc)
    
    user = session.get(UserDB, data.user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    chat = ChatDB(
        title=data.title,
        user_id=data.user_id,
        created_at=now_utc,
        last_activity_at=now_utc,
    )

    session.add(chat)
    session.commit()
    session.refresh(chat)  # reload from DB so chat_id and timestamps are set

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

    # update last activity time when something *changes* in the chat
    chat.last_activity_at = datetime.now(timezone.utc)
    session.add(chat)


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
def get_all_chats(user_id: int, session: Session = Depends(get_session)): 
    """Return all chats for a specific user, ordered by last activity."""
    
    # Make sure the user exists
    user = session.get(UserDB, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    statement = (select(ChatDB).where(ChatDB.user_id == user_id).order_by(ChatDB.last_activity_at.desc()))
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


@app.patch("/chats/{chat_id}", response_model=ChatSummary)
def rename_chat(
chat_id: int,data: RenameChatInput,session: Session = Depends(get_session),):
    """Rename an existing chat."""
    chat = session.get(ChatDB, chat_id)
    if chat is None:
        raise HTTPException(status_code=404, detail="Chat not found")

    chat.title = data.title
    session.add(chat)
    session.commit()
    session.refresh(chat)

    return ChatSummary(chat_id=chat.chat_id, title=chat.title)


@app.post("/create_user", response_model=UserSummary)
def create_user(data: CreateUserInput, session: Session = Depends(get_session)):
    company = session.get(CompanyDB, data.company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")

    if data.role not in ("company_admin", "employee"):
        raise HTTPException(status_code=400, detail="Invalid role")

    user = UserDB(
        company_id=data.company_id,
        email=data.email,
        first_name=data.first_name,
        last_name=data.last_name,
        role=data.role,
        national_id=data.national_id
    )

    session.add(user)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=409, detail="Email already in use")

    session.refresh(user)

    return UserSummary(
        user_id=user.user_id,
        company_id=user.company_id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        role=user.role,
        national_id=data.national_id
    )


@app.get("/users/{user_id}", response_model=UserSummary)
def get_user(user_id: int, session: Session = Depends(get_session)):
    user = session.get(UserDB, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    return UserSummary(
        user_id=user.user_id,
        company_id=user.company_id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        role=user.role,
        national_id=user.national_id
    )


@app.get("/companies/{company_id}/users", response_model=list[UserSummary])
def list_users_for_company(company_id: int,session: Session = Depends(get_session),):
    company = session.get(CompanyDB, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")

    statement = select(UserDB).where(UserDB.company_id == company_id)
    result = session.exec(statement)
    users = result.all()

    return [
        UserSummary(
            user_id=u.user_id,
            company_id=u.company_id,
            email=u.email,
            first_name=u.first_name,
            last_name=u.last_name,
            role=u.role,
            national_id=u.national_id
        )
        for u in users
    ]


@app.get("/companies/{company_id}", response_model=CompanySummary)
def get_company(
    company_id: int,
    session: Session = Depends(get_session)
):
    company = session.get(CompanyDB, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")

    return CompanySummary(
        company_id=company.company_id,
        name=company.name
    )