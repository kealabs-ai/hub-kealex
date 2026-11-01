from typing import Optional

from pydantic import BaseModel


class AgenteIACreate(BaseModel):
    nome: str
    descricao: Optional[str] = None
    provider: str
    api_key: str
    modelo: str
    max_tokens: int = 8192
    system_prompt: Optional[str] = None
    ativo: bool = True
    publico: bool = True

class AgenteIAUpdate(BaseModel):
    nome: Optional[str] = None
    descricao: Optional[str] = None
    provider: Optional[str] = None
    api_key: Optional[str] = None
    modelo: Optional[str] = None
    max_tokens: Optional[int] = None
    system_prompt: Optional[str] = None
    ativo: Optional[bool] = None
    publico: Optional[bool] = None

class PersonalAgentIn(BaseModel):
    nome: str
    descricao: Optional[str] = None
    provider: str
    modelo: str
    max_tokens: int = 4096
    system_prompt: Optional[str] = None
    ativo: bool = True

class AIPlanPolicyIn(BaseModel):
    can_create_agents: bool = False
    allowed_roles: list[str] = ["advogado"]
    max_agents: int = 0
    allowed_models: list[str] = []
    allowed_menus: list[str] = []
    monthly_token_limit: int = 0
    fallback_provider: Optional[str] = None
    fallback_model: Optional[str] = None

class AIUserPolicyIn(BaseModel):
    can_create_agents: Optional[bool] = None
    max_agents: Optional[int] = None
    allowed_models: Optional[list[str]] = None
    allowed_menus: Optional[list[str]] = None
    monthly_token_limit: Optional[int] = None
