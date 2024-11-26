import base64
import os
import time
import requests
from unstructured.partition.pdf import partition_pdf
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema.output_parser import StrOutputParser
from langchain.schema.runnable import RunnablePassthrough, RunnableLambda
from langchain.schema.messages import HumanMessage, SystemMessage
from dotenv import load_dotenv


from get_llm import get_llm
from logger import logger

llm = get_llm()

def doc_partition(path,file_name):
  raw_pdf_elements = partition_pdf(
    filename=path + file_name,
    extract_images_in_pdf=True,
    infer_table_structure=True,
    chunking_strategy="by_title",
    max_characters=4000,
    new_after_n_chars=3800,
    combine_text_under_n_chars=2000,
    image_output_dir_path=path,
    strategy="hi_res",
    )

  return raw_pdf_elements

path = ""
file_name = "split.pdf"
raw_pdf_elements = doc_partition(path,file_name)
print(raw_pdf_elements)

logger.info(f'Successfully Split {file_name}')


# appending texts and tables from the pdf file
def data_category(raw_pdf_elements): # we may use decorator here
    tables = []
    texts = []
    for element in raw_pdf_elements:
        if "unstructured.documents.elements.Table" in str(type(element)):
           tables.append(str(element))
        elif "unstructured.documents.elements.CompositeElement" in str(type(element)):
           texts.append(str(element))
    data_category = [texts,tables]
    return data_category
texts = data_category(raw_pdf_elements)[0]
tables = data_category(raw_pdf_elements)[1]


# function to take tables as input and then summarize them
def tables_summarize(table_data, llm):
    prompt_text = """You are an assistant tasked with summarizing tables. \
                    Give a concise summary of the table. Table chunk: {element} """
    
    prompt = ChatPromptTemplate.from_template(prompt_text)
    summarize_chain = {"element": lambda x: x} | prompt | llm | StrOutputParser()
    
    table_summaries = []
    count = 0
    # Process each table one at a time
    for table in table_data:
        count += 1
        logger.info(f"Table Being Summarized: {count}. Sleeping for 60s to avoid rate limiting...")
        summary = summarize_chain.invoke(table)
        print(table)
        table_summaries.append(summary)
        print(summary)
        # time.sleep(30)  # Wait 30 seconds after each summary
        
    return table_summaries

## Now we have the table and text summaries, just have to process the images
table_summaries = tables_summarize(table_data= tables, llm= llm)
text_summaries = texts

logger.info("(Tables, Summaries) and Text Ready")


def encode_image(image_path):
    ''' Getting the base64 string '''
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')
    



def image_captioning(img_base64, prompt, llm):
    ''' Image summary '''
    message = HumanMessage(
    content=[
            {"type": "text", "text": prompt},
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{img_base64}"},
            },
        ]
    )
    ai_msg = llm.invoke([message])
    ai_msg.content
    print(ai_msg.content)
    return ai_msg.content


# Store base64 encoded images
img_base64_list = []

# Store image summaries
image_summaries = []

# Prompt : Our prompt here is customized to the type of images we have which is chart in our case
prompt = "Describe the image in detail. Be specific about graphs, such as bar plots."

# Read images, encode to base64 strings
image_path_folder = 'figures'
image_summarised_count = 0
for img_file in sorted(os.listdir(image_path_folder)):
    if img_file.endswith('.jpg') or img_file.endswith('.png'):
        img_path = os.path.join(image_path_folder, img_file)
        image_summarised_count += 1
        base64_image = encode_image(img_path)
        img_base64_list.append(base64_image)
        img_capt = image_captioning(base64_image,prompt, llm)
        logger.info(f"Image Being Summarized: {image_summarised_count}. Sleeping for 60s to avoid rate limiting...")
        image_summaries.append(img_capt)
        break
        
        time.sleep(60)

logger.info("(Image, Summary) ready")
logger.info("All Good, beginning data ingestion to vector and doc store...")



# texts, text_summaries, tables, table_summaries, img_base64_list, image_summaries
# ALL READY !


# Push data to API endpoints
API_BASE_URL = os.getenv("API_BASE_URL")
def push_to_api():
    try:
        # Push texts
        if texts:
            response = requests.post(
                f"{API_BASE_URL}/api/insert-text", 
                json={"texts": texts}  # Note the key name matching the Pydantic model
            )
            if response.status_code == 200:
                logger.info("Texts inserted successfully")
            else:
                logger.error(f"Failed to insert texts: {response.text}")

        # Push tables and their summaries
        if tables and table_summaries:
            response = requests.post(
                f"{API_BASE_URL}/api/insert-table", 
                json={
                    "tables": tables,
                    "table_summaries": table_summaries
                }
            )
            if response.status_code == 200:
                logger.info("Tables inserted successfully")
            else:
                logger.error(f"Failed to insert tables: {response.text}")

        # Push images and their summaries
        if img_base64_list and image_summaries:
            response = requests.post(
                f"{API_BASE_URL}/api/insert-image",
                json={
                    "image_b64_list": img_base64_list,
                    "image_summaries": image_summaries
                }
            )
            if response.status_code == 200:
                logger.info("Images inserted successfully")
            else:
                logger.error(f"Failed to insert images: {response.text}")

    except Exception as e:
        logger.error(f"Error pushing data to API: {str(e)}")
# Execute the data push
logger.info("Beginning data ingestion to vector and doc store...")
push_to_api()
logger.info("Data ingestion complete!")