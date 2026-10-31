import sys
import unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

SERVICE_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SERVICE_ROOT))

from app.api.schemas.user_schema import UsuarioUpdate
from app.application.use_cases.user_presenter import public_key_to_dict, user_to_dict


class UserSchemaTests(unittest.TestCase):
    def test_update_schema_keeps_clear_office_contract(self):
        update = UsuarioUpdate.model_validate({"id": "user-1", "clearEscritorio": True})
        self.assertTrue(update.clearEscritorio)
        self.assertEqual(update.model_dump(exclude_unset=True)["clearEscritorio"], True)


class UserPresentationTests(unittest.TestCase):
    def test_user_response_keeps_camel_case_contract(self):
        now = datetime(2026, 10, 31, 12, 0, 0)
        user = SimpleNamespace(
            id="user-1", tenant_id="tenant-1", escritorio_id=None, codigo=None,
            nome="Usuário Teste", email="user@example.com", role="advogado",
            ativo=True, oab=None, created_at=now, updated_at=now,
        )
        result = user_to_dict(user, db=None)
        self.assertEqual(result["tenantId"], "tenant-1")
        self.assertEqual(result["modalidade"], "autonomo")
        self.assertIn("createdAt", result)
        self.assertNotIn("tenant_id", result)

    def test_public_key_response_keeps_camel_case_contract(self):
        now = datetime(2026, 10, 31, 12, 0, 0)
        key = SimpleNamespace(
            id="key-1", user_id="user-1", orgao="Tribunais Superiores",
            chave_publica="key", created_at=now, updated_at=now,
        )
        result = public_key_to_dict(key)
        self.assertEqual(result["userId"], "user-1")
        self.assertEqual(result["chavePublica"], "key")
        self.assertIn("updatedAt", result)


if __name__ == "__main__":
    unittest.main()
