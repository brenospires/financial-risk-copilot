from langchain_ollama import ChatOllama

from config.settings import LLM_MODEL


def get_llm():
    return ChatOllama(
        model=LLM_MODEL,
        temperature=0
    )
