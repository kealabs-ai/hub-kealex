import unittest
from fastapi import HTTPException
from app.api.routes.tracked_process_routes import _merge, _normalizar_cnj, _scope


class TrackedProcessTests(unittest.TestCase):
    def test_accepts_valid_formatted_cnj(self):
        self.assertEqual(_normalizar_cnj("0018063-19.2013.8.26.0002"), "00180631920138260002")

    def test_rejects_wrong_check_digit(self):
        with self.assertRaises(HTTPException) as error:
            _normalizar_cnj("0018063-18.2013.8.26.0002")
        self.assertEqual(error.exception.status_code, 422)

    def test_keeps_omitted_fields_and_movements(self):
        old = {"fontes": [{"sigla": "TJSP", "movimentacoes": [
            {"data": "2026-01-01", "nome": "Distribui??o"}]}]}
        new = {"fontes": [{"sigla": "TJSP", "capa": {"classe": "Procedimento"}}]}
        merged = _merge(old, new)
        self.assertEqual(merged["fontes"][0]["capa"]["classe"], "Procedimento")
        self.assertEqual(merged["fontes"][0]["movimentacoes"][0]["nome"], "Distribui??o")

    def test_lawyer_scope_is_user_and_other_roles_are_tenant(self):
        self.assertEqual(_scope({"role": "advogado", "tenant_id": "t1", "sub": "u1"}), "u1")
        self.assertEqual(_scope({"role": "escritorio", "tenant_id": "t1", "sub": "u1"}), "t1")


if __name__ == "__main__":
    unittest.main()
