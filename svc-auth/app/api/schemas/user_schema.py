from pydantic import BaseModel

class AuthUser(BaseModel):
    id:                 str
    nome:               str
    email:              str
    role:               str
    tenantId:           str
    accessToken:        str
    plano:              str
    subscriptionStatus: str | None = None
    tenantAtivo:        bool = True
    trialStartedAt:     str | None = None
    trialExpiresAt:     str | None = None
    subscriptionExpiresAt: str | None = None
    escritorioId:       str | None = None
    codigoEscritorio:    str | None = None
    escritorioNome:      str | None = None
    modalidade:         str | None = None  # autonomo | escritorio

# ── Endpoints ─────────────────────────────────────────────────────────────────
