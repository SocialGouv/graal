"""
ProConnect OAuth 2.0 / OpenID Connect service.

This module provides OAuth integration with ProConnect (French government identity provider)
following the authorization code flow with PKCE (Proof Key for Code Exchange).

ProConnect uses RS256 (RSA + SHA256) for ID token and userinfo signature verification.
The JWKS (JSON Web Key Set) is automatically fetched from the discovery document's jwks_uri
to verify token signatures.
"""

import logging
import logging.config
import os
import secrets
from typing import Any
from urllib.parse import urlencode

import httpx
from authlib.integrations.httpx_client import AsyncOAuth2Client
from authlib.jose import JsonWebKey, jwt
from authlib.oauth2.rfc7636 import create_s256_code_challenge

logging.config.fileConfig("logging.conf")


class ProConnectService:
    """Service for ProConnect OAuth 2.0 / OpenID Connect authentication.

    This service handles the OAuth authorization code flow with ProConnect,
    including authorization URL generation, code exchange, and user claims extraction.

    Configuration is loaded from environment variables:
        - PROCONNECT_CLIENT_ID: OAuth client ID
        - PROCONNECT_CLIENT_SECRET: OAuth client secret
        - PROCONNECT_DISCOVERY_URL: OpenID Connect discovery endpoint
        - PROCONNECT_REDIRECT_URI: Callback URL for this application
        - PROCONNECT_SCOPES: Space-separated list of scopes (default: "openid email profile")

    Attributes:
        _client: AsyncOAuth2Client instance for OAuth operations
        _discovery_url: OpenID Connect discovery endpoint URL
        _redirect_uri: Configured redirect URI
        _scopes: Required OAuth scopes
    """

    def __init__(self) -> None:
        """Initialize ProConnect service with configuration from environment."""
        logging.info("[ProConnectService] Initializing ProConnect service...")

        # Get configuration from environment
        self._client_id = os.getenv("PROCONNECT_CLIENT_ID")
        self._client_secret = os.getenv("PROCONNECT_CLIENT_SECRET")
        self._discovery_url = os.getenv(
            "PROCONNECT_DISCOVERY_URL",
            "https://auth.agentconnect.gouv.fr/api/v2/.well-known/openid-configuration",
        )
        self._redirect_uri = os.getenv(
            "PROCONNECT_REDIRECT_URI", "http://localhost:8000/api/v1/auth/callback"
        )
        self._scopes = os.getenv("PROCONNECT_SCOPES", "openid email profile").split()

        # Log configuration status (without exposing secrets)
        logging.info(
            f"[ProConnectService] Configuration loaded: "
            f"client_id={'SET' if self._client_id else 'MISSING'}, "
            f"client_secret={'SET' if self._client_secret else 'MISSING'}, "
            f"discovery_url={self._discovery_url}, "
            f"redirect_uri={self._redirect_uri}"
        )

        # Validate required configuration
        if not self._client_id or not self._client_secret:
            missing_vars = []
            if not self._client_id:
                missing_vars.append("PROCONNECT_CLIENT_ID")
            if not self._client_secret:
                missing_vars.append("PROCONNECT_CLIENT_SECRET")

            logging.error(
                f"[ProConnectService] Missing required configuration: "
                f"{', '.join(missing_vars)} must be set in environment variables"
            )
            raise ValueError(
                f"ProConnect configuration incomplete: {', '.join(missing_vars)} "
                f"{'is' if len(missing_vars) == 1 else 'are'} required. "
                f"Please set {'it' if len(missing_vars) == 1 else 'them'} in your .env file."
            )

        # Initialize OAuth client with OpenID Connect configuration
        # ProConnect uses RS256 (RSA + SHA256) for token signatures
        self._client = AsyncOAuth2Client(
            client_id=self._client_id,
            client_secret=self._client_secret,
            scope=" ".join(self._scopes),
            redirect_uri=self._redirect_uri,
            token_endpoint_auth_method="client_secret_post",  # noqa: S106
        )

        # Cache for discovery document and JWKS
        self._discovery_doc: dict[str, Any] | None = None
        self._jwks: dict[str, Any] | None = None

        logging.info(
            f"[ProConnectService] Initialized with redirect_uri={self._redirect_uri}, "
            f"scopes={self._scopes}"
        )

    async def _fetch_discovery_document(self) -> dict[str, Any]:
        """Fetch OpenID Connect discovery document.

        The discovery document contains OAuth endpoints (authorization, token, userinfo)
        and is cached after first fetch to avoid redundant requests.

        Returns:
            Discovery document containing OAuth endpoints

        Raises:
            ValueError: If discovery document cannot be fetched
        """
        if self._discovery_doc is not None:
            return self._discovery_doc

        try:
            logging.info(
                f"[ProConnectService] Fetching discovery document from {self._discovery_url}"
            )
            # Use plain HTTP client for public discovery document (no auth required)
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(self._discovery_url)
                response.raise_for_status()
                self._discovery_doc = response.json()
            logging.info("[ProConnectService] Discovery document fetched successfully")
            return self._discovery_doc
        except httpx.ConnectError as e:
            logging.error(
                f"[ProConnectService] Network/DNS error fetching discovery document from {self._discovery_url}: {e}"
            )
            raise ValueError(
                f"Cannot connect to ProConnect at {self._discovery_url}. "
                f"Check your internet connection and DNS settings. Error: {e}"
            ) from e
        except Exception as e:
            logging.error(
                f"[ProConnectService] Failed to fetch discovery document from {self._discovery_url}: {e}"
            )
            raise ValueError(
                f"Failed to fetch ProConnect discovery document from {self._discovery_url}: {e}"
            ) from e

    async def _fetch_jwks(self) -> dict[str, Any]:
        """Fetch JWKS (JSON Web Key Set) for token signature verification.

        ProConnect uses RS256 (RSA with SHA-256) for signing ID tokens and userinfo.
        The JWKS contains the public keys needed to verify these signatures.

        Returns:
            JWKS document containing public keys

        Raises:
            ValueError: If JWKS cannot be fetched
        """
        if self._jwks is not None:
            return self._jwks

        try:
            # Get JWKS URI from discovery document
            discovery = await self._fetch_discovery_document()
            jwks_uri = discovery.get("jwks_uri")

            if not jwks_uri:
                logging.error("[ProConnectService] No jwks_uri in discovery document")
                raise ValueError(
                    "Invalid ProConnect discovery document: missing jwks_uri"
                )

            logging.debug(f"[ProConnectService] Fetching JWKS from {jwks_uri}")
            # Use plain HTTP client for public JWKS endpoint (no auth required)
            async with httpx.AsyncClient() as client:
                response = await client.get(jwks_uri)
                response.raise_for_status()
                self._jwks = response.json()
            logging.info("[ProConnectService] JWKS fetched successfully")
            return self._jwks
        except Exception as e:
            logging.error(f"[ProConnectService] Failed to fetch JWKS: {e}")
            raise ValueError(f"Failed to fetch ProConnect JWKS: {e}") from e

    async def get_authorization_url(self) -> tuple[str, str, str]:
        """Generate OAuth authorization URL with state and PKCE parameters.

        This method creates a secure authorization URL for redirecting users to ProConnect.
        It generates random state and PKCE verifier for security.

        Returns:
            Tuple of (authorization_url, state, code_verifier)
                - authorization_url: Full URL to redirect user to
                - state: Random state parameter for CSRF protection
                - code_verifier: PKCE code verifier to store in session

        Raises:
            ValueError: If discovery document cannot be fetched
        """
        logging.info("[ProConnectService] Generating authorization URL...")

        # Fetch discovery document to get authorization endpoint
        try:
            discovery = await self._fetch_discovery_document()
        except Exception as e:
            logging.error(
                f"[ProConnectService] Failed to fetch discovery document: {e}",
                exc_info=True,
            )
            raise
        authorization_endpoint = discovery.get("authorization_endpoint")

        if not authorization_endpoint:
            logging.error(
                "[ProConnectService] No authorization_endpoint in discovery document"
            )
            raise ValueError(
                "Invalid ProConnect discovery document: missing authorization_endpoint"
            )

        # Generate secure random state for CSRF protection
        state = secrets.token_urlsafe(32)

        # Generate PKCE code verifier and challenge
        code_verifier = secrets.token_urlsafe(32)
        code_challenge = create_s256_code_challenge(code_verifier)

        # Build authorization URL with all required parameters
        params = {
            "response_type": "code",
            "client_id": self._client_id,
            "redirect_uri": self._redirect_uri,
            "scope": " ".join(self._scopes),
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }

        authorization_url = f"{authorization_endpoint}?{urlencode(params)}"

        logging.info(
            f"[ProConnectService] Generated authorization URL with state={state[:8]}..."
        )
        return authorization_url, state, code_verifier

    async def exchange_code_for_token(
        self, code: str, code_verifier: str
    ) -> dict[str, Any]:
        """Exchange authorization code for access token and ID token.

        This method completes the OAuth flow by exchanging the authorization code
        received from ProConnect for access and ID tokens.

        IMPORTANT: The ID token signature is NOT automatically verified by authlib
        during token exchange. The ID token MUST be explicitly verified using
        get_user_claims() which performs RS256 signature verification using JWKS.

        Args:
            code: Authorization code from ProConnect callback
            code_verifier: PKCE code verifier generated during authorization

        Returns:
            Token response containing access_token, id_token, token_type, expires_in

        Raises:
            ValueError: If token exchange fails
        """
        # Fetch discovery document to get token endpoint
        discovery = await self._fetch_discovery_document()
        token_endpoint = discovery.get("token_endpoint")

        if not token_endpoint:
            logging.error("[ProConnectService] No token_endpoint in discovery document")
            raise ValueError(
                "Invalid ProConnect discovery document: missing token_endpoint"
            )

        try:
            logging.debug("[ProConnectService] Exchanging code for token")

            # Exchange code for token with PKCE verifier
            token = await self._client.fetch_token(
                token_endpoint,
                grant_type="authorization_code",
                code=code,
                code_verifier=code_verifier,
            )

            logging.info("[ProConnectService] Successfully exchanged code for token")
            return token
        except Exception as e:
            logging.error(f"[ProConnectService] Token exchange failed: {e}")
            raise ValueError(f"Failed to exchange code for token: {e}") from e

    async def get_user_claims(self, token: dict[str, Any]) -> dict[str, Any]:
        """Extract and verify user information from ID token and userinfo endpoint.

        This method:
        1. Verifies the ID token signature (RS256) and extracts basic claims
        2. Fetches additional claims (email, given_name, etc.) from userinfo endpoint
        3. Merges both sets of claims

        ProConnect follows OpenID Connect standards where the ID token contains minimal
        claims (sub, iss, aud, exp, iat) and additional profile information must be
        fetched from the userinfo endpoint using the access token.

        Args:
            token: Token response from exchange_code_for_token() containing id_token and access_token

        Returns:
            Dictionary of verified user claims including:
                - sub: Unique ProConnect subject identifier
                - email: User email address (from userinfo)
                - email_verified: Email verification status (from userinfo)
                - given_name: First name (from userinfo, if available)
                - family_name: Last name (from userinfo, if available)
                - iss: Token issuer (ProConnect URL)
                - aud: Token audience (client_id)
                - exp: Token expiration timestamp
                - iat: Token issued-at timestamp

        Raises:
            ValueError: If ID token is missing, signature verification fails,
                       access token is missing, or userinfo fetch fails
        """
        try:
            # Get ID token from response
            id_token = token.get("id_token")
            if not id_token:
                logging.error("[ProConnectService] No id_token in token response")
                raise ValueError("Token response missing id_token")

            logging.debug("[ProConnectService] Verifying ID token signature (RS256)")

            # Fetch JWKS for signature verification
            jwks_data = await self._fetch_jwks()
            jwks = JsonWebKey.import_key_set(jwks_data)

            # Fetch discovery document for issuer validation
            discovery = await self._fetch_discovery_document()
            expected_issuer = discovery.get("issuer")

            # Decode and verify ID token with RS256 signature verification
            # This automatically:
            # 1. Verifies RS256 signature using JWKS public keys
            # 2. Validates token expiration (exp claim)
            # 3. Validates issued-at time (iat claim)
            # 4. Validates issuer (iss claim)
            # 5. Validates audience (aud claim)
            claims = jwt.decode(
                id_token,
                jwks,
                claims_options={
                    "iss": {"essential": True, "value": expected_issuer},
                    "aud": {"essential": True, "value": self._client_id},
                    "exp": {"essential": True},
                    "iat": {"essential": True},
                    "sub": {"essential": True},
                },
            )

            # Validate the JWT signature and claims with 2-minute clock skew tolerance
            # This handles cases where ProConnect's server clock is slightly ahead/behind
            claims.validate(leeway=120)

            logging.info(
                f"[ProConnectService] ID token verified successfully (RS256). "
                f"Claims available: {list(claims.keys())}"
            )
            logging.debug(f"[ProConnectService] Full claims: {dict(claims)}")

            claims_dict = dict(claims)

            # Get access token for userinfo endpoint
            access_token = token.get("access_token")
            if not access_token:
                logging.error("[ProConnectService] No access_token in token response")
                raise ValueError("Token response missing access_token")

            # Fetch additional claims from userinfo endpoint
            logging.info(
                "[ProConnectService] Fetching additional claims from userinfo endpoint..."
            )
            userinfo_endpoint = discovery.get("userinfo_endpoint")

            if not userinfo_endpoint:
                logging.error(
                    "[ProConnectService] No userinfo_endpoint in discovery document"
                )
                raise ValueError("Discovery document missing userinfo_endpoint")

            # Fetch userinfo with access token
            async with httpx.AsyncClient(timeout=30.0) as client:
                userinfo_response = await client.get(
                    userinfo_endpoint,
                    headers={"Authorization": f"Bearer {access_token}"},
                )

                logging.info(
                    f"[ProConnectService] Userinfo response status: {userinfo_response.status_code}"
                )
                logging.debug(
                    f"[ProConnectService] Userinfo response headers: {dict(userinfo_response.headers)}"
                )
                logging.debug(
                    f"[ProConnectService] Userinfo response body (first 200 chars): {userinfo_response.text[:200]}"
                )

                userinfo_response.raise_for_status()

                # Check if response is JWT or JSON
                content_type = userinfo_response.headers.get("content-type", "")

                if "application/jwt" in content_type:
                    # Userinfo returned as signed JWT - decode and verify it
                    logging.info(
                        "[ProConnectService] Userinfo response is a signed JWT, decoding..."
                    )
                    userinfo_jwt = userinfo_response.text

                    # Decode and verify the userinfo JWT using same JWKS
                    userinfo_claims_obj = jwt.decode(
                        userinfo_jwt,
                        jwks,
                        claims_options={
                            "iss": {"essential": True, "value": expected_issuer},
                            "aud": {"essential": True, "value": self._client_id},
                            "sub": {"essential": True},
                        },
                    )
                    # Allow 2-minute clock skew tolerance for userinfo JWT as well
                    userinfo_claims_obj.validate(leeway=120)
                    userinfo_claims = dict(userinfo_claims_obj)
                    logging.info(
                        "[ProConnectService] Userinfo JWT verified and decoded successfully"
                    )
                else:
                    # Standard JSON response
                    logging.info("[ProConnectService] Userinfo response is JSON")
                    try:
                        userinfo_claims = userinfo_response.json()
                    except Exception as json_error:
                        logging.error(
                            f"[ProConnectService] Failed to parse userinfo response. "
                            f"Status: {userinfo_response.status_code}, "
                            f"Content-Type: {content_type}, "
                            f"Body: {userinfo_response.text[:500]}"
                        )
                        raise ValueError(
                            f"Userinfo endpoint returned invalid response: {json_error}"
                        ) from json_error

            logging.info(
                f"[ProConnectService] Userinfo claims received: {list(userinfo_claims.keys())}"
            )
            logging.debug(f"[ProConnectService] Userinfo claims: {userinfo_claims}")

            # Merge ID token claims with userinfo claims
            # Userinfo claims override ID token claims for matching keys
            merged_claims = {**claims_dict, **userinfo_claims}

            return merged_claims

        except Exception as e:
            logging.error(
                f"[ProConnectService] ID token verification failed: {e}",
                exc_info=True,
            )
            raise ValueError(f"Failed to verify ID token signature: {e}") from e

    async def validate_token(self, access_token: str) -> bool:
        """Validate an access token (optional JWT validation).

        This method can be used to verify that an access token is still valid.
        For OpenID Connect, this typically involves checking token expiry.

        Args:
            access_token: Access token to validate

        Returns:
            True if token is valid, False otherwise
        """
        try:
            # For simple validation, we can try to fetch userinfo with the token
            discovery = await self._fetch_discovery_document()
            userinfo_endpoint = discovery.get("userinfo_endpoint")

            if not userinfo_endpoint:
                logging.warning(
                    "[ProConnectService] Cannot validate token: no userinfo endpoint"
                )
                return False

            response = await self._client.get(
                userinfo_endpoint,
                headers={"Authorization": f"Bearer {access_token}"},
            )

            return response.status_code == 200
        except Exception as e:
            logging.debug(f"[ProConnectService] Token validation failed: {e}")
            return False


# Singleton instance (following project pattern)
_proconnect_service: ProConnectService | None = None


def get_proconnect_service() -> ProConnectService:
    """Get global ProConnect service instance (Singleton pattern).

    Returns:
        Global ProConnect service instance

    Raises:
        ValueError: If ProConnect configuration is incomplete
    """
    global _proconnect_service
    if _proconnect_service is None:
        logging.info("[ProConnectService] Initializing singleton instance")
        _proconnect_service = ProConnectService()
    return _proconnect_service
