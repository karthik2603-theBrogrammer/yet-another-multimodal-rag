from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from kafka import KafkaProducer
import json
import requests
from typing import List
import os
from pydantic import BaseModel
from datetime import datetime
import logging
from dotenv import load_dotenv


load_dotenv()


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Configuration
NODEJS_API_URL = os.getenv("NODEJS_API_URL", "http://localhost:3000/api/insert-file")
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "file_uploads")
MAX_FILES = 3  # 


producer = KafkaProducer(
    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
    key_serializer=lambda v: json.dumps(v).encode('utf-8')
)
logger.info("Successfully Connected to Kafka")

class FileUploadResponse(BaseModel):
    fileId: str
    downloadUrl: str
    fileName: str
    uploadTimestamp: str
    status: str

class MultipleFileUploadResponse(BaseModel):
    uploads: List[FileUploadResponse]
    total_processed: int

@app.post("/upload-multiple", response_model=MultipleFileUploadResponse)
async def upload_files(files: List[UploadFile]):
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    
    if len(files) > MAX_FILES:
        raise HTTPException(
            status_code=400, 
            detail=f"Maximum {MAX_FILES} files allowed per request"
        )
    
    successful_uploads = []
    
    for file in files:
        try:
            file_content = await file.read()
            files_data = {
                'file': (file.filename, file_content, file.content_type)
            }
            response = requests.post(NODEJS_API_URL, files=files_data)
            if response.status_code != 200:
                logger.error(f"Error uploading file {file.filename}: {response.text}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Error from Node.js API for file {file.filename}: {response.text}"
                )
            
            nodejs_response = response.json()
            kafka_message = {
                **nodejs_response,
                "uploadTimestamp": datetime.utcnow().isoformat(),
                "status": "success",
                "originalFileName": file.filename,
                "contentType": file.content_type
            }
            try:
                future = producer.send(
                    KAFKA_TOPIC,
                    value=kafka_message,
                    key=nodejs_response["fileId"]
                )
                future.get(timeout=10)
                logger.info(f"Message sent to Kafka topic {KAFKA_TOPIC} for file {file.filename}")
            except Exception as e:
                logger.error(f"Failed to send message to Kafka for file {file.filename}: {str(e)}")
            
            successful_uploads.append(
                FileUploadResponse(
                    fileId=nodejs_response["fileId"],
                    downloadUrl=nodejs_response["downloadUrl"],
                    fileName=nodejs_response["fileName"],
                    uploadTimestamp=kafka_message["uploadTimestamp"],
                    status="success"
                )
            )
            
        except Exception as e:
            logger.error(f"Error processing file {file.filename}: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail={
                    "error": f"Error processing file {file.filename}: {str(e)}",
                    "processed_files": successful_uploads,
                    "failed_file": file.filename
                }
            )
    
    return MultipleFileUploadResponse(
        uploads=successful_uploads,
        total_processed=len(successful_uploads)
    )

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown"""
    producer.close()