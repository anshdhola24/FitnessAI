# database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# SQLite DB in the project folder
SQLALCHEMY_DATABASE_URL = "sqlite:///fitness_ai.db"
# if you prefer the old name, you can change to: "sqlite:///fitnessai.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}  # needed for SQLite + threads
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# This is what models.py imports
Base = declarative_base()
