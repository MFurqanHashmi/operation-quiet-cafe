"""Real Diffie-Hellman demo (X25519) for Mission 3 tradecraft.

Drives both halves from one console so the learner watches Alice and Bob
independently derive the SAME shared secret without it ever crossing the wire.
"""
import base64
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF


def _pub_b64(priv: X25519PrivateKey) -> str:
    return base64.b64encode(
        priv.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw
        )
    ).decode()


def run_exchange():
    """Returns the public 'paint mixes' and the identical derived secret."""
    alice = X25519PrivateKey.generate()
    bob = X25519PrivateKey.generate()

    alice_pub = alice.public_key()
    bob_pub = bob.public_key()

    alice_shared = alice.exchange(bob_pub)
    bob_shared = bob.exchange(alice_pub)

    def derive(s):
        return base64.b64encode(
            HKDF(algorithm=hashes.SHA256(), length=32, salt=None,
                 info=b"quiet-cafe-dh").derive(s)
        ).decode()

    a_secret = derive(alice_shared)
    b_secret = derive(bob_shared)
    return {
        "alice_mix": _pub_b64(alice),   # sent in the open
        "bob_mix": _pub_b64(bob),       # sent in the open
        "alice_secret": a_secret,
        "bob_secret": b_secret,
        "match": a_secret == b_secret,
    }
