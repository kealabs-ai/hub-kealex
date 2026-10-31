import os
import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

SERVICE_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SERVICE_ROOT))
os.environ.setdefault("KEALEX_DATABASE_URL", "mysql+pymysql://test:test@localhost/test")
os.environ.setdefault("KEALEX_SECRET_KEY", "unit-test-secret")
os.environ.setdefault("KEALEX_ASAAS_BASE_URL", "https://api-sandbox.asaas.com/v3")

from app.application.use_cases.check_tenant_access import check_tenant_access
from app.application.use_cases.grant_subscription_period import grant_subscription_period
from app.domain.exceptions import TenantAccessDenied
from app.infrastructure.security.bcrypt_hasher import hash_password, verify_password


class PasswordHasherTests(unittest.TestCase):
    def test_hash_verifies_only_original_password(self):
        password_hash = hash_password("correct horse battery staple")
        self.assertTrue(verify_password("correct horse battery staple", password_hash))
        self.assertFalse(verify_password("wrong password", password_hash))


class TenantAccessTests(unittest.TestCase):
    def test_admin_bypasses_subscription_access_check(self):
        check_tenant_access(None, "admin")

    def test_active_trial_is_allowed(self):
        tenant = SimpleNamespace(ativo=True, plano="trial", trial_expires_at=datetime.utcnow() + timedelta(days=1))
        check_tenant_access(tenant, "advogado")

    def test_expired_trial_is_denied(self):
        tenant = SimpleNamespace(ativo=True, plano="trial", trial_expires_at=datetime.utcnow() - timedelta(seconds=1))
        with self.assertRaises(TenantAccessDenied):
            check_tenant_access(tenant, "advogado")


class SubscriptionPeriodTests(unittest.TestCase):
    def test_payment_grants_period_once(self):
        tenant = SimpleNamespace(
            last_paid_payment_id=None,
            subscription_expires_at=None,
            subscription_cycle="MONTHLY",
            subscription_status="pending",
            subscription_plan="starter",
            plano="trial",
            ativo=True,
            updated_at=None,
        )
        self.assertTrue(grant_subscription_period(tenant, "payment-1"))
        self.assertEqual(tenant.last_paid_payment_id, "payment-1")
        self.assertEqual(tenant.plano, "starter")
        self.assertFalse(grant_subscription_period(tenant, "payment-1"))


if __name__ == "__main__":
    unittest.main()
