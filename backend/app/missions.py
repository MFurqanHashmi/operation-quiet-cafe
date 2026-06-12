"""Per-mission action handlers. Real crypto/SSH; emits live-play events.

Action contract:  POST /api/mission/{n}/action  {action, params}
Returns mission-specific data. Confirmation codes surface here only after the
underlying task genuinely succeeds; completion is then sealed via /verify.
"""
import secrets
from .ws import manager
from .session import Session
from . import config
from .crypto import symmetric, pubkey, dh, certs, totp
from . import ssh_client


async def handle(sess: Session, mission: int, action: str, params: dict) -> dict:
    fn = _DISPATCH.get((mission, action))
    if not fn:
        return {"ok": False, "error": f"unknown action '{action}' for mission {mission}"}
    return await fn(sess, params)


# ---------------- Mission 1 — Eve taps the open wire ----------------
async def m1_tap(sess: Session, params: dict) -> dict:
    transcript = [
        {"from": "alice", "text": "You there? Testing this cafe wifi."},
        {"from": "bob", "text": "Loud and clear. Nobody's listening, right?"},
        {"from": "alice", "text": "Relax. Who'd bother? Code word is "
                                  f"{config.CODES[1]}"},
        {"from": "bob", "text": "Got it. See you at the usual spot."},
    ]
    await manager.send(sess.id, "eve.capture", room="open_floor", noise=False)
    return {"ok": True, "transcript": transcript,
            "hint": "Everything is in the clear. Read it like a postcard."}


# ---------------- Mission 2 — Alice scrambles (symmetric) ----------------
async def m2_encrypt(sess: Session, params: dict) -> dict:
    pt = params.get("plaintext", "").strip() or "Meet me at the back table at 6."
    ct = symmetric.encrypt(sess.sym_key, pt)
    sess.scratch["m2_ct"] = ct
    sess.scratch["m2_pt"] = pt
    await manager.send(sess.id, "packet.sent", room="cipher_bench",
                       **{"from": "alice", "to": "bob", "encrypted": True,
                          "preview": None, "cipher": ct[:48] + "..."})
    return {"ok": True, "ciphertext": ct,
            "note": "To anyone tapping the wire, that's noise."}


async def m2_send(sess: Session, params: dict) -> dict:
    ct = sess.scratch.get("m2_ct")
    if not ct:
        return {"ok": False, "error": "Scramble a message first."}
    # Bob really decrypts with the shared key.
    pt = symmetric.decrypt(sess.sym_key, ct)
    reply = (f"Decrypted fine: \"{pt}\". Here's the day's code word: "
             f"{config.CODES[2]} ... but wait — how did you get me this key?")
    await manager.send(sess.id, "actor.message", room="cipher_bench",
                       **{"from": "bob", "to": "alice", "text": reply,
                          "encrypted": False})
    return {"ok": True, "bob_reply": reply}


async def m2_send_key(sess: Session, params: dict) -> dict:
    await manager.send(sess.id, "key.exposed", room="cipher_bench")
    return {"ok": True,
            "wall": "Eve just grabbed the shared key off the wire. "
                    "Same key locks AND unlocks — so now she can read everything. "
                    "That's the wall. Mission 3 breaks it."}


async def m2_tamper(sess: Session, params: dict) -> dict:
    ct = sess.scratch.get("m2_ct")
    if not ct:
        return {"ok": False, "error": "Scramble a message first."}
    bad = symmetric.tamper(ct)
    try:
        symmetric.decrypt(sess.sym_key, bad)
        result = "opened (unexpected!)"
    except Exception:
        result = "REFUSED to open — authentication tag failed."
    return {"ok": True, "tampered": bad, "result": result,
            "lesson": "AES-GCM doesn't just hide the message, it detects tampering."}


# ---------------- Mission 3 — Alice uses Bob's public padlock ----------------
async def m3_fetch_key(sess: Session, params: dict) -> dict:
    fp = pubkey.fingerprint(sess.bob_pub)
    sess.scratch["bob_fp"] = fp
    await manager.send(sess.id, "key.published", room="key_exchange",
                       owner="bob", pubkey_fingerprint=fp)
    return {"ok": True, "public_key": sess.bob_pub, "fingerprint": fp}


async def m3_encrypt(sess: Session, params: dict) -> dict:
    pt = params.get("plaintext", "").strip() or "The drop is confirmed for midnight."
    blob = pubkey.encrypt(sess.bob_pub, pt)
    sess.scratch["m3_blob"] = blob
    sess.scratch["m3_pt"] = pt
    await manager.send(sess.id, "packet.sent", room="key_exchange",
                       **{"from": "alice", "to": "bob", "encrypted": True,
                          "preview": None, "cipher": blob[:48] + "..."})
    await manager.send(sess.id, "eve.capture", room="key_exchange", noise=True,
                       sample=blob[:64])
    return {"ok": True, "ciphertext": blob,
            "note": "Locked with Bob's PUBLIC key. Only his PRIVATE key opens it."}


