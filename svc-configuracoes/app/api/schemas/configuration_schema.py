from typing import Optional

from pydantic import BaseModel


class GeralIn(BaseModel):
    nome_plataforma:  Optional[str]  = None
    url_base:         Optional[str]  = None
    email_suporte:    Optional[str]  = None
    descricao:        Optional[str]  = None
    fuso_horario:     Optional[str]  = None
    idioma:           Optional[str]  = None
    modo_manutencao:  Optional[bool] = None

class CdnIn(BaseModel):
    provider:          Optional[str]  = None
    bucket:            Optional[str]  = None
    region:            Optional[str]  = None
    access_key_id:     Optional[str]  = None
    secret_access_key: Optional[str]  = None
    cdn_url:           Optional[str]  = None
    tamanho_max_mb:    Optional[int]  = None
    tipos_permitidos:  Optional[str]  = None
    retencao_arquivo:  Optional[bool] = None
    retencao_delete:   Optional[bool] = None

class DatabaseIn(BaseModel):
    tipo:              Optional[str]  = None
    connection_string: Optional[str]  = None
    pool_size:         Optional[int]  = None
    timeout_segundos:  Optional[int]  = None
    ssl_enabled:       Optional[bool] = None
    query_logging:     Optional[bool] = None
    read_replicas:     Optional[bool] = None
    backup_frequencia: Optional[str]  = None
    backup_retencao:   Optional[int]  = None

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

class IaIn(BaseModel):
    provider:      Optional[str]  = None
    api_key:       Optional[str]  = None
    modelo:        Optional[str]  = None
    max_tokens:    Optional[int]  = None
    system_prompt: Optional[str]  = None
    ativo:         Optional[bool] = None

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

class UsuariosIn(BaseModel):
    max_tentativas_login: Optional[int]  = None
    bloqueio_minutos:     Optional[int]  = None
    senha_min_chars:      Optional[int]  = None
    senha_maiusculas:     Optional[bool] = None
    senha_numeros:        Optional[bool] = None
    senha_especiais:      Optional[bool] = None
    senha_expiracao_dias: Optional[int]  = None
    sessao_inativa_min:   Optional[int]  = None
    registro_modo:        Optional[str]  = None

class SegurancaIn(BaseModel):
    twofa_obrigatorio:   Optional[bool] = None
    oauth_google:        Optional[bool] = None
    oauth_microsoft:     Optional[bool] = None
    jwt_expiracao_horas: Optional[int]  = None
    log_acoes:           Optional[bool] = None
    log_documentos:      Optional[bool] = None
    alerta_suspeito:     Optional[bool] = None
    ips_bloqueados:      Optional[str]  = None
    lgpd_consentimento:  Optional[bool] = None
    lgpd_esquecimento:   Optional[bool] = None
    lgpd_exportacao:     Optional[bool] = None

class NotificacoesIn(BaseModel):
    email_provider:   Optional[str]  = None
    email_region:     Optional[str]  = None
    email_access_key: Optional[str]  = None
    email_secret_key: Optional[str]  = None
    email_remetente:  Optional[str]  = None
    notif_prazos:     Optional[bool] = None
    notif_honorarios: Optional[bool] = None
    notif_documentos: Optional[bool] = None
    notif_relatorio:  Optional[bool] = None
    notif_push:       Optional[str]  = None
    notif_sms:        Optional[str]  = None
