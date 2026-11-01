from typing import Optional
from pydantic import BaseModel
from app.domain.entities.document import TipoEnum, StatusEnum

class DocumentoIn(BaseModel):
    processoId:    str
    nome:          str
    tipo:          TipoEnum
    urlArquivo:    str
    tamanhoBytes:  int = 0
    escritorioId:  Optional[str] = None

class DocumentoGetIn(BaseModel):
    id: str

class DocumentoByProcessoIn(BaseModel):
    processoId: str

class DocumentoUpdate(BaseModel):
    id:         str
    nome:       Optional[str]        = None
    tipo:       Optional[TipoEnum]   = None
    status:     Optional[StatusEnum] = None
    urlArquivo: Optional[str]        = None

class DocumentoDeleteIn(BaseModel):
    id: str

