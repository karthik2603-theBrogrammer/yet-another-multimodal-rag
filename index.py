import os
import openai
import io
import uuid
import base64
import time 
from base64 import b64decode
import numpy as np
from PIL import Image
from pypdf import PdfReader

from unstructured.partition.pdf import partition_pdf

from langchain_community.chat_models import ChatOpenAI
from langchain.schema.messages import HumanMessage, SystemMessage
from langchain_community.vectorstores import Chroma
from langchain.storage import InMemoryStore
from langchain.schema.document import Document
from langchain_community.embeddings import OpenAIEmbeddings
from langchain.retrievers.multi_vector import MultiVectorRetriever
from langchain_community.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema.output_parser import StrOutputParser
from langchain.schema.runnable import RunnablePassthrough, RunnableLambda

from operator import itemgetter

print("Packages Ready! Setting up...")

def getText(filePath):
    """
    Reads and concatenates text from all pages of a PDF file.

    Args:
        filePath (str): Path to the PDF file.

    Returns:
        str: Combined text from all pages of the PDF.
    """
    try:
        # Create a PdfReader object
        reader = PdfReader(filePath)
        
        # Initialize an empty string to store all text
        all_text = ""
        
        # Iterate through all pages and extract text
        for page in reader.pages:
            all_text += page.extract_text() + "\n"  # Add newline between pages

        return all_text.strip()
    except FileNotFoundError:
        return f"Error: File not found at {filePath}"
    except Exception as e:
        return f"Error: Unable to read the PDF. Reason: {e}"
    

# load the pdf file to drive
# split the file to text, table and images
def doc_partition(path,file_name):
  raw_pdf_elements = partition_pdf(
    filename=path + file_name,
    extract_images_in_pdf=True,
    infer_table_structure=True,
    chunking_strategy="by_title",
    max_characters=4000,
    new_after_n_chars=3800,
    combine_text_under_n_chars=2000,
    image_output_dir_path=path
    )

  return raw_pdf_elements
path = "content/"
file_name = "book_with_images.pdf"
raw_pdf_elements = doc_partition(path,file_name)
print(raw_pdf_elements)



