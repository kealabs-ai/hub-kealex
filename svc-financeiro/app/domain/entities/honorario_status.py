import enum

class StatusEnum(str, enum.Enum):
    pendente  = "pendente"
    pago      = "pago"
    vencido   = "vencido"
    cancelado = "cancelado"

