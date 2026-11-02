from datetime import date
from typing import List, Literal, Optional

from pydantic import BaseModel, EmailStr, Field

from app.domain.entities.enums import StatusEnum


class LoginIn(BaseModel):
    email: EmailStr
    senha: str

class RegisterIn(BaseModel):
    nome:     str
    email:    EmailStr
    cpfCnpj:  str = ""
    whatsapp: str
    senha:    str
    perfil:   str = "advogado"

class AuthUser(BaseModel):
    id:             str
    nome:           str
    email:          str
    role:           str
    tenantId:       str
    accessToken:    str
    plano:          str           = "trial"
    subscriptionStatus: str | None = None
    trialStartedAt: str | None    = None
    trialExpiresAt: str | None    = None
    subscriptionExpiresAt: str | None = None

class ProcessoIn(BaseModel):
    numero: str
    titulo: str
    descricao: str = ""
    clienteId: str
    vara: str = ""
    tribunal: str = ""
    escritorioId: Optional[str] = None

class ProcessoGetIn(BaseModel):
    id: str

class ProcessoUpdate(BaseModel):
    id: str
    numero: Optional[str] = None
    titulo: Optional[str] = None
    descricao: Optional[str] = None
    status: Optional[StatusEnum] = None
    vara: Optional[str] = None
    tribunal: Optional[str] = None

class ProcessoDeleteIn(BaseModel):
    id: str

class AudienciaIn(BaseModel):
    processoId: str = ""
    processoTitulo: str = ""
    tipo: str = ""
    dataHora: str = ""
    local: str = ""
    juiz: str | None = None
    partes: str | None = None
    observacoes: str | None = None
    roteiro: str | None = None
    status: str = "agendada"

class AudienciaUpdateIn(AudienciaIn):
    id: str

class IntimacaoIn(BaseModel):
    processoId: Optional[str] = None
    processoNumero: Optional[str] = Field(default=None, max_length=50)
    processoTitulo: Optional[str] = Field(default=None, max_length=255)
    diario: str = Field(min_length=1, max_length=255)
    dataPublicacao: str = Field(min_length=1, max_length=40)
    conteudo: str
    resumoIA: Optional[str] = None
    prazoCalculado: Optional[str] = Field(default=None, max_length=40)
    status: Literal["nova", "lida", "respondida", "ignorada"] = "nova"

class IntimacaoUpdateIn(BaseModel):
    processoId: Optional[str] = None
    processoNumero: Optional[str] = Field(default=None, max_length=50)
    processoTitulo: Optional[str] = Field(default=None, max_length=255)
    diario: Optional[str] = Field(default=None, min_length=1, max_length=255)
    dataPublicacao: Optional[str] = Field(default=None, min_length=1, max_length=40)
    conteudo: Optional[str] = None
    resumoIA: Optional[str] = None
    prazoCalculado: Optional[str] = Field(default=None, max_length=40)
    status: Optional[Literal["nova", "lida", "respondida", "ignorada"]] = None

class IaIn(BaseModel):
    provider: Optional[str] = None
    api_key: Optional[str] = None
    modelo: Optional[str] = None
    max_tokens: Optional[int] = None
    system_prompt: Optional[str] = None
    ativo: Optional[bool] = None

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

class CreditCardIn(BaseModel):
    holderName: str; number: str; expiryMonth: str; expiryYear: str; ccv: str

class HolderInfoIn(BaseModel):
    name: str; email: str; cpfCnpj: str; postalCode: str; addressNumber: str
    addressComplement: str | None = None; phone: str | None = None; mobilePhone: str | None = None
    address: str | None = None; neighborhood: str | None = None; city: str | None = None; state: str | None = None

class AssinarIn(BaseModel):
    plano: str; asaasCustomerId: str; periodicidade: str = "mensal"
    creditCard: CreditCardIn; holderInfo: HolderInfoIn; remoteIp: str = "127.0.0.1"

class AssinarOut(BaseModel):
    subscriptionId: str; plano: str; periodicidade: str; status: str
    nextDueDate: str; value: float; valorMensal: float; desconto: float

