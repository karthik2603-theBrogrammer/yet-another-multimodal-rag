from fastapi import FastAPI, HTTPException, Depends, status, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from pydantic import BaseModel
from typing import List, Optional
import os
import uuid
import sys
import uvicorn
from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain.prompts import ChatPromptTemplate
from langchain.schema.output_parser import StrOutputParser
from langchain.schema.runnable import RunnablePassthrough, RunnableLambda
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_community.chat_message_histories import ChatMessageHistory

from get_llm import get_llm
from get_db import get_retriever
from rag_utils import encode_image, prompt_func, split_image_text_types
from logger import logger


from models import Base, User
from auth import (
    authenticate_user, 
    create_access_token, 
    get_current_user, 
    get_db, 
    get_password_hash, 
    UserCreate,
    UserLogin,
    Token
)

# Create database tables
from sqlalchemy import create_engine
engine = create_engine(os.getenv("DATABASE_URL", "sqlite:///./users.db"))
Base.metadata.create_all(bind=engine)


# Load environment variables
load_dotenv()
ACCESS_TOKEN_EXPIRE_MINUTES = 35
# Initialize FastAPI app
app = FastAPI()

# Pydantic models for request validation
class TextRequest(BaseModel):
    texts: List[str]

class TableRequest(BaseModel):
    tables: List[str]
    table_summaries: List[str]

class ImageRequest(BaseModel):
    image_b64_list: List[str]
    image_summaries: List[str]

class QuestionRequest(BaseModel):
    question: str

class Message(BaseModel):
    role: str  # "human" or "ai"
    content: str

class ChatSession(BaseModel):
    session_id: str
    messages: List[Message]

class ChatRequest(BaseModel):
    session_id: Optional[str]
    question: str


class TestRequest(BaseModel):
    some_text: str

chat_sessions = {}

# Initialize retriever
pinecone_api_key = os.getenv("PINECONE_API_KEY")
if not pinecone_api_key:
    logger.error("PINECONE_API_KEY not set.")
    sys.exit(1)
else:
    logger.info("API SET")
    
retriever = get_retriever(pinecone_api_key=pinecone_api_key)


@app.post("/api/chat/create")
async def create_chat_session():
    """Create a new chat session."""
    try:
        session_id = str(uuid.uuid4())
        chat_sessions[session_id] = ChatMessageHistory()
        logger.info(f"Created new chat session: {session_id}")
        return {"session_id": session_id}
    except Exception as e:
        logger.error(f"Error creating chat session: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/chat/{session_id}")
async def get_chat_history(session_id: str):
    """Retrieve chat history for a session."""
    try:
        if session_id not in chat_sessions:
            raise HTTPException(status_code=404, detail="Chat session not found")
        
        history = chat_sessions[session_id]
        messages = [
            Message(
                role="human" if isinstance(msg, HumanMessage) else "ai",
                content=msg.content
            )
            for msg in history.messages
        ]
        return ChatSession(session_id=session_id, messages=messages)
    except Exception as e:
        logger.error(f"Error retrieving chat history: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/chat/{session_id}")
async def delete_chat_session(session_id: str):
    """Delete a chat session."""
    try:
        if session_id not in chat_sessions:
            raise HTTPException(status_code=404, detail="Chat session not found")
        
        del chat_sessions[session_id]
        logger.info(f"Deleted chat session: {session_id}")
        return {"status": "success", "message": "Chat session deleted"}
    except Exception as e:
        logger.error(f"Error deleting chat session: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/insert-text")
async def insert_text(request: TextRequest):
    """Insert texts into vector DB and doc store."""
    try:
        doc_ids = [str(uuid.uuid4()) for _ in request.texts]
        documents = [
            Document(page_content=text, metadata={"doc_id": doc_ids[i]})
            for i, text in enumerate(request.texts)
        ]
        retriever.vectorstore.add_documents(documents)
        retriever.docstore.mset(list(zip(doc_ids, request.texts)))
        logger.info(f"Successfully inserted {len(request.texts)} texts")
        return {"status": "success", "inserted": len(request.texts)}
    except Exception as e:
        logger.error(f"Error inserting texts: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/insert-table")
