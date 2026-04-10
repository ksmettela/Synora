"""OAuth2 authentication endpoints."""
import hashlib
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from db.postgres import OAuthClient, DatabaseManager
from auth.jwt import JWTManager
from config import get_settings

router = APIRouter(prefix="/v1/auth", tags=["auth"])


class TokenRequest:
    """OAuth2 token request."""

    def __init__(
        self,
        grant_type: str = "client_credentials",
        client_id: str = "",
        client_secret: str = "",
        scope: str = "",
    ):
        self.grant_type = grant_type
        self.client_id = client_id
        self.client_secret = client_secret
        self.scope = scope


class TokenResponse:
    """OAuth2 token response."""

    def __init__(self, access_token: str, token_type: str, expires_in: int):
        self.access_token = access_token
        self.token_type = token_type
        self.expires_in = expires_in


@router.post("/token")
async def create_token(
    grant_type: str = "client_credentials",
    client_id: str = "",
    client_secret: str = "",
    scope: str = "",
    db_manager: DatabaseManager = None,
) -> dict:
    """
    OAuth2 token endpoint.

    Returns JWT token for valid client credentials.
    """
    settings = get_settings()

    if not client_id or not client_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing client_id or client_secret",
        )

    if grant_type != "client_credentials":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only client_credentials grant type is supported",
        )

    # Lookup client in database
    async with db_manager.get_session() as session:
        stmt = select(OAuthClient).where(OAuthClient.client_id == client_id)
        result = await session.execute(stmt)
        client = result.scalar_one_or_none()

        if not client or not client.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid client_id",
            )

        # Verify secret
        secret_hash = hashlib.sha256(client_secret.encode()).hexdigest()
        if secret_hash != client.client_secret_hash:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid client_secret",
            )

        # Generate JWT token
        jwt_manager = JWTManager(
            secret_key=settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )

        # Use requested scopes or client defaults
        scopes = scope.split() if scope else client.scopes
        access_token = jwt_manager.create_token(
            client_id=client_id,
            scopes=scopes,
            expires_in_seconds=settings.JWT_EXPIRATION_SECONDS,
        )

        return {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": settings.JWT_EXPIRATION_SECONDS,
        }


async def verify_token(
    token: str, required_scope: Optional[str] = None
) -> dict:
    """Verify JWT token and optional scope."""
    settings = get_settings()
    jwt_manager = JWTManager(
        secret_key=settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )

    token_data = jwt_manager.decode_token(token)
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    if required_scope and not jwt_manager.validate_scope(token_data, required_scope):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Insufficient permissions. Required scope: {required_scope}",
        )

    return {"client_id": token_data.client_id, "scopes": token_data.scopes}
