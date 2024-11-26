import os
import base64
import logging
import requests
import time
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from unstructured.partition.pdf import partition_pdf
from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class DocumentElements:
    texts: List[str]
    tables: List[str]
    table_summaries: List[str]
    image_base64: List[str]
    image_summaries: List[str]

class DocumentProcessor:
    def __init__(self, llm, api_base_url: str):
        self.llm = llm
        self.api_base_url = api_base_url

    def partition_document(self, path: str, file_name: str, image_folder: str) -> List:
        """
        Partition PDF document into elements using unstructured
        """
        try:
            raw_pdf_elements = partition_pdf(
                filename=os.path.join(path, file_name),
                chunking_strategy="by_title",
                max_characters=4000,
                new_after_n_chars=3800,
                combine_text_under_n_chars=2000,
                infer_table_structure=True,
                strategy='hi_res',
                extract_images_in_pdf=True,
                extract_image_block_output_dir= image_folder
            )
            logger.info(f'Successfully Split {file_name}')
            return raw_pdf_elements
        except Exception as e:
            logger.error(f"Error partitioning document: {str(e)}")
            raise

    def categorize_elements(self, raw_pdf_elements: List) -> Tuple[List[str], List[str]]:
        """
        Categorize PDF elements into tables and texts
        """
        tables = []
        texts = []
        for element in raw_pdf_elements:
            if "unstructured.documents.elements.Table" in str(type(element)):
                tables.append(str(element))
            elif "unstructured.documents.elements.CompositeElement" in str(type(element)):
                texts.append(str(element))
        return texts, tables

    def summarize_tables(self, tables: List[str], table_rate_limit: int = 10) -> List[str]:
        """
        Summarize tables using LLM
        """
        prompt_text = """You are an assistant tasked with summarizing tables. \
                        Give a concise summary of the table. Table chunk: {element}"""
        
        prompt = ChatPromptTemplate.from_template(prompt_text)
        summarize_chain = {"element": lambda x: x} | prompt | self.llm | StrOutputParser()
        
        table_summaries = []
        for idx, table in enumerate(tables, 1):
            logger.info(f"Table Being Summarized: {idx}. Sleeping for {table_rate_limit}s to avoid rate limiting...")
            try:
                summary = summarize_chain.invoke(table)
                table_summaries.append(summary)
                if idx < len(tables):  # Don't sleep after the last table
                    time.sleep(table_rate_limit)
            except Exception as e:
                logger.error(f"Error summarizing table {idx}: {str(e)}")
                table_summaries.append(f"Error summarizing table: {str(e)}")
        
        return table_summaries

    def process_images(self, image_folder: str, image_rate_limit: int = 60) -> Tuple[List[str], List[str]]:
        """
        Process and summarize images from the specified folder
        """
        def encode_image(image_path: str) -> str:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')

        prompt = "Describe the image in detail. Be specific about graphs, such as bar plots."
        img_base64_list = []
        image_summaries = []

        image_files = [f for f in sorted(os.listdir(image_folder)) 
                      if f.endswith(('.jpg', '.png'))]
        
        for idx, img_file in enumerate(image_files, 1):
            try:
                img_path = os.path.join(image_folder, img_file)
                base64_image = encode_image(img_path)
                img_base64_list.append(base64_image)
                
                message = HumanMessage(content=[
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                ])
                
                logger.info(f"Image Being Summarized: {idx}. Sleeping for {image_rate_limit}s to avoid rate limiting...")
                ai_msg = self.llm.invoke([message])
                image_summaries.append(ai_msg.content)
                
                if idx < len(image_files):  # Don't sleep after the last image
                    time.sleep(image_rate_limit)
                    
            except Exception as e:
                logger.error(f"Error processing image {img_file}: {str(e)}")
                image_summaries.append(f"Error processing image: {str(e)}")

        return img_base64_list, image_summaries

    def push_to_api(self, doc_elements: DocumentElements) -> bool:
        """
        Push processed document elements to API endpoints
        """
        try:
            if doc_elements.texts:
                response = requests.post(
                    f"{self.api_base_url}/api/insert-text",
                    json={"texts": doc_elements.texts}
                )
                if response.status_code != 200:
                    logger.error(f"Failed to insert texts: {response.text}")
                    return False


            if doc_elements.tables and doc_elements.table_summaries:
                response = requests.post(
                    f"{self.api_base_url}/api/insert-table",
                    json={
                        "tables": doc_elements.tables,
                        "table_summaries": doc_elements.table_summaries
                    }
                )
                if response.status_code != 200:
                    logger.error(f"Failed to insert tables: {response.text}")
                    return False


            if doc_elements.image_base64 and doc_elements.image_summaries:
                response = requests.post(
                    f"{self.api_base_url}/api/insert-image",
                    json={
                        "image_b64_list": doc_elements.image_base64,
                        "image_summaries": doc_elements.image_summaries
                    }
                )
                if response.status_code != 200:
                    logger.error(f"Failed to insert images: {response.text}")
                    return False

            logger.info("All data inserted successfully")
            return True

        except Exception as e:
            logger.error(f"Error pushing data to API: {str(e)}")
            return False

    def process_document(self, path: str, file_name: str, image_folder: str = 'figures') -> DocumentElements:
        """
        Main method to process a document end-to-end
        """
        raw_elements = self.partition_document(path, file_name, image_folder=image_folder)
        texts, tables = self.categorize_elements(raw_elements)
        table_summaries = self.summarize_tables(tables)
        img_base64_list, image_summaries = self.process_images(image_folder)
        return DocumentElements(
            texts=texts,
            tables=tables,
            table_summaries=table_summaries,
            image_base64=img_base64_list,
            image_summaries=image_summaries
        )