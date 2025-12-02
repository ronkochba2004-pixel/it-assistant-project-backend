
from sqlmodel import create_engine, Session
from typing import Generator

POSTGRES_USER = "postgres"
POSTGRES_PASSWORD = "1234"  
POSTGRES_HOST = "localhost"
POSTGRES_PORT = "5432"
POSTGRES_DB = "it_assistant_app"

DATABASE_URL = (
    f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
    f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)


engine = create_engine(DATABASE_URL, echo=True)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
