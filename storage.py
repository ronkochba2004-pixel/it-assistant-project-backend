from typing import Dict, List, Optional
from models import Chat, Message


class ChatStore:
    """In-memory storage for chats and messages."""

    def __init__(self) -> None:
        # key = chat_id, value = Chat object
        self._chats: Dict[int, Chat] = {} # Dict to save all the chats
        self._next_chat_id: int = 1 # Variable to save the next ID for a new chat
        self._next_message_id: Dict[int, int] = {} # A dict with variables to save the next ID for a new massege

    def create_chat(self, title: str = "") -> Chat:
        chat_id = self._next_chat_id
        chat = Chat(chat_id=chat_id, title=title)
        self._chats[chat_id] = chat
        self._next_chat_id += 1
        self._next_message_id[chat_id] = 1
        return chat

    def get_chat(self, chat_id: int) -> Optional[Chat]:
        """Return a chat by id, or None if it does not exist."""
        return self._chats.get(chat_id)

    def add_message(self, chat_id: int, sender: str, text: str, timestamp: int) -> Optional[Message]:
        chat = self.get_chat(chat_id)
        if chat is None:
            return None

        # message_id for this chat
        message_id = self._next_message_id[chat_id]
        self._next_message_id[chat_id] += 1

        message = Message(
            message_id=message_id,
            sender=sender,
            text=text,
            timestamp=timestamp,
        )

        chat.messages.append(message)
        return message


    def get_messages(self, chat_id: int) -> Optional[List[Message]]:
        """Return all messages of a chat, or None if chat not found."""
        chat = self.get_chat(chat_id)
        if chat is None:
            return None
        return chat.messages

    def get_all_chats(self) -> list[Chat]:
        """Return a list of all chats."""
        return list(self._chats.values())
    

    
