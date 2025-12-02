from fastapi import FastAPI, HTTPException

from models import MessageInput, Chat, Message, ChatSummary, CreateChatInput
from storage import ChatStore

app = FastAPI()

# Single instance of ChatStore for the whole app
chat_store = ChatStore()


@app.get("/")
def root():
    return {"message": "Backend is working!"}


@app.post("/create_chat", response_model=ChatSummary)
def create_chat(data: CreateChatInput):
    """Create a new chat and return its summary."""
    chat = chat_store.create_chat(title=data.title)
    return ChatSummary(chat_id=chat.chat_id, title=chat.title)


@app.post("/send_message", response_model=Message)
def send_message(data: MessageInput):
    message = chat_store.add_message(
        chat_id = data.chat_id,
        sender = data.sender,
        text = data.text,
        timestamp = data.timestamp,
    )

    if message is None:
        raise HTTPException(status_code=404, detail="Chat not found")

    return message


@app.get("/chats/{chat_id}/messages", response_model=list[Message])
def get_messages(chat_id: int):
    """Return all messages of a specific chat."""
    messages = chat_store.get_messages(chat_id)

    if messages is None:
        raise HTTPException(status_code=404, detail="Chat not found")

    return messages


@app.get("/chats", response_model=list[ChatSummary])
def get_all_chats():
    """Return all existing chats as summaries."""
    chats = chat_store.get_all_chats()
    return [ChatSummary(chat_id=chat.chat_id, title=chat.title) for chat in chats]


