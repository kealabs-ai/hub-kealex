import json as _json
import urllib.error
import urllib.request
from typing import Optional

from fastapi import HTTPException


MODELOS_DISPONIVEIS = {
    "cerebras": ["llama-3.3-70b", "llama-3.1-70b", "llama-3.1-8b"],
    "groq": ["llama-3.3-70b-versatile", "llama-3.1-70b-versatile", "llama-3.1-8b-instant", "llama-3.2-90b-text-preview", "llama-3.2-11b-text-preview", "gemma2-9b-it"],
    "openai": ["gpt-5.5", "gpt-5.4", "gpt-5.4-mini", "gpt-5.4-nano"],
    "google": ["gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.5-flash", "gemini-3.5-flash-lite"],
    "claude": ["claude-opus-5", "claude-sonnet-5", "claude-opus-4-8", "claude-opus-4-7", "claude-sonnet-4-6", "claude-haiku-4-5-20251001"],
    "deepseek": ["deepseek-chat", "deepseek-reasoner"],
}

IA_DEFAULT_MODELS = {"cerebras": "llama-3.3-70b", "groq": "llama-3.3-70b-versatile", "openai": "gpt-5.5", "google": "gemini-3.8-flash", "claude": "claude-sonnet-5", "deepseek": "deepseek-chat"}

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
        raise HTTPException(400, f"O modelo '{model}' não corresponde ao fabricante '{provider}'.")

def _openai_response(api_key: str, model: str, system_prompt: str, messages: list[dict], max_tokens: int, endpoint_url: Optional[str]) -> str:
    base = (endpoint_url or "https://api.openai.com/v1").rstrip("/")
    if base != "https://api.openai.com/v1":
        raise HTTPException(400, "Use o endpoint oficial https://api.openai.com/v1 da OpenAI.")
    request = urllib.request.Request(
        f"{base}/responses",
        data=_json.dumps({"model": model, "instructions": system_prompt, "input": messages, "max_output_tokens": max_tokens}).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            result = _json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise HTTPException(502, f"A OpenAI respondeu com erro ({exc.code}): {detail[:1000]}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise HTTPException(502, "NÃ£o foi possÃ­vel conectar Ã  OpenAI.") from exc
    return result.get("output_text") or "".join(
        part.get("text", "") for item in result.get("output", [])
        for part in item.get("content", []) if part.get("type") == "output_text"
    )

def _provider_response(provider: str, api_key: str, model: str, system_prompt: str, messages: list[dict], max_tokens: int, endpoint_url: Optional[str] = None) -> str:
    if provider == "openai":
        return _openai_response(api_key, model, system_prompt, messages, max_tokens, endpoint_url)
    if provider == "claude":
        url = "https://api.anthropic.com/v1/messages"
        headers = {"x-api-key": api_key, "anthropic-version": "2023-06-01"}
        data = {"model": model, "max_tokens": max_tokens, "system": system_prompt, "messages": messages}
    elif provider == "google":
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        headers = {}
        data = {"systemInstruction": {"parts": [{"text": system_prompt}]}, "contents": [{"role": "model" if m["role"] == "assistant" else "user", "parts": [{"text": m["content"]}]} for m in messages], "generationConfig": {"maxOutputTokens": max_tokens}}
    else:
        base = {"groq": "https://api.groq.com/openai/v1", "cerebras": "https://api.cerebras.ai/v1", "deepseek": "https://api.deepseek.com"}.get(provider)
        if not base:
            raise HTTPException(400, "Fabricante de IA não suportado.")
        url, headers = f"{base}/chat/completions", {"Authorization": f"Bearer {api_key}"}
        data = {"model": model, "messages": [{"role": "system", "content": system_prompt}, *messages], "max_tokens": max_tokens}
    headers.update({"Content-Type": "application/json", "Accept": "application/json", "User-Agent": "Kealex-AI/1.0"})
    request = urllib.request.Request(url, data=_json.dumps(data).encode("utf-8"), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            result = _json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        if provider == "groq" and exc.code == 403 and "1010" in detail:
            raise HTTPException(502, "O acesso do servidor ao Groq foi bloqueado pelo Cloudflare (erro 1010). Confira as regras de segurança ou a rota de saída do servidor no provedor.") from exc
        raise HTTPException(502, f"{provider} respondeu com erro ({exc.code}): {detail[:1000]}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise HTTPException(502, f"Não foi possível conectar ao provedor {provider}.") from exc
    if provider == "claude":
        return "".join(part.get("text", "") for part in result.get("content", []))
    if provider == "google":
        return "".join(part.get("text", "") for part in result.get("candidates", [{}])[0].get("content", {}).get("parts", []))
    return result.get("choices", [{}])[0].get("message", {}).get("content", "")

__all__ = ["MODELOS_DISPONIVEIS", "IA_DEFAULT_MODELS", "_validate_model_provider", "_openai_response", "_provider_response"]
