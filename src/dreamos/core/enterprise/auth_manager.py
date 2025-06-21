"""
Victor.os Enterprise Auth Manager
Phase 4: SSO, JWT, and tenant-aware authentication
"""

import time
import uuid
import jwt
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import structlog
from passlib.context import CryptContext

logger = structlog.get_logger("auth_manager")

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class AuthProvider(Enum):
    LOCAL = "local"
    OAUTH2 = "oauth2"
    SAML = "saml"

class UserRole(Enum):
    USER = "user"
    ADMIN = "admin"
    SUPERADMIN = "superadmin"
    SUPPORT = "support"

@dataclass
class AuthUser:
    user_id: str
    tenant_id: str
    email: str
    hashed_password: str
    roles: List[UserRole]
    provider: AuthProvider
    is_active: bool
    created_at: float
    updated_at: float
    last_login: Optional[float] = None
    sso_id: Optional[str] = None
    metadata: Dict[str, Any] = None

class AuthManager:
    """Tenant-aware authentication manager supporting SSO and JWT"""
    def __init__(self, secret_key: str, jwt_expiry: int = 3600):
        self.secret_key = secret_key
        self.jwt_expiry = jwt_expiry
        self.users: Dict[str, AuthUser] = {}  # user_id -> AuthUser
        self.email_index: Dict[str, str] = {}  # email -> user_id
        self.tenant_users: Dict[str, List[str]] = {}  # tenant_id -> [user_id]
        self.revoked_tokens: set = set()
        self.jwt_algorithm = "HS256"
        self.auth_dir = Path("auth")
        self.auth_dir.mkdir(exist_ok=True)

    def create_user(self, tenant_id: str, email: str, password: str, roles: List[UserRole], provider: AuthProvider = AuthProvider.LOCAL, sso_id: str = None, metadata: Dict[str, Any] = None) -> str:
        user_id = f"user_{uuid.uuid4().hex[:8]}"
        hashed_password = pwd_context.hash(password)
        user = AuthUser(
            user_id=user_id,
            tenant_id=tenant_id,
            email=email,
            hashed_password=hashed_password,
            roles=roles,
            provider=provider,
            is_active=True,
            created_at=time.time(),
            updated_at=time.time(),
            sso_id=sso_id,
            metadata=metadata or {}
        )
        self.users[user_id] = user
        self.email_index[email] = user_id
        self.tenant_users.setdefault(tenant_id, []).append(user_id)
        logger.info("User created", user_id=user_id, tenant_id=tenant_id, provider=provider.value)
        return user_id

    def authenticate_local(self, email: str, password: str) -> Optional[str]:
        user_id = self.email_index.get(email)
        if not user_id:
            return None
        user = self.users[user_id]
        if not user.is_active or user.provider != AuthProvider.LOCAL:
            return None
        if not pwd_context.verify(password, user.hashed_password):
            return None
        user.last_login = time.time()
        logger.info("User authenticated", user_id=user_id)
        return self.issue_jwt(user)

    def authenticate_sso(self, sso_id: str, provider: AuthProvider, tenant_id: str) -> Optional[str]:
        # SSO stub: in real system, validate SSO token/assertion
        for user in self.users.values():
            if user.sso_id == sso_id and user.provider == provider and user.tenant_id == tenant_id:
                user.last_login = time.time()
                logger.info("User SSO authenticated", user_id=user.user_id, provider=provider.value)
                return self.issue_jwt(user)
        return None

    def issue_jwt(self, user: AuthUser) -> str:
        payload = {
            "sub": user.user_id,
            "tenant": user.tenant_id,
            "roles": [role.value for role in user.roles],
            "iat": int(time.time()),
            "exp": int(time.time()) + self.jwt_expiry
        }
        token = jwt.encode(payload, self.secret_key, algorithm=self.jwt_algorithm)
        return token

    def validate_jwt(self, token: str) -> Optional[Dict[str, Any]]:
        if token in self.revoked_tokens:
            logger.warning("JWT token revoked", token=token)
            return None
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.jwt_algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("JWT expired", token=token)
            return None
        except jwt.InvalidTokenError:
            logger.warning("Invalid JWT", token=token)
            return None

    def revoke_jwt(self, token: str):
        self.revoked_tokens.add(token)
        logger.info("JWT revoked", token=token)

    def check_access(self, token: str, required_roles: List[UserRole]) -> bool:
        payload = self.validate_jwt(token)
        if not payload:
            return False
        user_roles = set(payload.get("roles", []))
        return any(role.value in user_roles for role in required_roles)

    # SSO/OAuth2/SAML stubs for future expansion
    def initiate_oauth2_flow(self, tenant_id: str):
        # Placeholder for OAuth2 redirect URL generation
        return f"https://sso.example.com/oauth2/authorize?tenant={tenant_id}"

    def initiate_saml_flow(self, tenant_id: str):
        # Placeholder for SAML request
        return f"https://sso.example.com/saml/login?tenant={tenant_id}" 