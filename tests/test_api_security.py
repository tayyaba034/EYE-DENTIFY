import base64
import hashlib
import hmac
import json
import time

import pytest

from api_security import ApiAuthError, verify_hs256_jwt


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _make_token(secret: str, payload: dict) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    header_part = _b64url(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_part = _b64url(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_part}.{payload_part}".encode("utf-8")
    signature = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    return f"{header_part}.{payload_part}.{_b64url(signature)}"


def test_verify_hs256_jwt_accepts_valid_token():
    secret = "test-secret"
    token = _make_token(secret, {"sub": "device-1", "exp": int(time.time()) + 60})

    payload = verify_hs256_jwt(token, secret)

    assert payload["sub"] == "device-1"


def test_verify_hs256_jwt_rejects_bad_signature():
    secret = "test-secret"
    token = _make_token(secret, {"sub": "device-1", "exp": int(time.time()) + 60})

    with pytest.raises(ApiAuthError):
        verify_hs256_jwt(token, "wrong-secret")
