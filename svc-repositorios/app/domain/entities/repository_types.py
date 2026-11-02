import enum


class TipoRepositorioEnum(str, enum.Enum):
    local = "local"
    cdn = "cdn"
    gdrive = "gdrive"


class StatusEnum(str, enum.Enum):
    ativo = "ativo"
    inativo = "inativo"
    erro = "erro"
