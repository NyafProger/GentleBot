from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from database.base import Base
from datetime import datetime

class Word(Base):
    __tablename__ = "words"

    id = Column(Integer, primary_key=True, index=True)
    word = Column(String, unique=True, nullable=False)
    translation = Column(String, nullable=False)
    example = Column(String, nullable=True)
    correct_answer_count = Column(Integer, default=0)
    last_guessed = Column(DateTime, default=datetime.utcnow)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)

