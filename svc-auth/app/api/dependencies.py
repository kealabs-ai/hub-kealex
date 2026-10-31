from datetime import datetime
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from app.infrastructure.database.models.auth_models import Tenant
from app.infrastructure.database.session import get_db
from app.infrastructure.security.jwt_provider import verify_token
from app.application.use_cases.check_tenant_access import check_tenant_access, TenantAccessDenied


def require_active_trial(payload=Depends(verify_token), db: Session = Depends(get_db)):
    tenant_id = payload.get("tenant_id")
    role = payload.get("role", "")
    tenant = db.query(Tenant).filter_by(id=tenant_id).first() if tenant_id else None
    try:
        check_tenant_access(tenant, role)
    except TenantAccessDenied as error:
        raise HTTPException(403, str(error)) from error
    return payload
