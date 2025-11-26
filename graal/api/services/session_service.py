"""
Session management service using secure tokens.

This module provides secure session token creation and validation using
itsdangerous for signing and encrypting session data.
"""

import logging
import logging.config
import os
from typing import Optional

from itsdangerous import BadSignature, SignatureExpired, TimestampSigner

logging.config.fileConfig("logging.conf")


class SessionService:
    """Service for managing secure session tokens.

    This service creates and validates session tokens that store the ProConnect
    subject identifier (proconnect_sub). Tokens are cryptographically signed
    and time-limited for security.

    Configuration is loaded from environment variables:
        - SESSION_SECRET_KEY: Secret key for signing tokens (required)
        - SESSION_MAX_AGE: Maximum age of tokens in seconds (default: 3600 = 1 hour)

    Attributes:
        _signer: TimestampSigner for creating and validating tokens
        _max_age: Maximum age of tokens in seconds
    """

    def __init__(self) -> None:
        """Initialize session service with configuration from environment.

        Raises:
            ValueError: If SESSION_SECRET_KEY is not configured
        """
        # Get configuration from environment
        secret_key = os.getenv("SESSION_SECRET_KEY")
        if not secret_key:
            logging.error(
                "[SessionService] Missing required configuration: "
                "SESSION_SECRET_KEY must be set"
            )
            raise ValueError(
                "Session configuration incomplete: SESSION_SECRET_KEY is required"
            )

        # Validate secret key strength (minimum 32 bytes recommended)
        if len(secret_key) < 32:
            logging.warning(
                "[SessionService] SESSION_SECRET_KEY is shorter than recommended "
                f"(current: {len(secret_key)} bytes, recommended: 32+ bytes)"
            )

        self._max_age = int(os.getenv("SESSION_MAX_AGE", "3600"))  # 1 hour default

        # Create timestamp signer for secure, time-limited tokens
        self._signer = TimestampSigner(secret_key)

        logging.info(
            f"[SessionService] Initialized with max_age={self._max_age} seconds"
        )

    def create_session_token(self, proconnect_sub: str) -> str:
        """Create a secure session token for the given ProConnect subject.

        The token is cryptographically signed and includes a timestamp for
        expiration checking. It can be safely stored in an HTTP-only cookie.

        Args:
            proconnect_sub: ProConnect subject identifier (unique user ID)

        Returns:
            Signed session token string

        Raises:
            ValueError: If proconnect_sub is empty
        """
        if not proconnect_sub:
            logging.error(
                "[SessionService] Cannot create token: proconnect_sub is empty"
            )
            raise ValueError("proconnect_sub cannot be empty")

        try:
            # Sign the proconnect_sub with timestamp
            token = self._signer.sign(proconnect_sub).decode("utf-8")
            logging.info(
                f"[SessionService] Created session token for user sub={proconnect_sub[:8]}..."
            )
            return token
        except Exception as e:
            logging.error(f"[SessionService] Failed to create session token: {e}")
            raise ValueError(f"Failed to create session token: {e}") from e

    def validate_session_token(self, token: str) -> Optional[str]:
        """Validate a session token and extract the ProConnect subject.

        This method verifies the token signature and checks that it hasn't expired.
        If validation succeeds, it returns the ProConnect subject identifier.

        Args:
            token: Session token to validate

        Returns:
            ProConnect subject identifier if valid, None if invalid or expired
        """
        if not token:
            logging.debug("[SessionService] Cannot validate empty token")
            return None

        try:
            # Unsign and verify timestamp
            proconnect_sub_bytes = self._signer.unsign(
                token.encode("utf-8"),
                max_age=self._max_age,
            )
            proconnect_sub = proconnect_sub_bytes.decode("utf-8")

            logging.debug(
                f"[SessionService] Validated session token for user sub={proconnect_sub[:8]}..."
            )
            return proconnect_sub

        except SignatureExpired:
            logging.info("[SessionService] Session token expired")
            return None
        except BadSignature:
            logging.warning("[SessionService] Invalid session token signature")
            return None
        except Exception as e:
            logging.error(f"[SessionService] Session validation failed: {e}")
            return None

    def get_max_age(self) -> int:
        """Get the maximum age of session tokens in seconds.

        Returns:
            Maximum age in seconds
        """
        return self._max_age


# Singleton instance (following project pattern)
_session_service: SessionService | None = None


def get_session_service() -> SessionService:
    """Get global session service instance (Singleton pattern).

    Returns:
        Global session service instance

    Raises:
        ValueError: If session configuration is incomplete
    """
    global _session_service
    if _session_service is None:
        logging.info("[SessionService] Initializing singleton instance")
        _session_service = SessionService()
    return _session_service
