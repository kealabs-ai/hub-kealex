import httpx


class EscavadorError(Exception):
    def __init__(self, status_code: int, code: str, message: str, retry_after: str | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.retry_after = retry_after


class EscavadorAdapter:
    """Cliente server-to-server para a API Escavador Business V2."""

    BASE_URL = "https://api.escavador.com"

    def __init__(self, token: str, enabled: bool = False, timeout: str | int | float = 30, transport: httpx.BaseTransport | None = None):
        self.token = token.strip()
        self.enabled = enabled
        self.transport = transport
        try:
            self.timeout = max(1.0, min(float(timeout), 120.0))
        except (TypeError, ValueError):
            self.timeout = 30.0

    def consultar_processo(self, numero_cnj: str) -> tuple[dict, str | None]:
        if not self.enabled:
            raise EscavadorError(503, "INTEGRACAO_DESABILITADA", "A integração Escavador está desabilitada no servidor.")
        if not self.token:
            raise EscavadorError(503, "CREDENCIAL_NAO_CONFIGURADA", "O token do Escavador não está configurado no servidor.")
        try:
            with httpx.Client(timeout=httpx.Timeout(self.timeout, connect=min(self.timeout, 5.0)), follow_redirects=False, transport=self.transport) as client:
                response = client.get(
                    f"{self.BASE_URL}/api/v2/processos/numero_cnj/{numero_cnj}",
                    headers={"Authorization": f"Bearer {self.token}", "Accept": "application/json"},
                )
        except httpx.TimeoutException as exc:
            raise EscavadorError(504, "TEMPO_LIMITE_FORNECEDOR", "O Escavador demorou demais para responder.") from exc
        except httpx.RequestError as exc:
            raise EscavadorError(502, "FALHA_COMUNICACAO_FORNECEDOR", "Não foi possível conectar à API do Escavador.") from exc

        if response.status_code == 401 or response.status_code == 403:
            raise EscavadorError(503, "CREDENCIAL_FORNECEDOR_INVALIDA", "O Escavador recusou o token configurado.")
        if response.status_code == 402:
            raise EscavadorError(402, "CREDITOS_INSUFICIENTES", "A conta Escavador está sem créditos para esta consulta.")
        if response.status_code == 404:
            raise EscavadorError(404, "PROCESSO_NAO_ENCONTRADO", "Nenhum processo foi encontrado para o número informado.")
        if response.status_code == 429:
            raise EscavadorError(429, "LIMITE_FORNECEDOR", "O limite de consultas do Escavador foi atingido.", response.headers.get("Retry-After"))
        if response.status_code == 422:
            raise EscavadorError(422, "PARAMETROS_RECUSADOS", "O Escavador recusou o número CNJ informado.")
        if response.status_code >= 500:
            raise EscavadorError(503, "SERVICO_FORNECEDOR_INDISPONIVEL", "O Escavador está temporariamente indisponível.")
        if response.status_code < 200 or response.status_code >= 300:
            raise EscavadorError(502, "RESPOSTA_FORNECEDOR_INVALIDA", "O Escavador retornou uma resposta inesperada.")
        try:
            body = response.json()
        except ValueError as exc:
            raise EscavadorError(502, "RESPOSTA_FORNECEDOR_INVALIDA", "O Escavador retornou um JSON inválido.") from exc
        if not isinstance(body, dict):
            raise EscavadorError(502, "RESPOSTA_FORNECEDOR_INVALIDA", "O Escavador retornou um formato inesperado.")
        return body, response.headers.get("Creditos-Utilizados")