async def m3_send(sess: Session, params: dict) -> dict:
    blob = sess.scratch.get("m3_blob")
    if not blob:
        return {"ok": False, "error": "Lock a message with Bob's key first."}
    pt = pubkey.decrypt(sess.bob_priv, blob)  # Bob really decrypts
    reply = (f"Opened it with my private key: \"{pt}\". "
             f"Eve only ever saw noise. Code word: {config.CODES[3]}")
    await manager.send(sess.id, "actor.message", room="key_exchange",
                       **{"from": "bob", "to": "alice", "text": reply,
                          "encrypted": False})
    return {"ok": True, "bob_reply": reply}


async def m3_dh(sess: Session, params: dict) -> dict:
    r = dh.run_exchange()
    return {"ok": True, **r,
            "lesson": "Both sides derived the SAME secret without ever sending it."}


# ---------------- Mission 4 — Alice inspects the two doors ----------------
async def m4_inspect(sess: Session, params: dict) -> dict:
    legit, impostor = sess.scratch.get("m4_certs", (None, None))
    if not legit:
        legit, impostor = certs.make_doors()
        sess.scratch["m4_certs"] = (legit, impostor)
        sess.scratch["m4_known_fp"] = legit["fingerprint"]
    door = params.get("door")
    cert = legit if door == config.LEGIT_DOOR else impostor
    await manager.send(sess.id, "cert.inspected", room="hall_of_padlocks", door=door)
    view = {k: cert[k] for k in
            ("subject_cn", "org", "issuer_cn", "fingerprint", "not_after")}
    return {"ok": True, "door": door, "cert": view,
            "known_good_fingerprint": sess.scratch["m4_known_fp"]}


async def m4_choose(sess: Session, params: dict) -> dict:
    door = params.get("door")
    if door == config.LEGIT_DOOR:
        await manager.send(sess.id, "door.verified", room="hall_of_padlocks", door=door)
        return {"ok": True, "verified": True,
                "message": f"Fingerprints match. This is really Bob. Code: {config.CODES[4]}"}
    await manager.send(sess.id, "door.warning", room="hall_of_padlocks", door=door)
    return {"ok": True, "verified": False,
            "warning": "This cert is signed by an unknown issuer and its "
                       "fingerprint doesn't match Bob's. The line is encrypted — "
                       "to an impostor. Back out."}


# ---------------- Mission 5 — Bob: real key-based SSH ----------------
async def m5_login(sess: Session, params: dict) -> dict:
    ok, steps, result = ssh_client.provision_and_login()
    for s in steps:
        await manager.send(sess.id, "ssh.step", room="station_bravo", text=s)
    if ok:
        await manager.send(sess.id, "ssh.login_success", room="station_bravo")
        return {"ok": True, "steps": steps, "flag": result}
    await manager.send(sess.id, "ssh.login_failed", room="station_bravo", error=result)
    return {"ok": False, "steps": steps, "error": result}


# ---------------- Mission 6 — Bob: kill the password ----------------
async def m6_totp_show(sess: Session, params: dict) -> dict:
    return {"ok": True, "seed": sess.totp_seed,
            "current": totp.current_code(sess.totp_seed),
            "note": "This 6-digit code is derived from a shared seed + the clock. "
                    "It changes every 30s and nothing secret crosses the wire."}


async def m6_totp_verify(sess: Session, params: dict) -> dict:
    code = params.get("code", "").strip()
    if totp.verify_totp(sess.totp_seed, code):
        sess.scratch["m6_totp_ok"] = True
        return {"ok": True, "accepted": True,
                "note": "Accepted. Now retire the password entirely."}
    return {"ok": True, "accepted": False, "note": "Expired or wrong — try the live code."}


async def m6_passkey_challenge(sess: Session, params: dict) -> dict:
    nonce = secrets.token_hex(16)
    sess.passkey_nonce = nonce
    await manager.send(sess.id, "passkey.challenge", room="the_vault")
    return {"ok": True, "nonce": nonce,
            "note": "The vault sends a one-time challenge. Your device signs it."}


async def m6_passkey_verify(sess: Session, params: dict) -> dict:
    nonce = sess.passkey_nonce
    if not nonce:
        return {"ok": False, "error": "Request a challenge first."}
    # The 'authenticator' signs with the session private key (real sign/verify).
    sig = totp.sign_challenge(sess.bob_priv, nonce)
    if totp.verify_challenge(sess.bob_pub, nonce, sig):
        await manager.send(sess.id, "passkey.verified", room="the_vault")
        return {"ok": True, "verified": True,
                "message": f"Signature checks out. No password existed to steal. "
                           f"Code: {config.CODES[6]}"}
    return {"ok": False, "verified": False, "error": "signature rejected"}


_DISPATCH = {
    (1, "tap"): m1_tap,
    (2, "encrypt"): m2_encrypt,
    (2, "send"): m2_send,
    (2, "send_key"): m2_send_key,
    (2, "tamper"): m2_tamper,
    (3, "fetch_key"): m3_fetch_key,
    (3, "encrypt"): m3_encrypt,
    (3, "send"): m3_send,
    (3, "dh"): m3_dh,
    (4, "inspect"): m4_inspect,
    (4, "choose"): m4_choose,
    (5, "login"): m5_login,
    (6, "totp_show"): m6_totp_show,
    (6, "totp_verify"): m6_totp_verify,
    (6, "passkey_challenge"): m6_passkey_challenge,
    (6, "passkey_verify"): m6_passkey_verify,
}
