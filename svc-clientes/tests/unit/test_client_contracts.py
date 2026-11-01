import sys
import unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

SERVICE_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SERVICE_ROOT))

from app.api.schemas.client_schema import ClienteIn, ClienteUpdate
from app.application.use_cases.client_presenter import client_to_dict


class ClientSchemaTests(unittest.TestCase):
    def test_create_schema_accepts_optional_contact_data(self):
        client = ClienteIn.model_validate({"nome": "Cliente Exemplo", "email": "cliente@example.com"})
        self.assertEqual(client.email, "cliente@example.com")
        self.assertIsNone(client.cpfCnpj)

    def test_update_schema_keeps_camel_case_cpf_field(self):
        update = ClienteUpdate.model_validate({"id": "client-1", "cpfCnpj": "12345678901"})
        self.assertEqual(update.model_dump(exclude_none=True, exclude={"id"})["cpfCnpj"], "12345678901")


class ClientPresentationTests(unittest.TestCase):
    def test_response_keeps_camel_case_fields(self):
        now = datetime(2026, 11, 1, 12, 0, 0)
        client = SimpleNamespace(
            id="client-1", tenant_id="tenant-1", advogado_id="lawyer-1",
            nome="Cliente Exemplo", email="cliente@example.com", telefone=None,
            cpf_cnpj="12345678901", endereco=None, observacoes=None,
            created_at=now, updated_at=now,
        )
        result = client_to_dict(client)
        self.assertEqual(result["tenantId"], "tenant-1")
        self.assertEqual(result["advogadoId"], "lawyer-1")
        self.assertEqual(result["cpfCnpj"], "12345678901")
        self.assertIn("createdAt", result)
        self.assertNotIn("tenant_id", result)


if __name__ == "__main__":
    unittest.main()
