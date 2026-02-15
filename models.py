from typing import List, Optional
from pydantic import BaseModel, Field


class Message(BaseModel):
    message_id: int
    sender: str
    sender_id: Optional[int] = None # For user to user
    text: str
    timestamp: int
    image_urls: list[str] = []

class GenerateAssistantInput(BaseModel):
    chat_id: int

class Chat(BaseModel):
    chat_id: int
    title: str 
    messages: List[Message] = Field(default_factory=list) # List of messages in this chat


# נוסיף מודל ליצירת צ'אט בין אנשים
class CreateUserChatInput(BaseModel):
    user_id: int        # המשתמש שיוצר
    participant_id: int # המשתמש שאליו פונים
    title: str = "צ'אט אישי"


class ChatSummary(BaseModel):
    # A summary of a chat
    chat_id: int
    title: str
    chat_type: str

class CreateChatInput(BaseModel):
    # A class for the title of the chat that the app gives us
    title: str = ""
    user_id: int


class MessageInput(BaseModel): 
    chat_id: int
    sender: str
    sender_id: Optional[int] = None  # For user to user
    text: str
    image_urls: list[str] = []


class RenameChatInput(BaseModel):
    title: str


class CreateUserInput(BaseModel):
    company_id: int
    email: str
    first_name: str
    last_name: str
    role: str  # "company_admin" / "employee"
    national_id: str
    password: str


class UserSummary(BaseModel):
    user_id: int
    company_id: int
    email: str
    first_name: str
    last_name: str
    role: str
    national_id: str

class CompanySummary(BaseModel):
    company_id: int
    name: str



class LoginInput(BaseModel):
    email: str
    password: str

class LoginResponse(BaseModel):
    ok: bool
    user_id: int | None = None
