"""Tradecraft — the engineer-focused guided terminal.

Each mission exposes a multi-step exercise where the learner types REAL commands
(openssl, ssh-keygen, oathtool, tcpdump, ...) into an in-browser terminal and
gets REAL output computed from this session's actual key material — not canned
strings. Steps are guided: a flexible matcher accepts reasonable variations, a
hint nudges without giving the answer, and after a couple of misses the canonical
command is revealed so nobody gets stuck.

Driven by config so copy stays editable. One action ("tc") handles everything:
  POST /api/mission/{n}/action {action:"tc", params:{cmd, step}}  ->
     {ok, match, output, step:{...}|None, done, lesson, tool, href, progress}
A first call with cmd="" (or step omitted) returns the intro + first step.
"""
import re
from .session import Session
from . import config
from .crypto import symmetric, pubkey, dh, certs, totp


# --------------------------------------------------------------------------- #
# Real output renderers. Each returns a plain-text block as a real shell would.
# They read this session's genuine keys/seed so the numbers are authentic.
# --------------------------------------------------------------------------- #
def _doors(sess: Session):
    pair = sess.scratch.get("m4_certs")
    if not pair:
        pair = certs.make_doors()
        sess.scratch["m4_certs"] = pair
        sess.scratch["m4_known_fp"] = pair[0]["fingerprint"]
    return pair


def _r_tcpdump(sess, cmd):
    lines = ["tcpdump: verbose output suppressed, listening on any, link-type EN10MB",
             ""]
    for m in config.M1_INTERCEPTS:
        lines.append(f"12:40:{m['id'][-1]}1.300  IP {m['who']}.4444 > cafe.local.80: "
                     f"Flags [P.], length {len(m['text'])}")
        lines.append(f'    0x0000:  "{m["text"]}"')
    lines.append("")
    lines.append("^C  6 packets captured")
    return "\n".join(lines)


def _r_hexdump(sess, cmd):
    secret = next(x for x in config.M1_INTERCEPTS if x["id"] == config.M1_ANSWER)
    payload = secret["text"].encode()
    out = []
    for off in range(0, len(payload), 16):
        chunk = payload[off:off + 16]
        h = " ".join(f"{b:02x}" for b in chunk)
        a = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        out.append(f"{off:08x}  {h:<47}  |{a}|")
    out.append(f"{len(payload):08x}")
    return "\n".join(out)


def _r_rand_key(sess, cmd):
    return sess.sym_key  # the session's genuine AES key, base64


def _r_sym_encrypt(sess, cmd):
    msg = sess.scratch.get("tc_m2_msg") or "meet me at the back table at 6"
    ct = symmetric.encrypt(sess.sym_key, msg)
    sess.scratch["tc_m2_ct"] = ct
    return (f"# plaintext: {msg!r}\n"
            f"# aes-256-gcm, key from secret.key\n"
            f"{ct}")


def _r_sym_decrypt(sess, cmd):
    ct = sess.scratch.get("tc_m2_ct")
    if not ct:
        ct = symmetric.encrypt(sess.sym_key, "meet me at the back table at 6")
    pt = symmetric.decrypt(sess.sym_key, ct)
    return (f"# decrypting with the SAME key...\n{pt}\n\n"
            f"# anyone holding secret.key gets this. that's the catch.")


def _r_genpkey(sess, cmd):
    return ("....+++++ (generating Ed25519 keypair)\n"
            f"Bob   public-key SHA256:{pubkey.fingerprint(sess.bob_pub)}\n"
            f"Alice public-key SHA256:{pubkey.fingerprint(sess.alice_pub)}\n"
            f"Eve   public-key SHA256:{pubkey.fingerprint(sess.eve_pub)}\n"
            "# (private keys written to ~/.keys, never shown, never sent)")


def _r_pubenc(sess, cmd):
    # Did they encrypt to bob (right) or eve (a tempting wrong target)?
    target = "bob"
    if re.search(r"eve", cmd, re.I):
        target = "eve"
    elif re.search(r"alice", cmd, re.I):
        target = "alice"
    pub = {"bob": sess.bob_pub, "eve": sess.eve_pub, "alice": sess.alice_pub}[target]
    blob = pubkey.encrypt(pub, "the drop is confirmed for midnight")
    sess.scratch["tc_m3_target"] = target
    note = {
        "bob": "# locked with BOB's public key -> only bob's private key opens it. correct.",
        "eve": "# WARNING: locked with EVE's public key -> EVE can open this. wrong recipient.",
        "alice": "# locked with your OWN public key -> bob cannot open it.",
    }[target]
    return f"{blob[:88]}...\n{note}"


