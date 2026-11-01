from typing import Optional
from pydantic import BaseModel
from app.domain.entities.honorario_status import StatusEnum

class HonorarioIn(BaseModel):
    processoId:     str
    clienteId:      str
    descricao:      str = ""
    valorCentavos:  int
    dataVencimento: str
    escritorioId:   Optional[str] = None

class HonorarioGetIn(BaseModel):
    id: str

class HonorarioUpdate(BaseModel):
    id:             str
    descricao:      Optional[str]        = None
    valorCentavos:  Optional[int]        = None
    dataVencimento: Optional[str]        = None
    dataPagamento:  Optional[str]        = None
    status:         Optional[StatusEnum] = None

class HonorarioDeleteIn(BaseModel):
    id: str

