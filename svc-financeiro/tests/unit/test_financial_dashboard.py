import unittest
from types import SimpleNamespace

from app.application.use_cases.financial_dashboard import calculate_totals
from app.domain.entities.honorario_status import StatusEnum


class FinancialDashboardTests(unittest.TestCase):
    def test_calculates_totals_by_status_and_overall(self):
        rows = [
            SimpleNamespace(valor_centavos=1000, status=StatusEnum.pendente),
            SimpleNamespace(valor_centavos=2500, status=StatusEnum.pago),
            SimpleNamespace(valor_centavos=500, status=StatusEnum.vencido),
        ]

        self.assertEqual(
            calculate_totals(rows),
            {"totalPendente": 1000, "totalPago": 2500, "totalVencido": 500, "totalGeral": 4000},
        )
