from datetime import time as pytime, datetime, timezone
from time import sleep as sleep_seconds
from sqlite3 import IntegrityError
from uuid import uuid4
from fastapi import FastAPI, File, HTTPException, Depends, Query, UploadFile, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session, select, or_
from sqlalchemy.orm import selectinload
from typing import Optional
from pathlib import Path as FsPath
from passlib.context import CryptContext
import traceback
from models import (MessageInput, Chat, Message, ChatSummary, CreateChatInput, RenameChatInput,
                    CreateUserInput, UserSummary, CompanySummary,LoginInput,LoginResponse, GenerateAssistantInput,CreateUserChatInput)
from db import get_session,engine
from db_models import ChatDB, MessageDB, CompanyDB, MessageImageDB, UserDB
import os

app = FastAPI()


from groq import Groq

# Initialize the Groq client
# Replace with the gsk_ key you just created
api_key = os.getenv("GROQ_API_KEY")
client = Groq(api_key=api_key)





UPLOAD_DIR = FsPath("uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)
                           


@app.get("/")
def root():
    return {"message": "Backend is working!"}


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
        chat_type="ai", # Set default type as AI for this endpoint
        created_at=now_utc,
        last_activity_at=now_utc,
    )

    session.add(chat)
    session.commit()
    session.refresh(chat)  # reload from DB so chat_id and timestamps are set

    return ChatSummary(
        chat_id=chat.chat_id, 
        title=chat.title, 
        chat_type=chat.chat_type
    )


@app.post("/create_user_chat", response_model=ChatSummary)
def create_user_chat(data: CreateUserChatInput, session: Session = Depends(get_session)):
    now_utc = datetime.now(timezone.utc)
    
    # וידוא ששני המשתמשים קיימים
    user_a = session.get(UserDB, data.user_id)
    user_b = session.get(UserDB, data.participant_id)
    if not user_a or not user_b:
        raise HTTPException(status_code=404, detail="One or both users not found")

    chat = ChatDB(
        title=data.title,
        user_id=data.user_id,
        participant_id=data.participant_id,
        chat_type="user", # כאן אנחנו מגדירים שזה צ'אט בין אנשים
        created_at=now_utc,
        last_activity_at=now_utc,
    )

    session.add(chat)
    session.commit()
    session.refresh(chat)

    return ChatSummary(
        chat_id=chat.chat_id, 
        title=chat.title, 
        chat_type="user" 
    )


@app.post("/send_message", response_model=Message)
def send_message(
    data: MessageInput,
    background_tasks: BackgroundTasks,
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
        sender_id=data.sender_id,
        text=data.text,
    )

    session.add(message_db)

    # update last activity time when something *changes* in the chat
    chat.last_activity_at = datetime.now(timezone.utc)
    session.add(chat)


    session.commit()
    session.refresh(message_db)

      # Save images (if any)
    for idx, url in enumerate(data.image_urls):
        image_db = MessageImageDB(
            message_id=message_db.message_id,
            url=url,
            position=idx,
        )
        session.add(image_db)

    session.commit()

    if chat.chat_type == "ai" and data.sender == "user":
        print("[send_message] AI chat detected, scheduling assistant")
        background_tasks.add_task(
            create_ai_assistant_message,
            data.chat_id,
            data.text,
        )
    else:
        print(f"[send_message] User-to-user chat ({chat.chat_id}), skipping AI")


    # Convert datetime → milliseconds for API
    timestamp_ms = int(message_db.timestamp.timestamp() * 1000)

    return Message(
        message_id=message_db.message_id,
        sender=message_db.sender,
        sender_id=message_db.sender_id,
        text=message_db.text,
        timestamp=timestamp_ms,
    )


def get_chat_history_for_ai(session: Session, chat_id: int, limit: int = 10):
    """
    Retrieves the last X messages from a specific chat and formats them for the AI.
    Handles new chats with 0 messages gracefully.
    """
    # 1. Fetch the last messages from the DB
    # We use order_by(MessageDB.message_id.desc()) to get the newest ones first
    db_messages = (
        session.query(MessageDB)
        .filter(MessageDB.chat_id == chat_id)
        .order_by(MessageDB.message_id.desc())
        .limit(limit)
        .all()
    )

    # 2. Reverse them to maintain chronological order (oldest to newest)
    db_messages.reverse()

    # 3. Format into a list that Groq/OpenAI understands
    formatted_history = []
    for m in db_messages:
        role = "user" if m.sender == "user" else "assistant"
        formatted_history.append({"role": role, "content": m.text})
    
    return formatted_history


def create_ai_assistant_message(chat_id: int, user_text: str):
    print(f"[AI-Groq] generating response for chat_id={chat_id}")
    try:
        with Session(engine) as session:
            # Get conversation context using our helper function
            history = get_chat_history_for_ai(session, chat_id, limit=10)

            # Build the full message list for Groq
            messages_to_send = [
                {"role": "system", "content": "You are a helpful AI assistant."}
            ]
            
            # Add the history we retrieved
            messages_to_send.extend(history)

            # Note: We don't need to manually add user_text here 
            # because send_message already saved it to the DB, 
            # so get_chat_history_for_ai will include it in the list.

            # Call Groq API
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages_to_send,
            )
            ai_reply_text = completion.choices[0].message.content

            # Save assistant reply to DB
            chat = session.get(ChatDB, chat_id)
            if not chat: return

            message_db = MessageDB(
                chat_id=chat_id,
                sender="assistant",
                sender_id=None,
                text=ai_reply_text,
            )
            session.add(message_db)
            chat.last_activity_at = datetime.now(timezone.utc)
            session.commit()
            print(f"[AI-Groq] SUCCESS for chat {chat_id}")

    except Exception as e:
        print(f"[AI-Groq] ERROR: {e}")
        import traceback
        traceback.print_exc()


