import unittest

from app.api.schemas.cobranca_schema import CobrancaIn, PagamentoIn


class CobrancaSchemaTests(unittest.TestCase):
    def test_create_charge_schema_preserves_api_field_names(self):
        charge = CobrancaIn.model_validate(
            {"processoId": "process-1", "clienteId": "client-1", "valorCentavos": 1250}
        )

        self.assertEqual(charge.processoId, "process-1")
        self.assertEqual(charge.valorCentavos, 1250)
        self.assertIsNone(charge.dataVencimento)

    def test_payment_schema_accepts_pix_and_customer_fields(self):
        payment = PagamentoIn.model_validate(
            {"cobrancaId": "charge-1", "customer": "cus_1", "billingType": "PIX"}
        )

        self.assertEqual(payment.cobrancaId, "charge-1")
        self.assertEqual(payment.billingType, "PIX")
