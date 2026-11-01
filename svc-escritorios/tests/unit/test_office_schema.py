import unittest

from app.api.schemas.office_schema import EscritorioIn, MembroIn


class OfficeSchemaTests(unittest.TestCase):
    def test_create_schema_keeps_legacy_field_names_and_defaults(self):
        office = EscritorioIn.model_validate({"nome": "Kealex"})

        self.assertEqual(office.nome, "Kealex")
        self.assertEqual(office.limiteAdvogados, 3)
        self.assertIsNone(office.emailAcesso)

    def test_member_schema_supports_disassociation(self):
        member = MembroIn.model_validate({"usuarioId": "user-1"})

        self.assertEqual(member.usuarioId, "user-1")
        self.assertIsNone(member.escritorioId)
