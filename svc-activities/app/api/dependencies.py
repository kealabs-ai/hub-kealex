from fastapi import HTTPException

def get_activity_owner(token: dict):
    user_id, tenant_id = token.get("sub"), token.get("tenant_id")
    if not user_id or not tenant_id:
        raise HTTPException(401, "Token sem usuário ou escritório associado")
    return str(user_id), str(tenant_id)
