import logging
from typing import Coroutine, Any, Dict, List, Tuple
from fastapi import HTTPException
from pydantic import BaseModel
from starlette.authentication import (
    AuthCredentials,
    AuthenticationBackend,
    BaseUser,
    UnauthenticatedUser,
)
from fastapi.security import OAuth2AuthorizationCodeBearer
from starlette.requests import HTTPConnection

from .oauth2_admin import oauth2_admin

log = logging.getLogger(__name__)


class AuthenticatedUser(BaseUser, BaseModel):
    claims: Dict[str, Any]
    name: str | None
    username: str | None
    email: str | None
    id: str | None

    @classmethod
    def from_claim(cls, claims: Dict[str, Any]) -> "AuthenticatedUser":
        return cls(
            claims=claims,
            name=claims.get("name"),
            username=claims.get("preferred_username"),
            email=claims.get("email"),
            id=claims.get("sub"),
        )

    @property
    def is_authenticated(self) -> bool:
        return True


class BearerTokenAuthBackend(AuthenticationBackend):
    def __init__(self, token_bearer: OAuth2AuthorizationCodeBearer) -> None:
        self.token_bearer = token_bearer

    async def authenticate(
        self, conn: HTTPConnection
    ) -> Coroutine[Any, Any, Tuple[AuthCredentials, BaseUser] | None]:
        print(f"baseurl: {conn.url.path}")
        if conn.url.path.endswith("v1/institutions"):
            return None
        try:
            token = await self.token_bearer(conn)
            claims = oauth2_admin.get_claims(token)
            if claims is not None:
                auths = (
                    self.extract_nested(
                        claims, "resource_access", "realm-management", "roles"
                    )
                    + self.extract_nested(claims, "resource_access", "account", "roles")
                    + ["authenticated"]
                )
                return AuthCredentials(auths), AuthenticatedUser.from_claim(claims)
        except HTTPException:
            log.exception("failed to get claims")
        return AuthCredentials("unauthenticated"), UnauthenticatedUser()

    def extract_nested(self, data: Dict[str, Any], *keys: str) -> List[str]:
        _ele = data
        try:
            for key in keys:
                _ele = _ele[key]
            return _ele
        except KeyError:
            return []
