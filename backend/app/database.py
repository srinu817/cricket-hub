import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


load_dotenv()


def normalize_database_url(value: str) -> str:
    database_url = make_url(value)
    if database_url.drivername in ("postgres", "postgresql"):
        database_url = database_url.set(drivername="postgresql+psycopg")
    return database_url.render_as_string(hide_password=False)


if os.getenv("DATABASE_URL"):
    DATABASE_URL = normalize_database_url(os.environ["DATABASE_URL"])
elif os.getenv("DB_HOST"):
    DATABASE_URL = URL.create(
        "postgresql+psycopg",
        username=os.getenv("DB_USER", "cricket_hub"),
        password=os.getenv("DB_PASSWORD", ""),
        host=os.environ["DB_HOST"],
        port=int(os.getenv("DB_PORT", "5432")),
        database=os.getenv("DB_NAME", "cricket_hub"),
    ).render_as_string(hide_password=False)
else:
    DATABASE_URL = "sqlite:///./data/cricket_hub.db"
url = make_url(DATABASE_URL)

if url.get_backend_name() == "sqlite" and url.database not in (None, "", ":memory:"):
    Path(url.database).parent.mkdir(parents=True, exist_ok=True)

engine_options = {"pool_pre_ping": True}
if url.get_backend_name() == "sqlite":
    engine_options["connect_args"] = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, **engine_options)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
