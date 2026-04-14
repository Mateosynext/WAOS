import unittest

from fastapi import HTTPException

from backend.app.security import ensure_bot_access, ensure_org_access


class TenantAuthorizationTests(unittest.TestCase):
    def test_member_can_access_own_org(self):
        user = {"global_role": "org_admin", "organization_ids": ["org_1"]}
        ensure_org_access(user, "org_1")

    def test_member_cannot_access_other_org(self):
        user = {"global_role": "org_admin", "organization_ids": ["org_1"]}
        with self.assertRaises(HTTPException) as ctx:
            ensure_org_access(user, "org_2")
        self.assertEqual(ctx.exception.status_code, 403)

    def test_super_admin_can_access_any_org(self):
        user = {"global_role": "super_admin", "organization_ids": []}
        ensure_org_access(user, "org_any")

    def test_bot_access_enforces_tenant_boundary(self):
        user = {"global_role": "operator", "organization_ids": ["org_safe"]}
        bot = {"id": "bot_1", "organization_id": "org_other"}
        with self.assertRaises(HTTPException) as ctx:
            ensure_bot_access(user, bot)
        self.assertEqual(ctx.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()