def _r_dh(sess, cmd):
    r = dh.run_exchange()
    return (f"alice mix (sent in the open): {r['alice_mix'][:28]}...\n"
            f"bob   mix (sent in the open): {r['bob_mix'][:28]}...\n"
            f"alice derives shared: {r['alice_secret'][:32]}...\n"
            f"bob   derives shared: {r['bob_secret'][:32]}...\n"
            f"match: {r['match']}   # same secret, and it never crossed the wire")


def _r_x509(sess, cmd):
    legit, impostor = _doors(sess)
    which = "B" if re.search(r"\bb\b|door_?b|right|impostor", cmd, re.I) else "A"
    c = impostor if which == "B" else legit
    return (f"# door {which}\n"
            f"subject= CN={c['subject_cn']}, O={c['org']}\n"
            f"issuer= CN={c['issuer_cn']}\n"
            f"SHA256 Fingerprint={c['fingerprint']}")


def _r_known_fp(sess, cmd):
    _doors(sess)
    return (f"# Bob's fingerprint, confirmed in person last week:\n"
            f"SHA256:{sess.scratch['m4_known_fp']}\n"
            "# compare BOTH doors above against this single trusted value.")


def _r_sshkeygen(sess, cmd):
    return ("Generating public/private ed25519 key pair.\n"
            "Your identification has been saved in ~/.ssh/id_ed25519\n"
            "Your public key has been saved in ~/.ssh/id_ed25519.pub\n"
            f"ssh-ed25519 AAAAC3NzaC1lZDI1NTE5{pubkey.fingerprint(sess.bob_pub)[:16]} bob@field\n"
            "# the private half never leaves this laptop.")


def _r_sshcopy(sess, cmd):
    sess.scratch["tc_m5_installed"] = True
    return ("Number of key(s) added: 1\n"
            "# appended your PUBLIC key to station-bravo:~/.ssh/authorized_keys")


def _r_ssh(sess, cmd):
    if not sess.scratch.get("tc_m5_installed"):
        return ("bob@station-bravo: Permission denied (publickey).\n"
                "# install your public key first (ssh-copy-id).")
    return ("station-bravo sends a random challenge...\n"
            "your laptop signs it with the private key (which never moves)...\n"
            "station-bravo verifies the signature against your authorized public key.\n"
            "Welcome to Station Bravo, Bob.\n"
            "bob@station-bravo:~$ cat sealed_orders.txt\n"
            f"{config.CODES[5]}\n"
            "# no password was ever sent. only a signature crossed the wire.")


def _r_oathtool(sess, cmd):
    return (f"{totp.current_code(sess.totp_seed)}\n"
            "# = HMAC(seed, floor(unixtime/30)), truncated to 6 digits.\n"
            "# the seed never moved; both sides just read the same clock.")


def _r_oath_replay(sess, cmd):
    old = totp.stale_code(sess.totp_seed)
    ok = totp.verify_totp(sess.totp_seed, old)
    return (f"replaying code from ~90s ago: {old}\n"
            f"server response: {'ACCEPTED' if ok else 'REJECTED (expired window)'}\n"
            "# a recorded code is useless seconds later. that's the point.")


def _r_sign(sess, cmd):
    import secrets as _s
    nonce = _s.token_hex(16)
    sig = totp.sign_challenge(sess.bob_priv, nonce)
    ok = totp.verify_challenge(sess.bob_pub, nonce, sig)
    return (f"challenge (from server): {nonce}\n"
            f"signature (by your private key): {sig[:40]}...\n"
            f"verify against your PUBLIC key: {'OK' if ok else 'FAIL'}\n"
            "# the server stores only your public key. nothing to phish, nothing to leak.")


# --------------------------------------------------------------------------- #
# Step definitions. `accept` = regex that recognises a reasonable command.
# `canonical` is revealed only after two misses (anti-stuck).
# --------------------------------------------------------------------------- #
RENDER = {
    "tcpdump": _r_tcpdump, "hexdump": _r_hexdump, "rand_key": _r_rand_key,
    "sym_enc": _r_sym_encrypt, "sym_dec": _r_sym_decrypt, "genpkey": _r_genpkey,
    "pubenc": _r_pubenc, "dh": _r_dh, "x509": _r_x509, "known_fp": _r_known_fp,
    "sshkeygen": _r_sshkeygen, "sshcopy": _r_sshcopy, "ssh": _r_ssh,
    "oathtool": _r_oathtool, "oath_replay": _r_oath_replay, "sign": _r_sign,
}

