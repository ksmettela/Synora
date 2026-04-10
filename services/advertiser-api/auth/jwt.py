"""JWT token creation and validation."""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from pydantic import BaseModel


class TokenData(BaseModel):
    """Token payload data."""

    client_id: str
    scopes: list[str]
    exp: datetime


class JWTManager:
    """Manages JWT token creation and validation."""

    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        self.secret_key = secret_key
        self.algorithm = algorithm

    def create_token(
        self,
        client_id: str,
        scopes: list[str],
        expires_in_seconds: int,
    ) -> str:
        """Create JWT token."""
        expire = datetime.utcnow() + timedelta(seconds=expires_in_seconds)
        payload = {
            "client_id": client_id,
            "scopes": scopes,
            "exp": expire,
        }
        encoded_jwt = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt

    def decode_token(self, token: str) -> Optional[TokenData]:
        """Decode and validate JWT token."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            client_id = payload.get("client_id")
            scopes = payload.get("scopes", [])
            exp = payload.get("exp")

            if not client_id or not exp:
                return None

            return TokenData(
                client_id=client_id,
                scopes=scopes,
                exp=datetime.fromtimestamp(exp),
            )
        except JWTError:
            return None

    def validate_scope(self, token_data: TokenData, required_scope: str) -> bool:
        """Check if token has required scope."""
        return required_scope in token_data.scopes
