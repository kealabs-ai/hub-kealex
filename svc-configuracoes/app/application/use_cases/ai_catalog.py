from fastapi import HTTPException

MODELOS_DISPONIVEIS = {
    "cerebras": [
        "llama-3.3-70b",
        "llama-3.1-70b",
        "llama-3.1-8b"
    ],
    "groq": [
        "llama-3.3-70b-versatile",
        "llama-3.1-70b-versatile", 
        "llama-3.1-8b-instant",
        "llama-3.2-90b-text-preview",
        "llama-3.2-11b-text-preview",
        "llama-3.2-3b-preview",
        "llama-3.2-1b-preview",
        "gemma2-9b-it",
        "gemma-7b-it"
    ],
    "openai": ["gpt-5.5", "gpt-5.4", "gpt-5.4-mini", "gpt-5.4-nano"],
    "google": ["gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.5-flash", "gemini-3.5-flash-lite"],
    "claude": ["claude-opus-5", "claude-sonnet-5", "claude-opus-4-8", "claude-opus-4-7", "claude-sonnet-4-6", "claude-haiku-4-5-20251001"],
    "deepseek": ["deepseek-chat", "deepseek-reasoner"],
}

IA_DEFAULT_MODELS = {
    "cerebras": "llama-3.3-70b", "groq": "llama-3.3-70b-versatile",
    "openai": "gpt-5.5", "google": "gemini-3.8-flash", "claude": "claude-sonnet-5", "deepseek": "deepseek-chat",
}

def _validate_model_provider(provider: str, model: str):
    name = (model or "").strip().lower()
    valid = {
        "openai": name.startswith(("gpt-", "o1-", "o3-", "o4-", "chatgpt-")),
        "claude": name.startswith("claude-"),
        "deepseek": name.startswith("deepseek-"),
        "google": name.startswith("gemini-"),
        "cerebras": bool(name) and not name.startswith(("gpt-", "o1-", "o3-", "o4-", "chatgpt-", "claude-", "gemini-", "deepseek-")),
        "groq": bool(name) and not name.startswith(("gpt-", "o1-", "o3-", "o4-", "chatgpt-", "claude-", "gemini-", "deepseek-")),
    }
    if provider not in valid or not valid[provider]:
        raise HTTPException(400, f"O modelo '{model}' nÃ£o corresponde ao fabricante '{provider}'.")

