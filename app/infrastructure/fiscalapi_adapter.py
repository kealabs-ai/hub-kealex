from urllib.parse import urlsplit

import httpx

from app.core.config import (
    FISCALAPI_API_KEY,
    FISCALAPI_BASE_URL,
    FISCALAPI_ENABLED,
    FISCALAPI_TIMEOUT,
)


class FiscalApiError(Exception):
    def __init__(self, status_code: int, code: str, message: str, retry_after: str | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.retry_after = retry_after


class FiscalApiAdapter:
    """Adapter HTTP isolado para a API oficial FiscalAPI."""

    def __init__(
        self,
        base_url: str = FISCALAPI_BASE_URL,
        api_key: str = FISCALAPI_API_KEY,
        timeout: str | int | float = FISCALAPI_TIMEOUT,
        enabled: bool = FISCALAPI_ENABLED,
        transport: httpx.BaseTransport | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key.strip()
        self.enabled = enabled
        self.transport = transport
        try:
            self.timeout = max(1.0, min(float(timeout), 120.0))
        except (TypeError, ValueError):
            self.timeout = 30.0

    def get(self, path: str, params: dict) -> dict:
        if not self.enabled:
            raise FiscalApiError(503, "INTEGRACAO_DESABILITADA", "A integração FiscalAPI está desabilitada.")
        if not self.api_key:
            raise FiscalApiError(503, "CREDENCIAL_NAO_CONFIGURADA", "A chave da FiscalAPI não está configurada no servidor.")

        base = urlsplit(self.base_url)
        if base.scheme != "https" or base.hostname != "api.fiscalapi.com.br" or base.username or base.password:
            raise FiscalApiError(503, "CONFIGURACAO_INVALIDA", "A URL configurada para a FiscalAPI não é permitida.")
        if not path.startswith("/api/") or ".." in path:
            raise FiscalApiError(500, "ROTA_EXTERNA_INVALIDA", "A operação FiscalAPI não está configurada.")

        try:
            with httpx.Client(
                timeout=httpx.Timeout(self.timeout, connect=min(self.timeout, 5.0)),
                follow_redirects=False,
                transport=self.transport,
            ) as client:
                response = client.get(
                    f"{self.base_url}{path}",
                    params=params,
                    headers={"X-API-Key": self.api_key, "Accept": "application/json"},
                )
        except httpx.TimeoutException as exc:
            raise FiscalApiError(504, "TEMPO_LIMITE_FORNECEDOR", "A FiscalAPI demorou demais para responder.") from exc
        except httpx.RequestError as exc:
            raise FiscalApiError(502, "FALHA_COMUNICACAO_FORNECEDOR", "Não foi possível conectar à FiscalAPI.") from exc

        if response.status_code == 429:
            raise FiscalApiError(429, "LIMITE_FORNECEDOR", "O limite temporário da FiscalAPI foi atingido.", response.headers.get("Retry-After"))
        if response.status_code in (401, 403):
            raise FiscalApiError(503, "CREDENCIAL_FORNECEDOR_INVALIDA", "A FiscalAPI recusou as credenciais configuradas.")
        if response.status_code == 402:
            raise FiscalApiError(503, "LIMITE_CONTRATUAL_FORNECEDOR", "A conta FiscalAPI não tem consultas disponíveis.")
        if response.status_code == 404:
            raise FiscalApiError(404, "REGISTRO_NAO_ENCONTRADO", "A FiscalAPI não encontrou registros para os dados informados.")
        if response.status_code == 400:
            raise FiscalApiError(422, "PARAMETROS_RECUSADOS_FORNECEDOR", "A FiscalAPI recusou os parâmetros da consulta.")
        if response.status_code >= 500:
            raise FiscalApiError(503, "SERVICO_FORNECEDOR_INDISPONIVEL", "O serviço FiscalAPI está temporariamente indisponível.")
        if response.status_code < 200 or response.status_code >= 300:
            raise FiscalApiError(502, "RESPOSTA_FORNECEDOR_INVALIDA", "A FiscalAPI retornou uma resposta inesperada.")
        try:
            body = response.json()
        except ValueError as exc:
            raise FiscalApiError(502, "RESPOSTA_FORNECEDOR_INVALIDA", "A FiscalAPI retornou um JSON inválido.") from exc
        if not isinstance(body, dict):
            raise FiscalApiError(502, "RESPOSTA_FORNECEDOR_INVALIDA", "A FiscalAPI retornou um formato inesperado.")
        return body
