import enum

class TipoEnum(str, enum.Enum):
    peticao     = "peticao"
    contrato    = "contrato"
    comprovante = "comprovante"
    outro       = "outro"

class StatusEnum(str, enum.Enum):
    pendente  = "pendente"
    aprovado  = "aprovado"
    rejeitado = "rejeitado"