async def insert_table(request: TableRequest):
    """Insert tables into vector DB and doc store."""
    try:
        if len(request.tables) != len(request.table_summaries):
            raise HTTPException(
                status_code=400, 
                detail="Number of tables and summaries must match"
            )
        
        table_ids = [str(uuid.uuid4()) for _ in request.tables]
        documents = [
            Document(page_content=summary, metadata={"doc_id": table_ids[i]})
            for i, summary in enumerate(request.table_summaries)
        ]
        retriever.vectorstore.add_documents(documents)
        retriever.docstore.mset(list(zip(table_ids, request.tables)))
        logger.info(f"Successfully inserted {len(request.tables)} tables")
        return {"status": "success", "inserted": len(request.tables)}
    except Exception as e:
        logger.error(f"Error inserting tables: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/insert-image")
async def insert_image(request: ImageRequest):
    """Insert images into vector DB and doc store."""
    try:
        if len(request.image_b64_list) != len(request.image_summaries):
            raise HTTPException(
                status_code=400, 
                detail="Number of images and summaries must match"
            )
            
        img_ids = [str(uuid.uuid4()) for _ in request.image_b64_list]
        documents = [
            Document(page_content=summary, metadata={"doc_id": img_ids[i]})
            for i, summary in enumerate(request.image_summaries)
        ]
        retriever.vectorstore.add_documents(documents)
        retriever.docstore.mset(list(zip(img_ids, request.image_b64_list)))
        logger.info(f"Successfully inserted {len(request.image_b64_list)} images")
        return {"status": "success", "inserted": len(request.image_b64_list)}
    except Exception as e:
        logger.error(f"Error inserting images: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/test")
async def test_fn(
    request: TestRequest,
    current_user: dict = Depends(get_current_user)
):
    """A test function used during development to check if JWT based token 
    authentication is working properly. Must validate user presence, token expiration."""
    logger.info(request.some_text)
    return {"status": "All Good"}
# Modify the existing generate endpoint to support chat history
@app.post("/api/generate")
async def generate(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user)
    ):
    """Invoke the RAG pipeline to answer a question with chat history."""
    try:
        # Get or create chat history
        if request.session_id:
            if request.session_id not in chat_sessions:
                raise HTTPException(status_code=404, detail="Chat session not found")
            history = chat_sessions[request.session_id]
        else:
            history = ChatMessageHistory()
            
        # Add the new question to history
        history.add_user_message(request.question)
        
        # Create the chat prompt with history context
        messages = history.messages
        
        # Modify the chain to include chat history
        chain = (
            {
                "context": retriever | RunnableLambda(split_image_text_types),
                "question": RunnablePassthrough(),
                "chat_history": RunnableLambda(lambda _: messages[:-1])  # Exclude the current question
            }
            | RunnableLambda(lambda x: prompt_func(x, debug=True))
            | get_llm()
            | StrOutputParser()
        )
        
        # Generate response
        response = chain.invoke(request.question)
        
        # Add the AI response to history
        history.add_ai_message(response)
        
        # If this was a new session, store it
        if not request.session_id:
            session_id = str(uuid.uuid4())
            chat_sessions[session_id] = history
        else:
            session_id = request.session_id
            
        return {
            "session_id": session_id,
            "question": request.question,
            "response": response
        }
    except Exception as e:
        logger.error(f"Error generating response: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Auth Endpoints
@app.post("/signup")
def signup(user: UserCreate, db: Session = Depends(get_db)):
    """User registration endpoint"""
    # Check if user already exists
    existing_user = db.query(User).filter(
        (User.username == user.username) | (User.email == user.email)
    ).first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already registered"
        )
    
    # Create new user
    hashed_password = get_password_hash(user.password)
    db_user = User(
        username=user.username, 
        email=user.email, 
        hashed_password=hashed_password
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return {"message": "User created successfully"}

@app.post("/api/login", response_model=Token)
def login(
    response: Response, 
    form_data: OAuth2PasswordRequestForm = Depends(), 
    db: Session = Depends(get_db)
):
    """User login endpoint with JWT token in cookie"""
    user = authenticate_user(db, form_data.username, form_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    # Set token in HTTP-only cookie
    response.set_cookie(
        key="access_token", 
        value=access_token, 
        httponly=True, 
        secure=True,  # Use only in HTTPS
        samesite='lax'
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/api/logout")
def logout(response: Response):
    """User logout endpoint"""
    response.delete_cookie("access_token")
    return {"message": "Logged out successfully"}


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run(app, host=host, port=port)