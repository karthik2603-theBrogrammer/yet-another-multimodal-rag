import base64
from langchain_core.documents import Document
from langchain.schema.messages import HumanMessage, SystemMessage
from langchain.prompts import ChatPromptTemplate
from logger import logger


def encode_image(image_path):
    """Encode an image to base64."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def split_image_text_types(docs):
    """Split base64-encoded images and texts."""
    b64, text = [], []
    for doc in docs:
        try:
            base64.b64decode(doc)
            b64.append(doc)
        except Exception:
            text.append(doc)
    return {"images": b64, "texts": text}

def prompt_func(inputs: dict, debug: bool) -> str:
    """Create a prompt that incorporates context, chat history, and the current question."""
    if debug:
        print(dict)
    # Extract inputs
    context = inputs["context"]
    question = inputs["question"]
    chat_history = inputs.get("chat_history", [])
    
    # Split context types if they exist
    text_content = context.get("texts", "No relevant text content found")
    table_content = context.get("tables", "No relevant table content found")
    image_content = context.get("images", "No relevant image content found")
    
    # Format chat history
    history_str = ""
    if chat_history:
        history_str = "\nPrevious conversation:\n"
        for msg in chat_history:
            role = "Human" if isinstance(msg, HumanMessage) else "Assistant"
            history_str += f"{role}: {msg.content}\n"
    
    # Create the prompt template
    template = ChatPromptTemplate.from_messages([
        ("system", """You are a helpful AI assistant. You have access to texts, tables, and images. 
                     Answer questions based on this context and previous conversation history. 
                     If you cannot find the relevant information in the provided context, say so.
                     When referencing images, tables, or text, be specific about which source you're using."""),
        ("user", f"""Here is the available context:

                    Text Content:
                    {text_content}

                    Table Content:
                    {table_content}

                    Image Content:
                    {image_content}
                    
                    {history_str}
                    Current Question: {question}
                    
                    Please provide a clear and specific answer based on the above context and conversation history.
                    If you reference any specific piece of content, indicate which source you're using.""")
    ])
    
    if debug:
        logger.info(f"Context - Text: {(text_content)}, Tables: {(table_content)}, Images: {(image_content)}")
        logger.info(f"Chat History Present: {(chat_history)}")
        logger.info(f"Question: {question}")
    
    return template