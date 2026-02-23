import logging
from datetime import datetime, timezone

import jwt
from fastapi import HTTPException, status

from app.core.config import settings

logger = logging.getLogger(__name__)


class SecurityService:
    def __init__(self):
        pass

    def validar_jwt(self, token: str) -> dict:
        """Decode and validate a JWT token.

        - Accepts tokens with or without the "Bearer " prefix.
        - Supports common HS algorithms (HS256/HS384/HS512).
        - Returns the decoded payload on success.
        - Raises HTTPException on invalid/expired tokens.
        """
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Token não fornecido"
            )

        # Remove Bearer prefix if present
        if token.startswith("Bearer "):
            token = token.split(" ", 1)[1]

        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET,
                algorithms=["HS256", "HS384", "HS512"],
            )

            # Some jwt libraries/settings may not enforce exp verification in all cases.
            # Add a manual check to ensure expired tokens are rejected.
            exp = payload.get("iat") or payload.get("exp")
            if exp is not None:
                try:
                    exp_ts = int(exp)
                except Exception:
                    exp_ts = None

                if exp_ts is not None:
                    exp_dt = datetime.fromtimestamp(exp_ts, tz=timezone.utc)
                    if datetime.now(tz=timezone.utc) >= exp_dt:
                        logger.warning("Erro: Token expirado (verificação manual)")
                        raise jwt.ExpiredSignatureError("Token expirado")

            logger.info("Token válido! Payload: %s", payload)
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("Erro: Token expirado")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expirado"
            )
        except jwt.InvalidTokenError:
            logger.warning("Erro: Token inválido")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido"
            )
        except Exception as exc:
            logger.exception("Erro ao validar token: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Erro ao validar token"
            )
