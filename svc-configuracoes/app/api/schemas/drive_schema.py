from typing import Optional

from pydantic import BaseModel


class DriveSourceCreate(BaseModel):
    pasta_id: str
    nome_pasta: str
    service_account: str
    agente_id: Optional[str] = None

class DriveSourceUpdate(BaseModel):
    nome_pasta: Optional[str] = None
    agente_id: Optional[str] = None
    ativo: Optional[bool] = None
