from langchain_ollama import ChatOllama
from config.settings import LLM_MODEL
import requests

def get_llm():
    return ChatOllama(model=LLM_MODEL, temperature=0)

def get_ollama_context_length(model: str = "qwen3:8b") -> int | None:
    response = requests.post(
        "http://localhost:11434/api/show",
        json={"model": model},
        timeout=10,
    )

    response.raise_for_status()
    data = response.json()

    model_info = data.get("model_info", {})

    return (
        model_info.get("qwen3.context_length")
        or model_info.get("general.context_length")
    )
