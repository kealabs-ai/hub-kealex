import os
import unittest
from base64 import b64encode

os.environ["KEALEX_DB_HOST"] = ""
os.environ["KEALEX_DB_NAME"] = ""
os.environ["KEALEX_DB_USER"] = ""
os.environ["KEALEX_DB_PASSWORD"] = ""
os.environ["KEALEX_DATABASE_URL"] = "sqlite:///./test_fiscalapi.db"
os.environ["KEALEX_SECRET_KEY"] = "fiscalapi-tests-secret"

import httpx
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.application.use_cases.fiscalapi_certificates import (
    build_provider_call,
    create_consultation,
    get_consultation,
    get_consultation_document,
)
from app.infrastructure.database.models import FiscalApiConsulta, FiscalApiDocumento
from app.infrastructure.fiscalapi_adapter import FiscalApiAdapter, FiscalApiError


class FiscalApiIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        FiscalApiConsulta.__table__.create(self.engine)
        FiscalApiDocumento.__table__.create(self.engine)
        self.session_factory = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)

    def tearDown(self):
        self.engine.dispose()

    def test_adapter_uses_official_endpoint_key_and_query(self):
        seen = {}

        def handler(request):
            seen["url"] = str(request.url)
            seen["key"] = request.headers.get("X-API-Key")
            return httpx.Response(200, json={"results": []})

        adapter = FiscalApiAdapter(api_key="fapi_mock_key", enabled=True, transport=httpx.MockTransport(handler))
        response = adapter.get("/api/consultar", {"uf": "SP", "cnpj": "11222333000181"})
        self.assertEqual(response, {"results": []})
        self.assertEqual(seen["url"], "https://api.fiscalapi.com.br/api/consultar?uf=SP&cnpj=11222333000181")
        self.assertEqual(seen["key"], "fapi_mock_key")

    def test_adapter_sanitizes_provider_authentication_failure(self):
        adapter = FiscalApiAdapter(
            api_key="fapi_mock_key",
            enabled=True,
            transport=httpx.MockTransport(lambda request: httpx.Response(401, json={"detail": "secret vendor data"})),
        )
        with self.assertRaises(FiscalApiError) as caught:
            adapter.get("/api/consultar-cnpj", {"cnpj": "11222333000181"})
        self.assertEqual(caught.exception.status_code, 503)
        self.assertNotIn("secret vendor data", caught.exception.message)

    def test_provider_call_validates_identifiers_and_uses_documented_routes(self):
        path, params, _, _ = build_provider_call("consulta-ie", {"uf": "sp", "cnpj": "11.222.333/0001-81"})
        self.assertEqual(path, "/api/consultar")
        self.assertEqual(params, {"uf": "SP", "cnpj": "11222333000181"})

        path, params, _, _ = build_provider_call("federais", {"tipo": "cndt", "cpf": "529.982.247-25"})
        self.assertEqual(path, "/api/consultar-cndt")
        self.assertEqual(params, {"cpf": "52998224725"})

        with self.assertRaises(HTTPException) as caught:
            build_provider_call("consulta-ie", {"uf": "SP", "cpf": "52998224725", "cnpj": "11222333000181"})
        self.assertEqual(caught.exception.status_code, 422)

        with self.assertRaises(HTTPException) as caught:
            build_provider_call("federais", {"tipo": "cndt", "cpf": "52998224725", "cnpj": "11222333000181"})
        self.assertEqual(caught.exception.status_code, 422)

    def test_idempotency_prevents_second_paid_provider_request(self):
        calls = []

        def handler(request):
            calls.append(request)
            return httpx.Response(200, json={"request_id": "provider-1", "uf": "SP", "results": []})

        adapter = FiscalApiAdapter(api_key="fapi_mock_key", enabled=True, transport=httpx.MockTransport(handler))
        with self.session_factory() as db:
            first = create_consultation(db, "tenant-1", "user-1", "consulta-ie", {"uf": "SP", "cnpj": "11222333000181"}, "once-1", adapter)
            duplicate = create_consultation(db, "tenant-1", "user-1", "consulta-ie", {"uf": "SP", "cnpj": "11222333000181"}, "once-1", adapter)
            self.assertEqual(len(calls), 1)
            self.assertEqual(first["metadata"]["status"], "SEM_RESULTADOS")
            self.assertEqual(first["metadata"]["request_id"], duplicate["metadata"]["request_id"])

    def test_pdf_is_encrypted_persisted_and_scoped_to_request_owner(self):
        pdf = b"%PDF-1.4\nMock certificate\n%%EOF"
        response_body = {"request_id": "provider-cndt-1", "result": {"status": "negativa", "pdf_base64": b64encode(pdf).decode()}}
        adapter = FiscalApiAdapter(
            api_key="fapi_mock_key",
            enabled=True,
            transport=httpx.MockTransport(lambda request: httpx.Response(200, json=response_body)),
        )
        with self.session_factory() as db:
            result = create_consultation(db, "tenant-1", "user-1", "federais", {"tipo": "cndt", "cpf": "52998224725"}, "pdf-1", adapter)
            self.assertTrue(result["metadata"]["document_available"])
            raw_saved = db.query(FiscalApiConsulta).filter_by(id=result["metadata"]["request_id"]).first()
            self.assertNotIn("pdf_base64", raw_saved.provider_response_json)
            stored_document = db.query(FiscalApiDocumento).filter_by(consultation_id=raw_saved.id).first()
            self.assertNotIn(pdf, stored_document.file_data)
            content, filename = get_consultation_document(db, "tenant-1", "user-1", raw_saved.id)
            self.assertEqual(content, pdf)
            self.assertTrue(filename.endswith(".pdf"))
            self.assertEqual(get_consultation(db, "tenant-1", "user-1", raw_saved.id)["data"]["status"], "negativa")
            with self.assertRaises(HTTPException) as caught:
                get_consultation_document(db, "tenant-1", "user-2", raw_saved.id)
            self.assertEqual(caught.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
