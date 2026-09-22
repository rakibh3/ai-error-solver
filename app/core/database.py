from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import DATABASE_URL

if not DATABASE_URL:
    raise RuntimeError(
        "POSTGRES_USER, POSTGRES_PASSWORD and POSTGRES_DB must all be set. "
        "Copy .env.example to .env and fill it in."
    )

engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
