from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from functools import wraps
from typing import Any, Callable, Optional

from flask import Request, g, jsonify, request

from env_config import get_env


class ApiAuthError(ValueError):
    pass


def _env_flag(name: str, default: bool = False) -> bool:
    raw_value = get_env(name, "").strip().lower()
    if not raw_value:
        return default
    return raw_value in {"1", "true", "yes", "on"}


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def _json_loads(data: bytes, label: str) -> dict[str, Any]:
    try:
        decoded = data.decode("utf-8")
        value = json.loads(decoded)
    except Exception as exc:  # pragma: no cover - defensive parsing guard
        raise ApiAuthError(f"invalid {label}") from exc
    if not isinstance(value, dict):
        raise ApiAuthError(f"invalid {label}")
    return value


def verify_hs256_jwt(token: str, secret: str) -> dict[str, Any]:
    if not token:
        raise ApiAuthError("missing bearer token")
    if not secret:
        raise ApiAuthError("API JWT secret is not configured")

    parts = token.split(".")
    if len(parts) != 3:
        raise ApiAuthError("invalid JWT format")

    header = _json_loads(_b64url_decode(parts[0]), "JWT header")
    if header.get("alg") != "HS256":
        raise ApiAuthError("unsupported JWT algorithm")

    signing_input = f"{parts[0]}.{parts[1]}".encode("utf-8")
    expected_sig = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    supplied_sig = _b64url_decode(parts[2])
    if not hmac.compare_digest(expected_sig, supplied_sig):
        raise ApiAuthError("invalid JWT signature")

    payload = _json_loads(_b64url_decode(parts[1]), "JWT payload")
    now = int(time.time())
    exp = payload.get("exp")
    if exp is not None and int(exp) < now:
        raise ApiAuthError("JWT has expired")

    nbf = payload.get("nbf")
    if nbf is not None and int(nbf) > now:
        raise ApiAuthError("JWT is not yet valid")

    return payload


@dataclass(frozen=True)
class ApiAuthConfig:
    required: bool
    secret: str
    allow_localhost_bypass: bool = True

    @classmethod
    def from_env(
        cls,
        required_override: Optional[bool] = None,
        allow_localhost_bypass_override: Optional[bool] = None,
    ) -> "ApiAuthConfig":
        secret = get_env("API_JWT_SECRET", "").strip()
        required = _env_flag("API_AUTH_REQUIRED", default=bool(secret))
        allow_localhost_bypass = _env_flag("API_ALLOW_LOCALHOST_BYPASS", default=True)

        if required_override is not None:
            required = required_override
        if allow_localhost_bypass_override is not None:
            allow_localhost_bypass = allow_localhost_bypass_override

        return cls(
            required=required,
            secret=secret,
            allow_localhost_bypass=allow_localhost_bypass,
        )


def _is_local_request(req: Request) -> bool:
    remote_addr = (req.remote_addr or "").strip()
    return remote_addr in {"127.0.0.1", "::1", "localhost", ""}


def require_api_auth(config: ApiAuthConfig):
    def decorator(view: Callable[..., Any]):
        @wraps(view)
        def wrapped(*args: Any, **kwargs: Any):
            if not config.required:
                return view(*args, **kwargs)
            if config.allow_localhost_bypass and _is_local_request(request):
                return view(*args, **kwargs)

            bearer = request.headers.get("Authorization", "").strip()
            token = bearer.removeprefix("Bearer ").strip()
            try:
                payload = verify_hs256_jwt(token, config.secret)
            except ApiAuthError as exc:
                return jsonify({"error": str(exc)}), 401

            g.api_jwt_payload = payload
            return view(*args, **kwargs)

        return wrapped

    return decorator
