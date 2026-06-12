"""Real SSH into station-bravo (Mission 5) via paramiko.

The backend holds a baked 'bootstrap' key already trusted by the station.
Flow that mirrors the lesson:
  1. generate a FRESH session keypair (the learner's "new key")
  2. use the bootstrap connection to install the session public key
  3. reconnect using ONLY the session private key (real key-based auth)
  4. read the flag — proving the password never crossed the wire
"""
import io
import paramiko
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

from . import config


def _gen_session_key():
    k = ed25519.Ed25519PrivateKey.generate()
    priv = k.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.OpenSSH,
        serialization.NoEncryption(),
    ).decode()
    pub = k.public_key().public_bytes(
        serialization.Encoding.OpenSSH, serialization.PublicFormat.OpenSSH
    ).decode() + " session-key"
    return priv, pub


def _connect(pkey):
    cli = paramiko.SSHClient()
    cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    cli.connect(
        hostname=config.STATION_HOST,
        port=config.STATION_PORT,
        username=config.STATION_USER,
        pkey=pkey,
        look_for_keys=False,
        allow_agent=False,
        timeout=8,
    )
    return cli


def provision_and_login():
    """Returns (ok, steps, flag_or_error). steps = human-readable log for the UI."""
    steps = []
    try:
        bootstrap = paramiko.Ed25519Key.from_private_key_file(
            config.BOOTSTRAP_KEY_PATH
        )
    except Exception as e:  # noqa
        return False, steps, f"bootstrap key unavailable: {e}"

    session_priv, session_pub = _gen_session_key()
    steps.append("Generated a fresh session key on your laptop (private half never leaves).")

    # 1. install the session public key using the trusted bootstrap connection
    try:
        cli = _connect(bootstrap)
        cmd = (
            "mkdir -p ~/.ssh && chmod 700 ~/.ssh && "
            f"grep -qxF '{session_pub}' ~/.ssh/authorized_keys 2>/dev/null || "
            f"echo '{session_pub}' >> ~/.ssh/authorized_keys && "
            "chmod 600 ~/.ssh/authorized_keys"
        )
        _, stdout, _ = cli.exec_command(cmd)
        stdout.channel.recv_exit_status()  # wait for the append to finish
        cli.close()
        steps.append("Installed your PUBLIC key on Station Bravo's authorized list.")
    except Exception as e:  # noqa
        return False, steps, f"could not reach station to install key: {e}"

    # 2. reconnect using ONLY the freshly generated session private key
    try:
        pkey = paramiko.Ed25519Key.from_private_key(io.StringIO(session_priv))
        cli = _connect(pkey)
        steps.append("Logged in using key auth ONLY — no password was ever sent.")
        _, stdout, _ = cli.exec_command("cat ~/flag.txt")
        flag = stdout.read().decode().strip()
        cli.close()
        steps.append("Read the sealed orders waiting on the station.")
        return True, steps, flag
    except Exception as e:  # noqa
        return False, steps, f"key-based login failed: {e}"
