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


class MessageInput(BaseModel): 
    chat_id: int
    sender: str
    text: str
    timestamp: int