@app.get("/chats/{chat_id}/messages_after", response_model=list[Message])
def get_messages_after(
    chat_id: int,
    after_id: int = Query(..., ge=0),
    session: Session = Depends(get_session),
):
    """Checks what are the new messages after a spesific message, and returns the new ones"""
    # Ensure chat exists
    chat = session.get(ChatDB, chat_id)
    if chat is None:
        raise HTTPException(status_code=404, detail="Chat not found")

    statement = (
        select(MessageDB)
        .where(MessageDB.chat_id == chat_id)
        .where(MessageDB.message_id > after_id)
        .order_by(MessageDB.message_id)
        .options(selectinload(MessageDB.images))
    )

    messages_db = session.exec(statement).all()

    return [
        Message(
            message_id=m.message_id,
            sender=m.sender,
            sender_id=m.sender_id, # For user to user
            text=m.text,
            timestamp=int(m.timestamp.timestamp() * 1000),
            image_urls=[
                img.url
                for img in sorted(m.images, key=lambda i: i.position)
            ],
        )
        for m in messages_db
    ]


@app.get("/chats/{chat_id}/messages_before", response_model=list[Message])
def get_messages_before(
    chat_id: int,
    before_id: Optional[int] = Query(default=None, ge=1),
    limit: int = Query(default=30, ge=1, le=100),
    session: Session = Depends(get_session),
):
    # Ensure chat exists
    chat = session.get(ChatDB, chat_id)
    if chat is None:
        raise HTTPException(status_code=404, detail="Chat not found")

    stmt = (
        select(MessageDB)
        .where(MessageDB.chat_id == chat_id)
        .options(selectinload(MessageDB.images))
    )

    # If before_id is provided -> fetch older than that
    if before_id is not None:
        stmt = stmt.where(MessageDB.message_id < before_id)

    # Fetch newest-first then reverse to chronological order
    stmt = stmt.order_by(MessageDB.message_id.desc()).limit(limit)

    messages_db = session.exec(stmt).all()
    messages_db.reverse()  # now oldest->newest for UI append-at-top

    return [
        Message(
            message_id=m.message_id,
            sender=m.sender,
            sender_id=m.sender_id, # For user to user
            text=m.text,
            timestamp=int(m.timestamp.timestamp() * 1000),
            image_urls=[img.url for img in sorted(m.images, key=lambda i: i.position)],
        )
        for m in messages_db
    ]


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
        .options(selectinload(MessageDB.images))
    )
    result = session.exec(statement)
    messages_db = result.all()

    return [
        Message(
            message_id=m.message_id,
            sender=m.sender,
            text=m.text,
            timestamp=int(m.timestamp.timestamp() * 1000),
             image_urls=[
                img.url
                for img in sorted(m.images, key=lambda i: i.position)
            ],
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

    statement = (
        select(ChatDB)
        .where(or_(ChatDB.user_id == user_id, ChatDB.participant_id == user_id))
        .order_by(ChatDB.last_activity_at.desc())
    )

    result = session.exec(statement)
    chats_db = result.all()

    return [
        ChatSummary(
            chat_id=chat.chat_id, 
            title=chat.title, 
            chat_type=chat.chat_type
        )
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

    return ChatSummary(
        chat_id=chat.chat_id, 
        title=chat.title, 
        chat_type="user" 
    )


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
        national_id=data.national_id,
        password_hash=hash_password(data.password)
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
        national_id=user.national_id
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

@app.get("/users/by_national_id/{national_id}", response_model=UserSummary)
def get_user_by_national_id(national_id: str, session: Session = Depends(get_session)):
    statement = select(UserDB).where(UserDB.national_id == national_id)
    user = session.exec(statement).first()
    
    if user is None:
        raise HTTPException(status_code=404, detail="User not found with this ID")

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

@app.delete("/users/{user_id}", status_code=204)
def delete_user(user_id: int, session: Session = Depends(get_session)):
    user = session.get(UserDB, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    session.delete(user)
    session.commit()
    return

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


@app.post("/upload_images")
async def upload_images(images: list[UploadFile] = File(...)):
    image_urls: list[str] = []

    for img in images:
        suffix = FsPath(img.filename).suffix if img.filename else ""
        filename = f"{uuid4()}{suffix}"
        file_path = UPLOAD_DIR / filename

        content = await img.read()
        file_path.write_bytes(content)

        # returning a path that the client can request later
        image_urls.append(f"/uploads/{filename}")

    return {"image_urls": image_urls}


@app.post("/login", response_model=LoginResponse)
def login(data: LoginInput, session: Session = Depends(get_session)):
    # Find user by email
    statement = select(UserDB).where(UserDB.email == data.email)
    user = session.exec(statement).first()

    # Always return the same error message
    if user is None or user.password_hash is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Verify password
    if not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return LoginResponse(ok=True, user_id=user.user_id)