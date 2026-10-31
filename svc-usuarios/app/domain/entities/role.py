import enum

class RoleEnum(str, enum.Enum):
    admin    = "admin"
    escritorio = "escritorio"
    advogado = "advogado"
    juridico = "juridico"
    cliente  = "cliente"
