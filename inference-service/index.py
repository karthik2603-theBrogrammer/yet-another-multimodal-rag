# index.py
from fastapi import FastAPI, HTTPException, Depends, status, Response, Request, Path, Body
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc
from pydantic import BaseModel
import asyncio
from typing import List, Optional, Dict
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
from datetime import datetime, timedelta


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
    RefreshTokenRequest,
    Token,
    verify_refresh_token,
    create_refresh_token
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
origins = [
    "http://localhost:3000",  # React or frontend running on localhost
    "http://example.com",     # Your production domain
    "*"
]

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,          # Allow specific origins
    allow_credentials=True,         # Allow cookies and headers with credentials
    allow_methods=["*"],            # Allow all HTTP methods
    allow_headers=["*"],            # Allow all headers
)

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
    message_id: str
    role: str  # "human" or "ai"
    content: str
    created_at: datetime

class ChatConversation(BaseModel):
    conversation_id: str
    summary: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    messages: List[Message] = []

    def add_user_message(self, content: str):
        """Add a user message to the conversation."""
        self.messages.append(Message(
            message_id=str(uuid.uuid4()),  # Add a unique ID
            role="user", 
            content=content, 
            created_at=datetime.now()
        ))
        self.updated_at = datetime.now()

    def add_ai_message(self, content: str):
        """Add an AI message to the conversation."""
        self.messages.append(Message(
            message_id=str(uuid.uuid4()),  # Add a unique ID
            role="assistant", 
            content=content, 
            created_at=datetime.now()
        ))
        self.updated_at = datetime.now()

        # Update summary if not set or if it's too short
        if not self.summary or len(self.summary) < 100:
            self.summary = content[:100]

class ChatRequest(BaseModel):
    conversation_id: Optional[str] = None
    question: str

class ChatRequestIndividualMessage(BaseModel):
    role: str
    content: str
class ChatRequestGenerateStream(BaseModel):
    messages: List[ChatRequestIndividualMessage]
    conversation_id: str


class TestRequest(BaseModel):
    some_text: str

chat_conversations: Dict[str, ChatConversation] = {}

# Initialize retriever
pinecone_api_key = os.getenv("PINECONE_API_KEY")
if not pinecone_api_key:
    logger.error("PINECONE_API_KEY not set.")
    sys.exit(1)
else:
    logger.info("API SET")
    
retriever = get_retriever(pinecone_api_key=pinecone_api_key)


@app.post("/api/conversation/create")
async def create_chat_conversation():
    """Create a new chat conversation."""
    try:
        conversation_id = str(uuid.uuid4())
        conversation = ChatConversation(
            conversation_id=conversation_id,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            messages=[]
        )
        chat_conversations[conversation_id] = conversation
        logger.info(f"Created new chat conversation: {conversation_id}")
        return {"conversation_id": conversation_id}
    except Exception as e:
        logger.error(f"Error creating chat session: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/chat/{conversation_id}")
async def get_chat_history(conversation_id: str):
    """Retrieve chat history for a conversation."""
    try:
        if conversation_id not in chat_conversations:
            raise HTTPException(status_code=404, detail="Chat session not found")
        
        return chat_conversations[conversation_id]
    except Exception as e:
        logger.error(f"Error retrieving chat history: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/newwww")
