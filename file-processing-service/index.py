import json
import os
import requests
import logging
from kafka import KafkaConsumer
from dotenv import load_dotenv
from datetime import datetime
import time

from file_processing_utils import DocumentProcessor
from get_llm import get_llm

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FileProcessingPipeline:
    def __init__(self):
        # Configuration
        self.kafka_bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        self.kafka_topic = os.getenv("KAFKA_TOPIC", "file_uploads")
        self.download_dir = os.getenv("DOWNLOAD_DIR", "downloaded_files")
        self.processed_dir = os.getenv("PROCESSED_DIR", "processed_files")
        self.llm_api_key = os.getenv("GOOGLE_API_KEY")

        self.llm = get_llm(api_key = self.llm_api_key)
        self.api_base_url = os.getenv("INFERENCE_API_BASE_URL")
        self.document_processor = DocumentProcessor(llm=self.llm, api_base_url=self.api_base_url)
        
        # Ensure directories exist
        os.makedirs(self.download_dir, exist_ok=True)
        os.makedirs(self.processed_dir, exist_ok=True)
        
        # Initialize Kafka consumer
        self.consumer = KafkaConsumer(
            self.kafka_topic,
            bootstrap_servers=self.kafka_bootstrap_servers,
            value_deserializer=lambda x: json.loads(x.decode('utf-8')),
            key_deserializer=lambda x: json.loads(x.decode('utf-8')),
            auto_offset_reset='earliest',
            enable_auto_commit=False,
            group_id='file_processing_group'
        )
        logger.info(f"Connected to Kafka topic: {self.kafka_topic}")

    def download_file(self, download_url, file_path):
        """Download file from the provided URL"""
        try:
            response = requests.get(download_url, stream=True)
            response.raise_for_status()
            
            with open(file_path, 'wb') as file:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        file.write(chunk)
            return True
        except Exception as e:
            logger.error(f"Error downloading file: {str(e)}")
            return False

    def process_file(self, file_path, message):
        """Process the downloaded file"""
        try:
            # Get file extension
            _, ext = os.path.splitext(message['originalFileName'])
            
            # Create processed file path
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            processed_filename = f"processed_{message['fileId']}_{timestamp}{ext}"
            processed_path = os.path.join(self.processed_dir, processed_filename)
            
            # First, copy the file to processed directory
            with open(file_path, 'rb') as source, open(processed_path, 'wb') as dest:
                dest.write(source.read())
            
            # Now process the copied file
            doc_elements = self.document_processor.process_document(
                path=self.processed_dir,  # Pass the directory path
                file_name=processed_filename,  # Pass just the filename
                image_folder="figures"
            )

            success = self.document_processor.push_to_api(doc_elements=doc_elements)
            if success:
                logger.info("[Success]: Parsed document and fed to RAG Store")
            else:
                logger.error("[Fail]: Unable to parse document and feed to RAG Store")
            
            logger.info(f"File processed successfully: {processed_filename}")
            return True
        except Exception as e:
            logger.error(f"Error processing file: {str(e)}")
            return False
    
    def run(self):
        """Main processing loop"""
        try:
            logger.info("Starting file processing consumer...")
            for message in self.consumer:
                try:
                    value = message.value
                    logger.info(f"Received message: {value['fileId']}")
                    
                    # Create file path
                    file_name = value['originalFileName']
                    file_path = os.path.join(self.download_dir, file_name)
                    
                    # Download file
                    if self.download_file(value['downloadUrl'], file_path):
                        logger.info(f"File downloaded successfully: {file_name}")
                        
                        # Process file
                        if self.process_file(file_path, value):
                            # Clean up downloaded file
                            os.remove(file_path)
                            logger.info(f"Processed and cleaned up: {file_name}")
                            
                            # Commit the offset
                            self.consumer.commit()
                        else:
                            logger.error(f"Failed to process file: {file_name}")
                    else:
                        logger.error(f"Failed to download file: {file_name}")
                        
                except Exception as e:
                    logger.error(f"Error processing message: {str(e)}")
                    continue
                    
        except KeyboardInterrupt:
            logger.info("Shutting down consumer...")
        finally:
            self.cleanup()

    def cleanup(self):
        """Cleanup resources"""
        try:
            self.consumer.close()
            logger.info("Consumer closed successfully")
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")

if __name__ == "__main__":
    processor = FileProcessingPipeline()
    logger.info("Processing pipeline is up!")
    processor.run()