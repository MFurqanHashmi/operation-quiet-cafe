"""Real public-key crypto (RSA-2048 + OAEP) with envelope encryption.

RSA-OAEP can't directly encrypt long messages, so we wrap a random AES key
(envelope) — exactly how TLS/PGP do it. Returns base64 blobs the frontend
treats as opaque "scrambled noise".
"""
import os
import base64
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def new_keypair():
    priv = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    priv_pem = priv.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
    pub_pem = priv.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()
    return priv_pem, pub_pem


def fingerprint(pub_pem: str) -> str:
    pub = serialization.load_pem_public_key(pub_pem.encode())
    der = pub.public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    digest = hashes.Hash(hashes.SHA256())
    digest.update(der)
    h = digest.finalize().hex().upper()
    return ":".join(h[i:i + 2] for i in range(0, len(h), 2))[:47]


def encrypt(pub_pem: str, plaintext: str) -> str:
    pub = serialization.load_pem_public_key(pub_pem.encode())
    aes_key = AESGCM.generate_key(bit_length=256)
    nonce = os.urandom(12)
    body = AESGCM(aes_key).encrypt(nonce, plaintext.encode(), None)
    wrapped = pub.encrypt(
        aes_key,
        padding.OAEP(
            mgf=padding.MGF1(hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )
    return base64.b64encode(
        len(wrapped).to_bytes(2, "big") + wrapped + nonce + body
    ).decode()


def decrypt(priv_pem: str, blob_b64: str) -> str:
    priv = serialization.load_pem_private_key(priv_pem.encode(), password=None)
    raw = base64.b64decode(blob_b64)
    wlen = int.from_bytes(raw[:2], "big")
    wrapped = raw[2:2 + wlen]
    nonce = raw[2 + wlen:2 + wlen + 12]
    body = raw[2 + wlen + 12:]
    aes_key = priv.decrypt(
        wrapped,
        padding.OAEP(
            mgf=padding.MGF1(hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )
    return AESGCM(aes_key).decrypt(nonce, body, None).decode()
