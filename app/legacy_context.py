import os, re, uuid, enum, logging, base64, hashlib
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta
from typing import Optional, List, Literal
from urllib.parse import quote_plus
from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field
import bcrypt
from jose import jwt, JWTError
from sqlalchemy import create_engine, Column, String, Boolean, Date, DateTime, Enum as SAEnum, Index, PrimaryKeyConstraint, Text, Integer, Numeric, ForeignKey, UniqueConstraint
from sqlalchemy import text as sql_text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from cryptography.fernet import Fernet, InvalidToken

# Carregar variáveis de ambiente
from dotenv import load_dotenv
load_dotenv()
from app.core.config import *
from app.infrastructure.database.models import *
from app.api.schemas.schemas import *
from app.infrastructure.database.session import *
from app.infrastructure.security.password_hasher import _hash, _verify
from app.infrastructure.security.jwt_provider import _make_token, verify_identity_token, verify_token
from app.api.dependencies import _require_admin
from app.application.use_cases.serialization import *
from app.application.use_cases.activities import *
from app.infrastructure.database.initialize import _init_db
from app.application.use_cases.ai_configuration import *
from app.application.use_cases.billing import *
from app.application.use_cases.ai_providers import *
from app.application.use_cases.api_keys import *
from app.application.use_cases.ai_policy import *



# Configurar logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Configurações do Banco de Dados



# Enums


# Models
TRIAL_DAYS = 7






























# Helper functions


# Pydantic models

    # whatsapp já inclui máscara do frontend, ex: (11) 99999-9999

















cors_allowed_origins = [
    origin.strip()
    for origin in os.getenv("KEALEX_CORS_ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
]


# ── Assinatura (Asaas) ───────────────────────────────────────────────────────

import hmac as _hmac
import json as _json








































# Health endpoints



# Auth endpoints













# Basic endpoints for other services (placeholder endpoints)

























# IA Configuration


























































# Agentes IA endpoints










# ── COBRANCAS ──────────────────────────────────────────────────────────────












# Configuration Models





# Configuration Endpoints












# Public and private symbols are intentionally exported for route modules and legacy tests.
__all__ = [name for name in globals() if not name.startswith("__")]
