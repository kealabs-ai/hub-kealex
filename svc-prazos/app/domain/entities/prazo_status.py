import enum

class StatusEnum(str, enum.Enum):
    pendente  = "pendente"
    concluido = "concluido"
    vencido   = "vencido"

