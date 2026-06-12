"""Per-mission action handlers — the "make them think" model.

Every mission now demands a real decision, deduction, or extraction:
  * the wrong choice is possible and tempting,
  * the mistake plays out visibly on the live stage, then you retry,
  * the confirmation code is released ONLY on the genuinely correct path.

Harder hands-on manipulation lives in the per-mission "Tradecraft" actions.
Action contract:  POST /api/mission/{n}/action  {action, params}
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


# --------------------------- shared: deduction checkpoints ------------------
async def _checkpoint(sess: Session, params: dict) -> dict:
    """Generic server-side deduction check. Answers never ship to the client."""
    key = params.get("checkpoint")
    cp = config.CHECKPOINTS.get(key)
    if not cp:
        return {"ok": False, "error": f"unknown checkpoint '{key}'"}
    choice = params.get("choice")
    if choice == cp["answer"]:
        sess.scratch[f"cp_{key}"] = True
        return {"ok": True, "correct": True, "reveal": cp["reveal"]}
    nudge = cp.get("nudges", {}).get(choice) or \
        "Not quite — think it through and try another answer."
    return {"ok": True, "correct": False, "nudge": nudge}


def _cp_done(sess: Session, key: str) -> bool:
    return bool(sess.scratch.get(f"cp_{key}"))


# ============================ Mission 1 — Eve sifts the wire ================
async def m1_intercept(sess: Session, params: dict) -> dict:
    """Return the noisy intercept stream. The learner must FIND the real leak."""
    await manager.send(sess.id, "eve.capture", room="open_floor", noise=False)
    lines = [{"id": x["id"], "who": x["who"], "text": x["text"]}
             for x in config.M1_INTERCEPTS]
    return {"ok": True, "intercepts": lines,
            "task": "Six messages crossed the wire in the clear. Only one would "
                    "actually compromise the operation. Flag it."}


async def m1_accuse(sess: Session, params: dict) -> dict:
    pick = params.get("line_id")
    if pick == config.M1_ANSWER:
        await manager.send(sess.id, "eve.capture", room="open_floor", noise=False)
        return {"ok": True, "correct": True,
                "message": "That's the one — an operational secret, sitting in "
                           "plaintext for anyone at the next table.",
                "code": config.CODES[1]}
    nudge = config.M1_NUDGES.get(pick, "Keep reading — that isn't the leak.")
    return {"ok": True, "correct": False, "nudge": nudge}


async def m1_sniff_raw(sess: Session, params: dict) -> dict:
    """Tradecraft: a tcpdump-style raw frame so engineers see the bytes."""
    secret = next(x for x in config.M1_INTERCEPTS if x["id"] == config.M1_ANSWER)
    payload = secret["text"].encode()
    hexdump = []
    for off in range(0, len(payload), 16):
        chunk = payload[off:off + 16]
        h = " ".join(f"{b:02x}" for b in chunk)
        a = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        hexdump.append(f"{off:04x}  {h:<48}  {a}")
    return {"ok": True, "hexdump": "\n".join(hexdump),
            "lesson": "No key, no decoding — the ASCII column is just... readable. "
                      "That's plaintext on the wire."}


# ============================ Mission 2 — Alice: the key-sharing wall =======
async def m2_encrypt(sess: Session, params: dict) -> dict:
    pt = params.get("plaintext", "").strip() or "Meet me at the back table at 6."
    ct = symmetric.encrypt(sess.sym_key, pt)
    sess.scratch["m2_ct"] = ct
    sess.scratch["m2_pt"] = pt
    await manager.send(sess.id, "packet.sent", room="cipher_bench",
                       **{"from": "alice", "to": "bob", "encrypted": True,
                          "cipher": ct[:48] + "..."})
    return {"ok": True, "ciphertext": ct,
            "note": "Scrambled with a shared key. On the wire it's pure noise — "
                    "but Bob can only read it if he has the same key."}


async def m2_share_key(sess: Session, params: dict) -> dict:
    """The decision: how do you get the shared key to Bob? Every option fails —
    that IS the lesson (symmetric key distribution is the wall)."""
    if not sess.scratch.get("m2_ct"):
        return {"ok": False, "error": "Scramble your message first."}
    method = params.get("method")
    if method == "wire":
        # Consequence plays out live: Eve grabs the key and reads everything.
        await manager.send(sess.id, "key.exposed", room="cipher_bench")
        pt = sess.scratch.get("m2_pt", "")
        await manager.send(sess.id, "actor.message", room="cipher_bench",
                           **{"from": "eve", "to": None, "encrypted": False,
                              "text": f"Thanks for the key! Your 'secret' reads: \"{pt}\". "
                                      f"Same key locks AND unlocks, remember?"})
        return {"ok": True, "wall": True,
                "consequence": "Eve scooped the key off the wire and decrypted your "
                               "message instantly. The same key locks and unlocks — "
                               "so sharing it in the open hands her everything.",
                "next": "So how DO you share a key when the line isn't safe? "
                        "Lock in your answer below."}
    if method == "shout":
        await manager.send(sess.id, "key.exposed", room="cipher_bench")
        return {"ok": True, "wall": True,
                "consequence": "You said the key out loud in a crowded cafe. Eve, two "
                               "tables over, wrote it down. Same result.",
                "next": "Every open channel has an Eve. Lock in your answer below."}
    if method == "courier":
        return {"ok": True, "wall": True,
                "consequence": "A trusted courier works once — but you can't hand-deliver "
                               "a key to every stranger on the internet before talking to "
                               "them. It doesn't scale.",
                "next": "There has to be a way that needs NO pre-shared secret. "
                        "Lock in your answer below."}
    return {"ok": False, "error": "Pick how you'd share the key."}


async def m2_checkpoint(sess: Session, params: dict) -> dict:
    r = await _checkpoint(sess, {**params, "checkpoint": "m2_why"})
    if r.get("correct"):
        r["code"] = config.CODES[2]
    return r


async def m2_tamper(sess: Session, params: dict) -> dict:
    """Tradecraft: hands-on — corrupt the ciphertext, watch GCM refuse it."""
    ct = sess.scratch.get("m2_ct")
    if not ct:
        return {"ok": False, "error": "Scramble a message first."}
    bad = symmetric.tamper(ct)
    try:
        symmetric.decrypt(sess.sym_key, bad)
        result = "opened (unexpected!)"
    except Exception:
        result = "REFUSED to open — authentication tag failed."
    return {"ok": True, "original": ct[:40] + "...", "tampered": bad[:40] + "...",
            "result": result,
            "lesson": "AES-GCM is 'authenticated' encryption: change a single byte and "
                      "it won't decrypt at all. Secrecy AND tamper-detection."}


# ============================ Mission 3 — Alice: pick the right key =========
async def m3_keyring(sess: Session, params: dict) -> dict:
    ring = [
        {"owner": "bob", "label": "Bob — public key",
         "fp": pubkey.fingerprint(sess.bob_pub)},
        {"owner": "eve", "label": "Eve — public key",
         "fp": pubkey.fingerprint(sess.eve_pub)},
        {"owner": "alice", "label": "Alice (you) — public key",
         "fp": pubkey.fingerprint(sess.alice_pub)},
    ]
    await manager.send(sess.id, "key.published", room="key_exchange",
                       owner="bob", pubkey_fingerprint=ring[0]["fp"])
    return {"ok": True, "keyring": ring,
            "task": "Lock the message so ONLY Bob can open it. Choose the key wisely — "
                    "the wrong padlock has real consequences."}


async def m3_lock(sess: Session, params: dict) -> dict:
    """Decision: which public key locks the box? Wrong picks play out live."""
    pt = params.get("plaintext", "").strip() or "The drop is confirmed for midnight."
    owner = params.get("key_owner")
    pubs = {"bob": sess.bob_pub, "eve": sess.eve_pub, "alice": sess.alice_pub}
    if owner not in pubs:
        return {"ok": False, "error": "Pick a key from the ring."}

    blob = pubkey.encrypt(pubs[owner], pt)
    await manager.send(sess.id, "packet.sent", room="key_exchange",
                       **{"from": "alice", "to": "bob", "encrypted": True,
                          "cipher": blob[:48] + "..."})

    if owner == "bob":
        pt_out = pubkey.decrypt(sess.bob_priv, blob)  # Bob really opens it
        await manager.send(sess.id, "eve.capture", room="key_exchange",
                           noise=True, sample=blob[:64])
        await manager.send(sess.id, "actor.message", room="key_exchange",
                           **{"from": "bob", "to": "alice", "encrypted": False,
                              "text": f"Opened it with my PRIVATE key: \"{pt_out}\". "
                                      f"Eve only ever saw noise."})
        return {"ok": True, "correct": True,
                "message": "Locked with Bob's public key — only his private key opens "
                           "it. Eve recorded pure noise.",
                "code": config.CODES[3]}

    if owner == "eve":
        # Consequence: Eve holds the matching private key and reads it.
        leaked = pubkey.decrypt(sess.eve_priv, blob)
        await manager.send(sess.id, "eve.capture", room="key_exchange", noise=False)
        await manager.send(sess.id, "actor.message", room="key_exchange",
                           **{"from": "eve", "to": None, "encrypted": False,
                              "text": f"You locked it with MY public key — so my private "
                                      f"key opens it. It says: \"{leaked}\". Thank you!"})
        return {"ok": True, "correct": False,
                "consequence": "You locked the box with Eve's public key. Only the "
                               "matching private key opens it — and that's hers. She read "
                               "it cleanly. Lock with the RECIPIENT's key, not just any.",
                "retry": True}

    # owner == "alice": only Alice's private key could open it — Bob can't.
    await manager.send(sess.id, "actor.message", room="key_exchange",
                       **{"from": "bob", "to": "alice", "encrypted": True,
                          "text": "This is locked with YOUR public key — I don't have "
                                  "your private key, so I can't open it. Try again?"})
    return {"ok": True, "correct": False,
            "consequence": "You locked it with your own public key. Only YOUR private key "
                           "could open it — so Bob is locked out. To reach Bob, use Bob's "
                           "public key.",
            "retry": True}


async def m3_dh(sess: Session, params: dict) -> dict:
    r = dh.run_exchange()
    return {"ok": True, **r,
            "lesson": "Both sides derived the SAME secret without ever sending it — "
                      "this is what really happens in a TLS handshake."}


# ============================ Mission 4 — Alice: spot the forgery ===========
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
        sess.scratch["m4_door_ok"] = True
        return {"ok": True, "correct": True,
                "message": "Fingerprint matches Bob's known-good value. This is really "
                           "Bob. One more thing before you get the code…",
                "need_checkpoint": True}
    # Consequence: the impostor answers — and it's Eve.
    await manager.send(sess.id, "door.warning", room="hall_of_padlocks", door=door)
    await manager.send(sess.id, "actor.message", room="hall_of_padlocks",
                       **{"from": "eve", "to": None, "encrypted": False,
                          "text": "Welcome! 'Bob' here. Go ahead and send me everything…"})
    return {"ok": True, "correct": False,
            "consequence": "The line was encrypted — to an IMPOSTOR. The name matched, "
                           "the padlock was real, but the fingerprint didn't. You just "
                           "opened a secure channel straight to Eve. Back out and "
                           "compare fingerprints.",
            "retry": True}


async def m4_checkpoint(sess: Session, params: dict) -> dict:
    if not sess.scratch.get("m4_door_ok"):
        return {"ok": False, "error": "Verify the real door first."}
    r = await _checkpoint(sess, {**params, "checkpoint": "m4_tell"})
    if r.get("correct"):
        r["code"] = config.CODES[4]
    return r


async def m4_openssl(sess: Session, params: dict) -> dict:
    """Tradecraft: show the real cert PEM + an openssl-style summary."""
    legit, impostor = sess.scratch.get("m4_certs", (None, None))
    if not legit:
        legit, impostor = certs.make_doors()
        sess.scratch["m4_certs"] = (legit, impostor)
        sess.scratch["m4_known_fp"] = legit["fingerprint"]
    which = params.get("door", config.LEGIT_DOOR)
    cert = legit if which == config.LEGIT_DOOR else impostor
    return {"ok": True,
            "summary": f"subject=CN={cert['subject_cn']}, O={cert['org']}\n"
                       f"issuer=CN={cert['issuer_cn']}\n"
                       f"SHA256 Fingerprint={cert['fingerprint']}\n"
                       f"notAfter={cert['not_after']}",
            "pem": cert["pem"],
            "lesson": "`openssl x509 -noout -fingerprint -sha256` prints exactly this "
                      "fingerprint. Comparing it to a trusted value is how you bind a "
                      "key to a real identity."}


# ============================ Mission 5 — Bob: which key on the server? =====
async def m5_keygen(sess: Session, params: dict) -> dict:
    sess.scratch["m5_keys"] = True
    return {"ok": True,
            "public": "ssh-ed25519 AAAAC3Nz...bob@field   (safe to publish)",
            "private": "-----BEGIN OPENSSH PRIVATE KEY----- (NEVER leaves this laptop)",
            "task": "You generated a key pair. Now: which one do you install on Station "
                    "Bravo so you can log in?"}


async def m5_install(sess: Session, params: dict) -> dict:
    if not sess.scratch.get("m5_keys"):
        return {"ok": False, "error": "Generate your key pair first."}
    which = params.get("which")
    if which == "private":
        await manager.send(sess.id, "door.warning", room="station_bravo")
        return {"ok": True, "correct": False,
                "consequence": "You put your PRIVATE key on a shared server. Now anyone "
                               "who ever breaches that box can impersonate you everywhere "
                               "your key is trusted. The private key must never leave your "
                               "laptop. Install the PUBLIC key instead.",
                "retry": True}
    if which == "both":
        await manager.send(sess.id, "door.warning", room="station_bravo")
        return {"ok": True, "correct": False,
                "consequence": "The public key was all you needed — and you also exposed "
                               "the private one. A leaked private key undoes the whole "
                               "scheme. Public key ONLY.",
                "retry": True}
    if which != "public":
        return {"ok": False, "error": "Pick which key to install."}

    # Correct: install public key + perform a REAL key-based SSH login.
    ok, steps, result = ssh_client.provision_and_login()
    for s in steps:
        await manager.send(sess.id, "ssh.step", room="station_bravo", text=s)
    if ok:
        await manager.send(sess.id, "ssh.login_success", room="station_bravo")
        sess.scratch["m5_login_ok"] = True
        sess.scratch["m5_flag"] = result
        return {"ok": True, "correct": True, "steps": steps,
                "message": "Public key installed; logged in with a signature, no password "
                           "typed. The station handed you its sealed orders. One question "
                           "before the code…",
                "need_checkpoint": True}
    await manager.send(sess.id, "ssh.login_failed", room="station_bravo", error=result)
    return {"ok": False, "steps": steps, "error": result}


async def m5_checkpoint(sess: Session, params: dict) -> dict:
    if not sess.scratch.get("m5_login_ok"):
        return {"ok": False, "error": "Log in successfully first."}
    r = await _checkpoint(sess, {**params, "checkpoint": "m5_travels"})
    if r.get("correct"):
        r["code"] = sess.scratch.get("m5_flag") or config.CODES[5]
    return r


# ============================ Mission 6 — Bob: kill the password ============
async def m6_totp_show(sess: Session, params: dict) -> dict:
    return {"ok": True, "seed": sess.totp_seed,
            "current": totp.current_code(sess.totp_seed),
            "note": "Six digits derived from a shared seed + the clock. It changes every "
                    "30s, and nothing secret crosses the wire."}


async def m6_totp_verify(sess: Session, params: dict) -> dict:
    """Decision/experiment: a fresh code is accepted; a stale one is rejected —
    proving codes are one-time and time-bound."""
    if params.get("stale"):
        old = totp.stale_code(sess.totp_seed)
        accepted = totp.verify_totp(sess.totp_seed, old)
        return {"ok": True, "accepted": accepted, "used_code": old,
                "note": "That code was valid ~90 seconds ago. The vault rejects it — "
                        "a recorded code can't be replayed. That's the point of TOTP."
                        if not accepted else "Unexpectedly accepted (clock skew)."}
    code = params.get("code", "").strip()
    if totp.verify_totp(sess.totp_seed, code):
        sess.scratch["m6_totp_ok"] = True
        return {"ok": True, "accepted": True,
                "note": "Accepted. But a code you type can still be phished. "
                        "Now retire the password entirely."}
    return {"ok": True, "accepted": False,
            "note": "Wrong or expired — enter the LIVE code shown above."}


async def m6_passkey_challenge(sess: Session, params: dict) -> dict:
    nonce = secrets.token_hex(16)
    sess.passkey_nonce = nonce
    await manager.send(sess.id, "passkey.challenge", room="the_vault")
    return {"ok": True, "nonce": nonce,
            "note": "The vault issues a one-time challenge. Your device signs it with a "
                    "private key that never leaves the laptop."}


async def m6_passkey_verify(sess: Session, params: dict) -> dict:
    nonce = sess.passkey_nonce
    if not nonce:
        return {"ok": False, "error": "Request a challenge first."}
    sig = totp.sign_challenge(sess.bob_priv, nonce)  # real sign…
    if totp.verify_challenge(sess.bob_pub, nonce, sig):  # …real verify
        await manager.send(sess.id, "passkey.verified", room="the_vault")
        sess.scratch["m6_passkey_ok"] = True
        return {"ok": True, "verified": True,
                "message": "Signature checks out against your public key. No password "
                           "ever existed to steal or phish. One last question for the code…",
                "need_checkpoint": True}
    return {"ok": False, "verified": False, "error": "signature rejected"}


async def m6_checkpoint(sess: Session, params: dict) -> dict:
    if not sess.scratch.get("m6_passkey_ok"):
        return {"ok": False, "error": "Complete the passwordless login first."}
    r = await _checkpoint(sess, {**params, "checkpoint": "m6_safe"})
    if r.get("correct"):
        r["code"] = config.CODES[6]
    return r


_DISPATCH = {
    (1, "intercept"): m1_intercept,
    (1, "accuse"): m1_accuse,
    (1, "sniff_raw"): m1_sniff_raw,
    (2, "encrypt"): m2_encrypt,
    (2, "share_key"): m2_share_key,
    (2, "checkpoint"): m2_checkpoint,
    (2, "tamper"): m2_tamper,
    (3, "keyring"): m3_keyring,
    (3, "lock"): m3_lock,
    (3, "dh"): m3_dh,
    (4, "inspect"): m4_inspect,
    (4, "choose"): m4_choose,
    (4, "checkpoint"): m4_checkpoint,
    (4, "openssl"): m4_openssl,
    (5, "keygen"): m5_keygen,
    (5, "install"): m5_install,
    (5, "checkpoint"): m5_checkpoint,
    (6, "totp_show"): m6_totp_show,
    (6, "totp_verify"): m6_totp_verify,
    (6, "passkey_challenge"): m6_passkey_challenge,
    (6, "passkey_verify"): m6_passkey_verify,
    (6, "checkpoint"): m6_checkpoint,
}
