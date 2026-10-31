import json

class ActivityConsoleLogMiddleware:
    """Registra o JSON recebido e a resposta das rotas de activities no stdout."""

    _ACTIVITY_PREFIXES = (
        "/activities",
        "/api/activities",
        "/k1/lex/activities",
        "/v1/lex/activities",
    )

    def __init__(self, app):
        self.application = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.application(scope, receive, send)
            return

        path = scope.get("path", "")
        if not any(path == prefix or path.startswith(prefix + "/") for prefix in self._ACTIVITY_PREFIXES):
            await self.application(scope, receive, send)
            return

        request_messages = []
        request_body = bytearray()
        while True:
            message = await receive()
            request_messages.append(message)
            if message["type"] == "http.request":
                request_body.extend(message.get("body", b""))
                if not message.get("more_body", False):
                    break
            elif message["type"] == "http.disconnect":
                break

        async def replay_receive():
            if request_messages:
                return request_messages.pop(0)
            return await receive()

        response_status = None
        response_body = bytearray()

        async def capture_send(message):
            nonlocal response_status
            if message["type"] == "http.response.start":
                response_status = message["status"]
            elif message["type"] == "http.response.body":
                response_body.extend(message.get("body", b""))
            await send(message)

        def _display_json(raw: bytes):
            if not raw:
                return "<empty>"
            try:
                return json.dumps(json.loads(raw), ensure_ascii=False, default=str)
            except (json.JSONDecodeError, UnicodeDecodeError):
                return raw.decode("utf-8", errors="replace")

        method = scope.get("method", "")
        query = scope.get("query_string", b"").decode("latin-1")
        url = path + (f"?{query}" if query else "")
        print(f"[svc-activities][request] {method} {url} json={_display_json(bytes(request_body))}", flush=True)
        try:
            await self.application(scope, replay_receive, capture_send)
        except Exception as exc:
            print(f"[svc-activities][error] {method} {url} {type(exc).__name__}: {exc}", flush=True)
            raise
        print(
            f"[svc-activities][response] {method} {url} status={response_status} body={_display_json(bytes(response_body))}",
            flush=True,
        )