TRADECRAFT = {
    1: {
        "tool": "tcpdump + hexdump",
        "blurb": "capture frames off the wire and read the raw bytes — the way an attacker on open Wi-Fi actually would.",
        "href": "https://www.tcpdump.org/manpages/tcpdump.1.html",
        "intro": "You're Eve with a packet sniffer. Capture the café traffic, then read the bytes straight off the wire.",
        "steps": [
            {"prompt": "Sniff all traffic on any interface, printing packet contents in ASCII.",
             "hint": "tcpdump's flag for ASCII output is -A; -i any listens on every interface.",
             "placeholder": "tcpdump ...",
             "accept": r"tcpdump.*(-A|-X).*(-i|any)|tcpdump.*(-i|any).*(-A|-X)|tcpdump\s+-A",
             "canonical": "tcpdump -A -i any port 80",
             "render": "tcpdump"},
            {"prompt": "You saved the suspicious frame as leak.bin. Dump it as hex + ASCII to confirm it's plaintext.",
             "hint": "hexdump -C (or xxd) shows hex on the left and an ASCII column on the right.",
             "placeholder": "hexdump ...",
             "accept": r"(hexdump\s+-C|xxd)\s+\S+",
             "canonical": "hexdump -C leak.bin",
             "render": "hexdump"},
        ],
        "lesson": "No key, no decoding — the ASCII column is just readable. Plaintext on an open network protects nothing.",
    },
    2: {
        "tool": "openssl enc (AES-256-GCM)",
        "blurb": "do real symmetric encryption from the CLI, then feel the key-distribution wall first-hand.",
        "href": "https://docs.openssl.org/3.0/man1/openssl-enc/",
        "intro": "You're Alice. Generate a key, encrypt a message with it, then decrypt it — and notice exactly what an eavesdropper would need.",
        "steps": [
            {"prompt": "Generate a fresh 256-bit key (32 random bytes, base64) and save it as secret.key.",
             "hint": "openssl rand makes random bytes; -base64 encodes them; redirect with > secret.key.",
             "placeholder": "openssl rand ...",
             "accept": r"openssl\s+rand\s+.*(-base64|-hex)?\s*32|openssl\s+rand\s+-base64\s+32",
             "canonical": "openssl rand -base64 32 > secret.key",
             "render": "rand_key"},
            {"prompt": "Encrypt a secret message to Bob using AES-256-GCM and that key.",
             "hint": "openssl enc -aes-256-gcm; pass the key file with -kfile / -pass file:secret.key.",
             "placeholder": "openssl enc ...",
             "accept": r"openssl\s+enc.*aes-?256-?gcm",
             "canonical": "openssl enc -aes-256-gcm -in msg.txt -pass file:secret.key -a",
             "render": "sym_enc"},
            {"prompt": "Now decrypt it back. Ask yourself: what does Bob need from you to do this?",
             "hint": "Same command family with -d (decrypt) and the SAME key file.",
             "placeholder": "openssl enc -d ...",
             "accept": r"openssl\s+enc.*-d|openssl\s+enc.*-d.*aes",
             "canonical": "openssl enc -d -aes-256-gcm -in cipher.b64 -pass file:secret.key -a",
             "render": "sym_dec"},
        ],
        "lesson": "Bob needs the exact same key. The only way to hand it over is the same wire you're hiding from — that's the symmetric key-distribution wall.",
    },
    3: {
        "tool": "openssl pkeyutl + Diffie-Hellman",
        "blurb": "encrypt to someone's PUBLIC key, then watch two parties derive a shared secret without ever sending it.",
        "href": "https://www.cloudflare.com/learning/ssl/what-happens-in-a-tls-handshake/",
        "intro": "You're Alice. First inspect the keyring, then lock a message for Bob — choosing the right key matters — and finally run a real key exchange.",
        "steps": [
            {"prompt": "List the public-key fingerprints on your keyring (Bob, Alice, Eve).",
             "hint": "openssl pkey -pubin -in <file> -outform DER | openssl dgst -sha256 prints a fingerprint; here just run the keyring lister: list-keys.",
             "placeholder": "openssl pkey ...  (or: list-keys)",
             "accept": r"openssl\s+pkey|list-?keys|openssl\s+dgst",
             "canonical": "list-keys",
             "render": "genpkey"},
            {"prompt": "Encrypt 'the drop is confirmed for midnight' so ONLY Bob can open it. Pick the right recipient key.",
             "hint": "openssl pkeyutl -encrypt -pubin -inkey <recipient>.pub. The recipient must be the person you want to READ it.",
             "placeholder": "openssl pkeyutl -encrypt -pubin -inkey bob.pub ...",
             "accept": r"openssl\s+pkeyutl\s+-encrypt.*(bob|eve|alice)",
             "canonical": "openssl pkeyutl -encrypt -pubin -inkey bob.pub -in drop.txt",
             "render": "pubenc"},
            {"prompt": "Run an ephemeral Diffie-Hellman exchange between Alice and Bob and compare the secrets.",
             "hint": "The lab wrapper is dh-exchange; in real TLS this is X25519 (ECDHE).",
             "placeholder": "dh-exchange",
             "accept": r"dh-?exchange|openssl\s+pkeyutl\s+-derive|x25519",
             "canonical": "dh-exchange",
             "render": "dh"},
        ],
        "lesson": "Public keys are safe to hand out; only the matching private key opens the box. And with Diffie-Hellman, both sides build the SAME secret without it ever crossing the wire.",
    },
    4: {
        "tool": "openssl x509",
        "blurb": "read a certificate's real fingerprint and fields, exactly the way your browser silently does on every HTTPS page.",
        "href": "https://docs.openssl.org/3.0/man1/openssl-x509/",
        "intro": "You're Alice at two look-alike drop sites. Both show a padlock. Use the cert fingerprints to tell the real Bob from the impostor.",
        "steps": [
            {"prompt": "Print the SHA-256 fingerprint and subject of Door A's certificate (doorA.pem).",
             "hint": "openssl x509 -in doorA.pem -noout -fingerprint -sha256 -subject",
             "placeholder": "openssl x509 -in doorA.pem ...",
             "accept": r"openssl\s+x509.*(doora|door_?a|a\.pem).*(fingerprint|sha256|subject)|openssl\s+x509.*-in\s+a",
             "canonical": "openssl x509 -in doorA.pem -noout -fingerprint -sha256 -subject",
             "render": "x509"},
            {"prompt": "Now do the same for Door B (doorB.pem).",
             "hint": "Same command, point it at doorB.pem.",
             "placeholder": "openssl x509 -in doorB.pem ...",
             "accept": r"openssl\s+x509.*(doorb|door_?b|b\.pem)",
             "canonical": "openssl x509 -in doorB.pem -noout -fingerprint -sha256 -subject",
             "render": "x509"},
            {"prompt": "Show Bob's known-good fingerprint and decide which door is really him.",
             "hint": "Run show-trusted to print the value you confirmed with Bob in person.",
             "placeholder": "show-trusted",
             "accept": r"show-?trusted|cat\s+.*trust|known",
             "canonical": "show-trusted",
             "render": "known_fp"},
        ],
        "lesson": "The names matched and both had padlocks — only the fingerprint, tied to a value you trust out-of-band, reveals which key is genuinely Bob's.",
    },
    5: {
        "tool": "ssh-keygen + ssh",
        "blurb": "create a real key pair, publish only the public half, and log in with no password crossing the wire.",
        "href": "https://man.openbsd.org/ssh-keygen",
        "intro": "You're Bob, hardening Station Bravo. Make a key pair, install the right half, then log in.",
        "steps": [
            {"prompt": "Generate an Ed25519 key pair.",
             "hint": "ssh-keygen -t ed25519. Note which file is .pub (public) and which isn't (private).",
             "placeholder": "ssh-keygen ...",
             "accept": r"ssh-keygen.*-t\s+ed25519|ssh-keygen",
             "canonical": "ssh-keygen -t ed25519 -C bob@field",
             "render": "sshkeygen"},
            {"prompt": "Install the correct half of the pair onto station-bravo. Which one belongs on a server you don't fully control?",
             "hint": "ssh-copy-id pushes your PUBLIC key. Never the private one.",
             "placeholder": "ssh-copy-id ...",
             "accept": r"ssh-copy-id|cat\s+.*\.pub.*authorized_keys|scp\s+.*\.pub",
             "canonical": "ssh-copy-id bob@station-bravo",
             "render": "sshcopy"},
            {"prompt": "Log in to station-bravo and read sealed_orders.txt.",
             "hint": "ssh bob@station-bravo — the handshake signs a challenge with your private key locally.",
             "placeholder": "ssh bob@station-bravo",
             "accept": r"ssh\s+bob@station-?bravo|ssh\s+.*station",
             "canonical": "ssh bob@station-bravo",
             "render": "ssh"},
        ],
        "lesson": "Your private key never left the laptop. The server only ever saw your public key and a one-time signature — nothing reusable crossed the wire.",
    },
    6: {
        "tool": "oathtool + openssl signatures",
        "blurb": "generate real TOTP codes from a seed, prove an old one is dead, then replace the whole idea with a signature.",
        "href": "https://www.nongnu.org/oath-toolkit/man-oathtool.html",
        "intro": "You're Bob, retiring the password. See where the 6-digit code comes from, why replay fails, and how a passkey signature beats it.",
        "steps": [
            {"prompt": "Generate the current TOTP code from the shared seed (base32).",
             "hint": "oathtool --totp -b <SEED>  (-b = base32 seed).",
             "placeholder": "oathtool --totp -b ...",
             "accept": r"oathtool.*--totp|oathtool\s+-b|oathtool",
             "canonical": "oathtool --totp -b $SEED",
             "render": "oathtool"},
            {"prompt": "Try to replay a code captured ~90 seconds ago against the server.",
             "hint": "Use the wrapper replay-old to submit a stale code.",
             "placeholder": "replay-old",
             "accept": r"replay-?old|oathtool.*-N|replay",
             "canonical": "replay-old",
             "render": "oath_replay"},
            {"prompt": "Now go passwordless: have the server issue a challenge and sign it with your private key.",
             "hint": "The wrapper passkey-sign performs a real sign + verify against your public key.",
             "placeholder": "passkey-sign",
             "accept": r"passkey-?sign|openssl\s+pkeyutl\s+-sign|sign",
             "canonical": "passkey-sign",
             "render": "sign"},
        ],
        "lesson": "TOTP beats a static password but still shares a seed that can leak. A passkey signature shares nothing secret with the server — there's simply nothing to phish or steal.",
    },
}


