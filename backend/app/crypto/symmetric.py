"""Real symmetric crypto (AES-256-GCM) via the cryptography library."""
import os
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def new_key() -> str:
    return base64.b64encode(AESGCM.generate_key(bit_length=256)).decode()


def encrypt(key_b64: str, plaintext: str) -> str:
    key = base64.b64decode(key_b64)
    nonce = os.urandom(12)
    ct = AESGCM(key).encrypt(nonce, plaintext.encode(), None)
    return base64.b64encode(nonce + ct).decode()


def decrypt(key_b64: str, blob_b64: str) -> str:
    key = base64.b64decode(key_b64)
    raw = base64.b64decode(blob_b64)
    nonce, ct = raw[:12], raw[12:]
    return AESGCM(key).decrypt(nonce, ct, None).decode()


def tamper(blob_b64: str) -> str:
    """Flip a byte so GCM auth fails — used in Mission 2 tradecraft."""
    raw = bytearray(base64.b64decode(blob_b64))
    raw[-1] ^= 0x01
    return base64.b64encode(bytes(raw)).decode()
