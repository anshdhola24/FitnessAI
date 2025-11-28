# models.py
from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship

from database import Base, engine


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)

    profile = relationship("UserProfile", back_populates="user", uselist=False)
    plans = relationship("Plan", back_populates="user")
    progress = relationship("Progress", back_populates="user")


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    age = Column(Integer, nullable=False)
    gender = Column(String, nullable=False)
    height_cm = Column(Float, nullable=False)
    weight_kg = Column(Float, nullable=False)
    activity_level = Column(String, nullable=False)   # sedentary / light / ...
    goal = Column(String, nullable=False)             # lose / gain / maintain

    # NEW: workout experience level
    experience_level = Column(String, nullable=False, default="beginner")
    # "beginner", "intermediate", "advanced"

    user = relationship("User", back_populates="profile")


class Plan(Base):
    __tablename__ = "plans"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    bmi = Column(Float, nullable=False)
    bmr = Column(Float, nullable=False)
    calories_target = Column(Integer, nullable=False)

    # stored as stringified dicts
    diet_plan = Column(String, nullable=False)
    workout_plan = Column(String, nullable=False)

    user = relationship("User", back_populates="plans")


class Progress(Base):
    __tablename__ = "progress"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    day = Column(Integer, nullable=False)         # Day 1,2,3...
    weight_kg = Column(Float, nullable=False)

    user = relationship("User", back_populates="progress")


def init_db():
    """Create all tables."""
    Base.metadata.create_all(bind=engine)
