import enum

class StatusEnum(str, enum.Enum):
    ativo     = "ativo"
    arquivado = "arquivado"
    encerrado = "encerrado"

