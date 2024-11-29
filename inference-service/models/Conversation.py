# from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
# from sqlalchemy.orm import relationship
# from sqlalchemy.ext.declarative import declarative_base
# from datetime import datetime
# import uuid

# from .User import User

# Base = declarative_base()

# class Conversation(Base):
#     __tablename__ = "conversations"

#     id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
#     user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
#     summary = Column(String, nullable=True)
#     created_at = Column(DateTime, default=datetime.utcnow)
#     updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
#     # Relationship to User and Messages
#     user = relationship("User", back_populates="conversations")
#     messages = relationship("Message", back_populates="conversation")

# class Message(Base):
#     __tablename__ = "messages"

#     id = Column(Integer, primary_key=True, index=True)
#     conversation_id = Column(String(36), ForeignKey('conversations.id'), nullable=False)
#     role = Column(String, nullable=False)  # 'human' or 'ai'
#     content = Column(Text, nullable=False)
#     timestamp = Column(DateTime, default=datetime.utcnow)

#     # Relationship to Conversation
#     conversation = relationship("Conversation", back_populates="messages")

# # Update User model to include relationship
# User.conversations = relationship("Conversation", back_populates="user")