class TenantAccessDenied(Exception):
    """Raised when a tenant cannot access the authenticated platform area."""

    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(detail)
