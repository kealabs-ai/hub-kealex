import unittest

from app.api.schemas.document_schema import DocumentoIn
from app.domain.entities.document import TipoEnum


class DocumentSchemaTests(unittest.TestCase):
    def test_schema_preserves_camel_case_contract(self):
        document = DocumentoIn.model_validate(
            {"processoId": "process-1", "nome": "peticao.pdf", "tipo": "peticao", "urlArquivo": "https://example.test/file.pdf"}
        )

        self.assertEqual(document.processoId, "process-1")
        self.assertEqual(document.tipo, TipoEnum.peticao)
        self.assertEqual(document.tamanhoBytes, 0)