async def get_chat_history_list():
    """Retrieve list of existing chat conversations grouped by date."""
    try:
        logger.info(f"Retrieving all chat conversations: {chat_conversations}")
        
        # Prepare grouping data structure matching frontend interface
        grouped_conversations = {
            "today": [],
            "yesterday": [],
            "last7Days": [],
            "beforeThat": []
        }
        
        now = datetime.now()
        
        for conversation in chat_conversations.values():
            # if not conversation or not conversation.messages:
            #     logger.warning(f"Skipping conversation {conversation.conversation_id} due to invalid history")
            #     continue
            
            # Create conversation object matching frontend interface
            conversation_dict = {
                "_id": conversation.conversation_id,
                "summary": conversation.summary or (conversation.messages[0].content[:100] if conversation.messages else ""),
                "created_at": conversation.created_at.isoformat(),
                "updated_at": conversation.updated_at.isoformat(),
                "messages": [
                                {
                                    "_id": msg.message_id, 
                                    "role": msg.role, 
                                    "content": msg.content, 
                                    "created_at": msg.created_at.isoformat()
                                } 
                                for msg in conversation.messages
                            ]
            }
            
            # Group conversations
            days_diff = (now - conversation.created_at).days
            if days_diff == 0:
                grouped_conversations["today"].append(conversation_dict)
            elif days_diff == 1:
                grouped_conversations["yesterday"].append(conversation_dict)
            elif days_diff < 7:
                grouped_conversations["last7Days"].append(conversation_dict)
            else:
                grouped_conversations["beforeThat"].append(conversation_dict)
        
        logger.info(f"Retrieved conversations: {sum(len(group) for group in grouped_conversations.values())} total")
        return {
            "conversations": grouped_conversations,
            "total_count": sum(len(group) for group in grouped_conversations.values())
        }
    except Exception as e:
        logger.error(f"Error retrieving chat conversation list: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.delete("/api/chat/{conversation_id}")
async def delete_chat_session(conversation_id: str):
    """Delete a chat conversation."""
    try:
        if conversation_id not in chat_conversations:
            raise HTTPException(status_code=404, detail="Chat conversation not found")
        
        del chat_conversations[conversation_id]
        logger.info(f"Deleted chat conversation: {conversation_id}")
        return {"status": "success", "message": "Chat conversation deleted"}
    except Exception as e:
        logger.error(f"Error deleting chat conversation: {str(e)}")
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

# @app.post("/api/generate")
# async def generate(request: ChatRequest):
#     """Invoke the RAG pipeline to answer a question with chat history."""
#     try:
#         # Get or create chat conversation
#         if request.conversation_id:
#             if request.conversation_id not in chat_conversations:
#                 raise HTTPException(status_code=404, detail="Chat session not found")
#             conversation = chat_conversations[request.conversation_id]
#         else:
#             # Create new conversation if not exists
#             conversation_id = str(uuid.uuid4())
#             conversation = ChatConversation(
#                 conversation_id=conversation_id,
#                 created_at=datetime.now(),
#                 updated_at=datetime.now(),
#                 messages=[]
#             )
#             chat_conversations[conversation_id] = conversation
        
#         # Add the new question to conversation
#         conversation.add_user_message(request.question)
        
#         # Modify the chain to include chat history
#         messages = conversation.messages
        
#         chain = (
#             {
#                 "context": retriever | RunnableLambda(split_image_text_types),
#                 "question": RunnablePassthrough(),
#                 "chat_history": RunnableLambda(lambda _: messages[:-1])  # Exclude the current question
#             }
#             | RunnableLambda(lambda x: prompt_func(x, debug=True))
#             | get_llm()
#             | StrOutputParser()
#         )
        
#         # Generate response
#         response = chain.invoke(request.question)
        
#         # Add the AI response to conversation
#         conversation.add_ai_message(response)
            
#         return {
#             "conversation_id": conversation.conversation_id,
#             "question": request.question,
#             "response": response
#         }
#     except Exception as e:
#         logger.error(f"Error generating response: {str(e)}")
#         raise HTTPException(status_code=500, detail=str(e))
@app.post("/api/generate/stream")
async def generate_stream(
    request: ChatRequestGenerateStream,
    request_from_REST_API: Request
):
    """Invoke the RAG pipeline to answer a question with streaming."""
    try:
        # Get or create chat conversation
        # logger.info(chat_conversations)
        logger.info(request.conversation_id)
        if request.conversation_id:
            if request.conversation_id not in chat_conversations:
                raise HTTPException(status_code=404, detail="Chat session not found")
            conversation = chat_conversations[request.conversation_id]
        else:
            # Create new conversation if not exists
            conversation_id = str(uuid.uuid4())
            conversation = ChatConversation(
                conversation_id=conversation_id,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                messages=[]
            )
            chat_conversations[conversation_id] = conversation

        request_prompt_to_llm = request.messages[-1].content

        # Add the new question to conversation
        conversation.add_user_message(request_prompt_to_llm)

        # Create the chat prompt with history context
        messages = conversation.messages

        # Define the chain
        chain = (
            {
                "context": retriever | RunnableLambda(split_image_text_types),
                "question": RunnablePassthrough(),
                "chat_history": RunnableLambda(lambda _: messages[:-1])  # Exclude the current question
            }
            | RunnableLambda(lambda x: prompt_func(x, debug=True))
            | get_llm(allow_streaming=True)
            | StrOutputParser()
        )

        async def generate_response():
            """Async generator that streams AI response."""
            async for token in chain.astream(request_prompt_to_llm):
                yield token

        # Add the AI response to conversation (use the full response for history purposes)
        full_response = "".join([token async for token in generate_response()])
        conversation.add_ai_message(full_response)

        # Return streaming response
        return StreamingResponse(generate_response(), media_type="text/plain")

    except Exception as e:
        logger.error(f"Error generating response: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

class EditSummaryRequest(BaseModel):
    conversation_id: str
    summary: str


@app.patch("/api/conversations/summary/edit")
async def patch_conversation_summary(
    request_body: EditSummaryRequest
):
    conversation_id = request_body.conversation_id
    summary = request_body.summary
    if not chat_conversations or conversation_id not in chat_conversations:
        raise HTTPException(status_code=404, detail="Chat session not found")

    # Update the summary of the specific conversation
    conversation = chat_conversations[conversation_id]
    conversation.summary = summary
    conversation.updated_at = datetime.now()

    return {"status": "success", "message": "Summary updated"}


@app.delete("/api/conversations/{conversation_id}/delete")
async def delete_conversation (
    conversation_id: str
):
    if conversation_id not in chat_conversations:
        raise HTTPException(status_code = 404, detail = "Chat Conversation not found. Try again")

    del chat_conversations[conversation_id]















# Auth Endpoints
@app.post("/api/signup")
def signup(user: UserCreate, db: Session = Depends(get_db)):
    """User registration endpoint"""
    logger.info(f"Signup data received: {user.dict()}")
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
    
    return {"status": "success", "message": "User created successfully"}

@app.post("/api/login", response_model=Token)
def login(
    response: Response, 
    form_data: OAuth2PasswordRequestForm = Depends(), 
    db: Session = Depends(get_db)
):
    """User login endpoint with JWT access and refresh tokens in cookie"""
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
    
    # Create refresh token 
    refresh_token_expires = timedelta(days=7)
    refresh_token = create_refresh_token(
        data={"sub": user.username}, expires_delta=refresh_token_expires
    )
    
    # Set tokens in HTTP-only cookies
    response.set_cookie(
        key="access_token", 
        value=access_token, 
        httponly=True, 
        secure=True,  # Use only in HTTPS
        samesite='lax',
        max_age=int(access_token_expires.total_seconds())
    )
    
    response.set_cookie(
        key="refresh_token", 
        value=refresh_token, 
        httponly=True, 
        secure=True,  # Use only in HTTPS
        samesite='lax',
        max_age=int(refresh_token_expires.total_seconds())
    )
    
    return {
        "username": user.username,
        "email": user.email,
        "access_token": access_token, 
        "refresh_token": refresh_token, 
        "token_type": "bearer"
    }

@app.get("/api/me")
async def get_current_user_details(
    current_user: dict = Depends(get_current_user)
):
    """
    Fetch user details from the current token.
    Requires a valid access_token passed in the Authorization header.
    """
    try:
        user_details = {
            "email": current_user.email,
            "username": current_user.username
        }
        return user_details
    except AttributeError as e:
        logger.error(f"Error retrieving user data: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User data incomplete or unavailable"
        )

@app.post("/api/auth/refresh")
def refresh_token(
    request: RefreshTokenRequest,
    response: Response,
    db: Session = Depends(get_db)
):
    """Refresh access token using a valid refresh token"""
    try:
        # Verify the refresh token
        user = verify_refresh_token(request.refresh_token, db)
        
        # Create new access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        new_access_token = create_access_token(
            data={"sub": user.username}, 
            expires_delta=access_token_expires
        )

        refresh_token_expires = timedelta(days=7)
        refresh_token = create_refresh_token(
            data={"sub": user.username}, expires_delta=refresh_token_expires
        )
        
        # Set new access token in cookie
        response.set_cookie(
            key="access_token", 
            value=new_access_token, 
            httponly=True, 
            secure=True,  
            samesite='lax',
            max_age=int(access_token_expires.total_seconds())
        )

        response.set_cookie(
            key="refresh_token", 
            value=refresh_token, 
            httponly=True, 
            secure=True,  
            samesite='lax',
            max_age=int(refresh_token_expires.total_seconds())
        )
        
        return {
            "access_token": new_access_token, 
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }
    except HTTPException as e:
        # Re-raise the authentication exception
        raise e

@app.get("/stream")
async def stream_response():
    """Endpoint that returns a streaming response"""

    async def generate_response():
        """Async generator that simulates streaming a response"""
        responses = [
            "Hello, ",
            "this is ",
            "a streaming ",
            "response ",
            "from FastAPI!"
        ]
        
        for response in responses:
            # Simulate some processing time
            await asyncio.sleep(0.5)
            yield response

    return StreamingResponse(generate_response(), media_type="text/plain")


@app.post("/api/stream")
async def stream_response(request: Request):
    """Endpoint that returns a streaming response"""
    body = await request.body()
    print(f"Request Body: {body.decode('utf-8')}")  # Assuming the body is UTF-8 encoded


    async def generate_response():
        """Async generator that simulates streaming a response"""
        responses = [
            "Hello, ",
            "this is ",
            "a streaming ",
            "response ",
            "from FastAPI!"
        ]
        
        for response in responses:
            # Simulate some processing time
            await asyncio.sleep(0.5)
            yield response

    return StreamingResponse(generate_response(), media_type="text/plain")

@app.post("/api/logout")
def logout(response: Response):
    """User logout endpoint - delete both access and refresh tokens"""
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return {"message": "Logged out successfully"}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run(app, host=host, port=port)