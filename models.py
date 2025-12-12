from typing import List
from pydantic import BaseModel, Field


class Message(BaseModel):
    message_id: int
    sender: str
    text: str
    timestamp: int



class Chat(BaseModel):
    chat_id: int
    title: str 
    messages: List[Message] = Field(default_factory=list) # List of messages in this chat


class ChatSummary(BaseModel):
    # A summary of a chat
    chat_id: int
    title: str

class CreateChatInput(BaseModel):
    # A class for the title of the chat that the app gives us
    title: str = ""
    user_id: int


class MessageInput(BaseModel): 
    chat_id: int
    sender: str
    text: str


class RenameChatInput(BaseModel):
    title: str


class CreateUserInput(BaseModel):
    company_id: int
    email: str
    first_name: str
    last_name: str
    role: str  # "company_admin" / "employee"
    national_id: str


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
