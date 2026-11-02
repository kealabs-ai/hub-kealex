class ActivityConsoleLogMiddleware:
    """Registra somente metadados HTTP, sem copiar conteúdo sensível."""

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

        response_status = None

        async def capture_send(message):
            nonlocal response_status
            if message["type"] == "http.response.start":
                response_status = message["status"]
            await send(message)

        method = scope.get("method", "")
        url = path
        print(f"[svc-activities][request] {method} {url}", flush=True)
        try:
            await self.application(scope, receive, capture_send)
        except Exception as exc:
            print(f"[svc-activities][error] {method} {url} {type(exc).__name__}", flush=True)
            raise
        print(f"[svc-activities][response] {method} {url} status={response_status}", flush=True)
