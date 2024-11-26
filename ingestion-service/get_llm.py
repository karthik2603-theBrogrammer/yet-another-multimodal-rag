from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

load_dotenv()

def get_llm(model_name="gemini-1.5-flash", temperature=0, max_tokens=None, timeout=None, max_retries=2):
    """Initialize and return the LLM."""
    return ChatGoogleGenerativeAI(
        model=model_name,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
        max_retries=max_retries,
    )