class AssinarPreviewOut(BaseModel):
    plano: str; descricaoPlano: str; periodicidade: str
    valorMensal: float; valorTotal: float; desconto: float
    nextDueDate: str
    titular: str; email: str; cpfCnpj: str
    cartaoFinal: str  # últimos 4 dígitos
    mensagem: str

class AssinarPixIn(BaseModel):
    plano: str; asaasCustomerId: str; periodicidade: str = "mensal"

class AssinarPixOut(BaseModel):
    subscriptionId: str; plano: str; periodicidade: str; status: str
    nextDueDate: str; value: float; valorMensal: float; desconto: float
    pixQrCode: str; pixKey: str; pixExpiresAt: str

class PreRegisterIn(BaseModel):
    nome: str; email: EmailStr; senha: str

class PreRegisterOut(BaseModel):
    userId: str; tenantId: str; token: str

class ActivityCreateIn(BaseModel):
    title: str = Field(min_length=1, max_length=180)
    description: str = Field(default="", max_length=5000)
    status: str = Field(default="todo", min_length=1, max_length=36)
    priority: str = "media"
    dueDate: date | None = None

class ActivityUpdateIn(BaseModel):
    id: str
    title: str | None = Field(default=None, min_length=1, max_length=180)
    description: str | None = Field(default=None, max_length=5000)
    status: str | None = Field(default=None, min_length=1, max_length=36)
    priority: str | None = None
    dueDate: date | None = None

class ActivityColumnCreateIn(BaseModel):
    title: str = Field(min_length=1, max_length=80)
    color: str = Field(default="#087E96", pattern=r"^#[0-9A-Fa-f]{6}$")

class ActivityColumnUpdateIn(BaseModel):
    id: str
    title: str | None = Field(default=None, min_length=1, max_length=80)
    color: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")

class ActivityIdIn(BaseModel):
    id: str

class UserApiKeyCreate(BaseModel):
    provider: str
    model: str
    api_key: str
    is_active: bool = True

class UserApiKeyUpdate(BaseModel):
    provider: Optional[str] = None
    model: Optional[str] = None
    api_key: Optional[str] = None
    is_active: Optional[bool] = None

class ChavePublicaIn(BaseModel):
    orgao: str
    chavePublica: str

class IaProviderIn(BaseModel):
    api_key: Optional[str] = None
    endpoint_url: Optional[str] = None
    modelo: Optional[str] = None
    max_tokens: Optional[int] = None
    system_prompt: Optional[str] = None
    ativo: Optional[bool] = None

class IaChatMessage(BaseModel):
    role: str
    content: str

class IaChatIn(BaseModel):
    messages: list[IaChatMessage]
    agente_id: Optional[str] = None

class AIPlanPolicyIn(BaseModel):
    can_create_agents: bool = False
    allowed_roles: list[str] = Field(default_factory=lambda: ["advogado"])
    max_agents: int = 0
    allowed_models: list[str] = Field(default_factory=list)
    allowed_menus: list[str] = Field(default_factory=list)
    monthly_token_limit: int = 0
    fallback_provider: Optional[str] = None
    fallback_model: Optional[str] = None

class AIUserPolicyIn(BaseModel):
    can_create_agents: Optional[bool] = None
    max_agents: Optional[int] = None
    allowed_models: Optional[list[str]] = None
    allowed_menus: Optional[list[str]] = None
    monthly_token_limit: Optional[int] = None

class _CreditCardIn(BaseModel):
    holderName: str; number: str; expiryMonth: str; expiryYear: str; ccv: str

class _CreditCardHolderInfoIn(BaseModel):
    name: str; email: str; cpfCnpj: str; postalCode: str; addressNumber: str
    phone: Optional[str] = None; mobilePhone: Optional[str] = None

class PagamentoIn(BaseModel):
    cobrancaId: str
    billingType: str
    customer: str
    description: Optional[str] = None
    creditCardToken: Optional[str] = None
    creditCard: Optional[_CreditCardIn] = None
    creditCardHolderInfo: Optional[_CreditCardHolderInfoIn] = None
    remoteIp: str = "127.0.0.1"


__all__ = [name for name in globals() if not name.startswith("__")]
