from app.domain.entities.honorario_status import StatusEnum


def calculate_totals(rows):
    return {
        "totalPendente": sum(row.valor_centavos for row in rows if row.status == StatusEnum.pendente),
        "totalPago": sum(row.valor_centavos for row in rows if row.status == StatusEnum.pago),
        "totalVencido": sum(row.valor_centavos for row in rows if row.status == StatusEnum.vencido),
        "totalGeral": sum(row.valor_centavos for row in rows),
    }
