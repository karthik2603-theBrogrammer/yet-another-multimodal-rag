from langchain_google_genai import ChatGoogleGenerativeAI

def get_llm(model_name="gemini-1.5-flash", temperature=0, max_tokens=None, timeout=None, max_retries=2, allow_streaming = True):
    """Initialize and return the LLM."""
    return ChatGoogleGenerativeAI(
        model=model_name,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
        max_retries=max_retries,
        streaming = allow_streaming
    )