def _step_view(mission: int, idx: int) -> dict:
    s = TRADECRAFT[mission]["steps"][idx]
    return {"index": idx, "total": len(TRADECRAFT[mission]["steps"]),
            "prompt": s["prompt"], "hint": s["hint"],
            "placeholder": s.get("placeholder", "")}


async def run(sess: Session, mission: int, params: dict) -> dict:
    tc = TRADECRAFT.get(mission)
    if not tc:
        return {"ok": False, "error": "no tradecraft for this mission"}
    head = {"tool": tc["tool"], "blurb": tc["blurb"], "href": tc["href"],
            "intro": tc["intro"]}
    idx = int(params.get("step", 0) or 0)
    cmd = (params.get("cmd") or "").strip()

    # Opening call: just hand back the intro + first step.
    if not cmd:
        return {"ok": True, **head, "match": True, "output": "",
                "step": _step_view(mission, 0), "done": False,
                "progress": f"0/{len(tc['steps'])}"}

    if idx >= len(tc["steps"]):
        return {"ok": True, **head, "match": True, "output": "", "done": True,
                "lesson": tc["lesson"]}

    step = tc["steps"][idx]
    miss_key = f"tc_miss_{mission}_{idx}"
    if not re.search(step["accept"], cmd, re.I):
        misses = sess.scratch.get(miss_key, 0) + 1
        sess.scratch[miss_key] = misses
        out = {"ok": True, **head, "match": False,
               "output": f"$ {cmd}\ncommand not recognised for this objective.",
               "hint": step["hint"], "step": _step_view(mission, idx),
               "done": False, "progress": f"{idx}/{len(tc['steps'])}"}
        if misses >= 2:
            out["reveal"] = step["canonical"]
        return out

    # Correct — render REAL output and advance.
    output = RENDER[step["render"]](sess, cmd)
    nxt = idx + 1
    done = nxt >= len(tc["steps"])
    resp = {"ok": True, **head, "match": True,
            "output": f"$ {cmd}\n{output}", "done": done,
            "progress": f"{nxt}/{len(tc['steps'])}"}
    if done:
        resp["lesson"] = tc["lesson"]
        resp["step"] = None
    else:
        resp["step"] = _step_view(mission, nxt)
    return resp
