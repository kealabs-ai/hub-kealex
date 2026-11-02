from typing import Optional

from pydantic import BaseModel

from app.domain.entities.repository_types import StatusEnum, TipoRepositorioEnum


class RepositorioIn(BaseModel):
    nome: str
    tipo: TipoRepositorioEnum
    url: Optional[str] = None
    caminhoLocal: Optional[str] = None
    gdriveFolder: Optional[str] = None
    descricao: Optional[str] = None


class RepositorioUpdate(BaseModel):
    id: str
    nome: Optional[str] = None
    status: Optional[StatusEnum] = None
    descricao: Optional[str] = None


class RepositorioGetIn(BaseModel):
    id: str


class RepositorioDeleteIn(BaseModel):
    id: str
