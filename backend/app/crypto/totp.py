"""Real TOTP (RFC 6238) + a simulated-but-real passwordless ceremony.

TOTP uses pyotp. Passwordless signs a server nonce with the session's RSA key
and verifies it server-side — a genuine challenge/response, no WebAuthn
hardware required (works offline on any laptop).
"""
import base64
import pyotp
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization, hashes


def new_seed() -> str:
    return pyotp.random_base32()


def current_code(seed: str) -> str:
    return pyotp.TOTP(seed).now()


def verify_totp(seed: str, code: str) -> bool:
    # valid_window=1 tolerates clock skew (±30s).
    return pyotp.TOTP(seed).verify(code, valid_window=1)


def stale_code(seed: str) -> str:
    """A code that was valid ~90s ago — used to prove replays are rejected."""
    import time
    return pyotp.TOTP(seed).at(time.time() - 90)


def sign_challenge(priv_pem: str, nonce: str) -> str:
    priv = serialization.load_pem_private_key(priv_pem.encode(), password=None)
    sig = priv.sign(
        nonce.encode(),
        padding.PSS(mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH),
        hashes.SHA256(),
    )
    return base64.b64encode(sig).decode()


def verify_challenge(pub_pem: str, nonce: str, sig_b64: str) -> bool:
    pub = serialization.load_pem_public_key(pub_pem.encode())
    try:
        pub.verify(
            base64.b64decode(sig_b64),
            nonce.encode(),
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()),
                        salt_length=padding.PSS.MAX_LENGTH),
            hashes.SHA256(),
        )
        return True
    except Exception:
        return False
