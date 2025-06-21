"""
Victor.os Tenant Onboarding CLI/API
Phase 4: Enterprise Deployment - Tenant onboarding, configuration, and provisioning
"""

import argparse
import asyncio
from src.dreamos.core.enterprise.multi_tenant_manager import MultiTenantManager, TenantTier
from src.dreamos.core.enterprise.auth_manager import AuthManager, UserRole, AuthProvider
import secrets

# CLI Entrypoint

def main():
    parser = argparse.ArgumentParser(description="Victor.os Tenant Onboarding CLI")
    subparsers = parser.add_subparsers(dest="command")

    # Create tenant
    create_parser = subparsers.add_parser("create-tenant", help="Create a new tenant")
    create_parser.add_argument("--name", required=True, help="Tenant name")
    create_parser.add_argument("--domain", required=True, help="Tenant domain")
    create_parser.add_argument("--admin-email", required=True, help="Admin email")
    create_parser.add_argument("--tier", choices=[t.value for t in TenantTier], default=TenantTier.STARTER.value, help="Tenant tier")

    # Add user
    user_parser = subparsers.add_parser("add-user", help="Add a user to a tenant")
    user_parser.add_argument("--tenant-id", required=True, help="Tenant ID")
    user_parser.add_argument("--email", required=True, help="User email")
    user_parser.add_argument("--password", required=True, help="User password")
    user_parser.add_argument("--role", choices=[r.value for r in UserRole], default=UserRole.USER.value, help="User role")

    args = parser.parse_args()

    # Setup managers
    mtm = MultiTenantManager()
    auth = AuthManager(secret_key=secrets.token_hex(32))

    if args.command == "create-tenant":
        tenant_id = asyncio.run(mtm.create_tenant(
            name=args.name,
            domain=args.domain,
            tier=TenantTier(args.tier),
            admin_email=args.admin_email
        ))
        print(f"Tenant created: {tenant_id}")

    elif args.command == "add-user":
        user_id = auth.create_user(
            tenant_id=args.tenant_id,
            email=args.email,
            password=args.password,
            roles=[UserRole(args.role)],
            provider=AuthProvider.LOCAL
        )
        print(f"User created: {user_id}")

if __name__ == "__main__":
    main()

# Example API functions (for integration)
async def api_create_tenant(mtm: MultiTenantManager, name: str, domain: str, tier: str, admin_email: str) -> str:
    return await mtm.create_tenant(name=name, domain=domain, tier=TenantTier(tier), admin_email=admin_email)

def api_add_user(auth: AuthManager, tenant_id: str, email: str, password: str, role: str) -> str:
    return auth.create_user(tenant_id=tenant_id, email=email, password=password, roles=[UserRole(role)], provider=AuthProvider.LOCAL) 