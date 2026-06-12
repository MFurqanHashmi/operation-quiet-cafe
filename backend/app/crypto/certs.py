"""Real self-signed certs for Mission 4 (two drop-site doors).

Generates one legit cert (CN=bob.dropsite.cafe) and one impostor that *looks*
similar but has a different fingerprint / issuer — the visual punchline:
a padlock proves the line is locked, not who's on the other end.
"""
import datetime
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa


def _make_cert(common_name: str, org: str, issuer_cn: str):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, common_name),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, org),
    ])
    issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, issuer_cn)])
    now = datetime.datetime.utcnow()
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=365))
        .add_extension(
            x509.SubjectAlternativeName([x509.DNSName(common_name)]),
            critical=False,
        )
        .sign(key, hashes.SHA256())
    )
    fp = cert.fingerprint(hashes.SHA256()).hex().upper()
    fp = ":".join(fp[i:i + 2] for i in range(0, len(fp), 2))
    return {
        "subject_cn": common_name,
        "org": org,
        "issuer_cn": issuer_cn,
        "fingerprint": fp,
        "not_after": cert.not_valid_after_utc.strftime("%Y-%m-%d"),
        "pem": cert.public_bytes(serialization.Encoding.PEM).decode(),
    }


def make_doors():
    """Left = the real Bob (matches the known-good fingerprint). Right = impostor."""
    legit = _make_cert("bob.dropsite.cafe", "Quiet Cafe Field Office",
                       "Quiet Cafe Root CA")
    impostor = _make_cert("bob.dropsite.cafe", "Quiet Cafe Field Office",
                          "Free-Certs-R-Us")  # self-signed by an unknown issuer
    return legit, impostor
