import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# We default to SQLite for local development. 
# To switch to PostgreSQL later, just add DATABASE_URL to your .env file.
SQLALCHEMY_DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "sqlite:///./predictions.db"
)

# The connect_args dictionary is only needed for SQLite to handle threading
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False} if "sqlite" in SQLALCHEMY_DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """Yields a database session and safely closes it after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()