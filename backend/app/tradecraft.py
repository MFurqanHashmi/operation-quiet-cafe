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
        "blurb": "capture frames off the wire and read the raw bytes \u2014 the way an attacker on open Wi-Fi actually would.",
        "href": "https://www.tcpdump.org/manpages/tcpdump.1.html",
        "intro": "You're Eve with a packet sniffer. We'll walk you through two real commands an attacker uses on open Wi-Fi. Each step shows the exact command and why it works \u2014 just hit Run.",
        "steps": [
            {"objective": "Capture every frame on the network and print its contents as text.",
             "why": "On open Wi-Fi every laptop can see every other laptop's traffic. tcpdump turns your machine into a silent recorder \u2014 no hacking required, it's a standard admin tool.",
             "command": "tcpdump -A -i any port 80",
             "parts": [["tcpdump", "the packet capture tool"],
                       ["-A", "print packet contents as ASCII (readable text)"],
                       ["-i any", "listen on every network interface"],
                       ["port 80", "only plain HTTP traffic"]],
             "notice": "Look at the captured frames \u2014 the message text is sitting there in plain ASCII. You didn't decrypt anything; there was nothing to decrypt.",
             "hint": "Just press Run \u2014 the command is filled in for you.",
             "accept": r"tcpdump.*(-A|-X).*(-i|any)|tcpdump.*(-i|any).*(-A|-X)|tcpdump\s+-A",
             "canonical": "tcpdump -A -i any port 80",
             "render": "tcpdump"},
            {"objective": "You saved the suspicious frame as leak.bin. Dump it as hex + ASCII to confirm it's plaintext.",
             "why": "hexdump shows the exact bytes on the left and their readable characters on the right. If the right-hand column is readable English, the data was never encrypted.",
             "command": "hexdump -C leak.bin",
             "parts": [["hexdump", "show a file's raw bytes"],
                       ["-C", "canonical view: hex on the left, ASCII on the right"],
                       ["leak.bin", "the captured frame"]],
             "notice": "The ASCII column on the right is plain readable text. No key, no decoding \u2014 plaintext on an open network protects nothing.",
             "hint": "Just press Run \u2014 the command is filled in for you.",
             "accept": r"(hexdump\s+-C|xxd)\s+\S+",
             "canonical": "hexdump -C leak.bin",
             "render": "hexdump"},
        ],
        "lesson": "No key, no decoding \u2014 the ASCII column is just readable. Plaintext on an open network protects nothing.",
    },
    2: {
        "tool": "openssl enc (AES-256-GCM)",
        "blurb": "do real symmetric encryption from the CLI, then feel the key-distribution wall first-hand.",
        "href": "https://docs.openssl.org/3.0/man1/openssl-enc/",
        "intro": "You're Alice. We'll generate a real key, encrypt a message with it, then decrypt it \u2014 and you'll spot exactly what an eavesdropper would need to break in.",
        "steps": [
            {"objective": "Generate a fresh 256-bit key (32 random bytes) and save it as secret.key.",
             "why": "Symmetric encryption needs one shared secret key. This makes a strong random one \u2014 the same kind of key that protects real data at rest.",
             "command": "openssl rand -base64 32 > secret.key",
             "parts": [["openssl rand", "generate cryptographically random bytes"],
                       ["-base64", "encode them as text so they're easy to store"],
                       ["32", "32 bytes = 256 bits = AES-256 strength"],
                       ["> secret.key", "save it to a file"]],
             "notice": "That random string IS the key. Whoever holds it can both lock and unlock \u2014 keep that in mind for the last step.",
             "hint": "Just press Run \u2014 the command is filled in for you.",
             "accept": r"openssl\s+rand\s+.*(-base64|-hex)?\s*32|openssl\s+rand\s+-base64\s+32",
             "canonical": "openssl rand -base64 32 > secret.key",
             "render": "rand_key"},
            {"objective": "Encrypt a secret message to Bob using AES-256-GCM and that key.",
             "why": "AES-256-GCM is the same authenticated cipher that secures HTTPS and disk encryption. It scrambles the message so it's useless without the key.",
             "command": "openssl enc -aes-256-gcm -in msg.txt -pass file:secret.key -a",
             "parts": [["openssl enc", "symmetric encrypt/decrypt"],
                       ["-aes-256-gcm", "the cipher: strong + tamper-detecting"],
                       ["-in msg.txt", "the plaintext message"],
                       ["-pass file:secret.key", "use the key you just made"],
                       ["-a", "output as base64 text"]],
             "notice": "The output is unreadable ciphertext. So far so good \u2014 but Bob can't read it yet. He needs something from you...",
             "hint": "Just press Run \u2014 the command is filled in for you.",
             "accept": r"openssl\s+enc.*aes-?256-?gcm",
             "canonical": "openssl enc -aes-256-gcm -in msg.txt -pass file:secret.key -a",
             "render": "sym_enc"},
            {"objective": "Decrypt it back. As you run it, ask: what did Bob need from you to do this?",
             "why": "Decryption uses the EXACT SAME key as encryption. That's the defining trait of symmetric crypto \u2014 and the source of its biggest problem.",
             "command": "openssl enc -d -aes-256-gcm -in cipher.b64 -pass file:secret.key -a",
             "parts": [["-d", "decrypt mode"],
                       ["-aes-256-gcm", "same cipher as before"],
                       ["-pass file:secret.key", "the SAME key \u2014 there's no other"]],
             "notice": "It only worked because the same key was used. To let Bob do this, you'd have to send him the key \u2014 over the same wire Eve is watching. That's the wall.",
             "hint": "Just press Run \u2014 the command is filled in for you.",
             "accept": r"openssl\s+enc.*-d|openssl\s+enc.*-d.*aes",
             "canonical": "openssl enc -d -aes-256-gcm -in cipher.b64 -pass file:secret.key -a",
             "render": "sym_dec"},
        ],
        "lesson": "Bob needs the exact same key. The only way to hand it over is the same wire you're hiding from \u2014 that's the symmetric key-distribution wall.",
    },
    3: {
        "tool": "openssl pkeyutl + Diffie-Hellman",
        "blurb": "encrypt to someone's PUBLIC key, then watch two parties derive a shared secret without ever sending it.",
        "href": "https://www.cloudflare.com/learning/ssl/what-happens-in-a-tls-handshake/",
        "intro": "You're Alice. We'll inspect the keyring, lock a message for Bob using his PUBLIC key, then run a real key exchange. Each command is provided \u2014 watch the output to see why public-key crypto solves the wall from Mission 2.",
        "steps": [
            {"objective": "List the public-key fingerprints on your keyring (Bob, Alice, Eve).",
             "why": "Public keys are meant to be shared openly. A fingerprint is a short, unique ID for each one so you can tell them apart at a glance.",
             "command": "list-keys",
             "parts": [["list-keys", "lab wrapper that prints each public key's SHA-256 fingerprint"]],
             "notice": "Three public keys, three fingerprints. These are safe to hand out \u2014 the matching PRIVATE keys never appear here.",
             "hint": "Just press Run \u2014 the command is filled in for you.",
             "accept": r"openssl\s+pkey|list-?keys|openssl\s+dgst",
             "canonical": "list-keys",
             "render": "genpkey"},
            {"objective": "Encrypt 'the drop is confirmed for midnight' so ONLY Bob can open it.",
             "why": "Locking with Bob's PUBLIC key means only Bob's PRIVATE key can open it. You never need to share a secret first \u2014 this is what breaks the Mission 2 wall. (Try swapping bob.pub for eve.pub to see what goes wrong.)",
             "command": "openssl pkeyutl -encrypt -pubin -inkey bob.pub -in drop.txt",
             "parts": [["openssl pkeyutl", "public-key operations"],
                       ["-encrypt", "lock the message"],
                       ["-pubin -inkey bob.pub", "use Bob's PUBLIC key as the lock"],
                       ["-in drop.txt", "the message to protect"]],
             "notice": "Locked with Bob's public key \u2014 only his private key opens it. Nothing secret was shared first. Swap to eve.pub and the warning shows why the recipient choice matters.",
             "hint": "The command uses bob.pub. Change it to eve.pub or alice.pub to experiment.",
             "accept": r"openssl\s+pkeyutl\s+-encrypt.*(bob|eve|alice)",
             "canonical": "openssl pkeyutl -encrypt -pubin -inkey bob.pub -in drop.txt",
             "render": "pubenc"},
            {"objective": "Run an ephemeral Diffie-Hellman exchange between Alice and Bob and compare the secrets.",
             "why": "Diffie-Hellman lets two people derive the SAME shared secret while only exchanging public values. The secret itself never crosses the wire \u2014 this is what real TLS (X25519) does on every HTTPS connection.",
             "command": "dh-exchange",
             "parts": [["dh-exchange", "lab wrapper for an X25519 (ECDHE) key agreement"]],
             "notice": "Both sides computed the IDENTICAL secret, yet only their public 'mixes' were sent. An eavesdropper recording everything still can't reproduce it.",
             "hint": "Just press Run \u2014 the command is filled in for you.",
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
        "intro": "You're Alice at two look-alike drop sites. Both show a padlock. We'll read each certificate's fingerprint with the same tool your browser uses, then compare against Bob's trusted value.",
        "steps": [
            {"objective": "Print the SHA-256 fingerprint and subject of Door A's certificate.",
             "why": "A certificate's fingerprint is a unique hash of its key. The padlock only proves traffic is encrypted \u2014 the fingerprint proves WHO you're talking to.",
             "command": "openssl x509 -in doorA.pem -noout -fingerprint -sha256 -subject",
             "parts": [["openssl x509", "read an X.509 certificate"],
                       ["-in doorA.pem", "Door A's certificate file"],
                       ["-noout", "don't dump the raw cert"],
                       ["-fingerprint -sha256", "print its SHA-256 fingerprint"],
                       ["-subject", "and who it claims to be"]],
             "notice": "Note Door A's fingerprint and subject. The subject (the name) can say anything \u2014 the fingerprint is what's hard to fake.",
             "hint": "Just press Run \u2014 the command is filled in for you.",
             "accept": r"openssl\s+x509.*(doora|door_?a|a\.pem).*(fingerprint|sha256|subject)|openssl\s+x509.*-in\s+a",
             "canonical": "openssl x509 -in doorA.pem -noout -fingerprint -sha256 -subject",
             "render": "x509"},
            {"objective": "Now read Door B's certificate the same way.",
             "why": "Both doors claim to be Bob and both have valid padlocks. The only way to tell them apart is to compare their fingerprints side by side.",
             "command": "openssl x509 -in doorB.pem -noout -fingerprint -sha256 -subject",
             "parts": [["-in doorB.pem", "Door B's certificate this time"],
                       ["-fingerprint -sha256", "same fingerprint check"],
                       ["-subject", "same claimed name"]],
             "notice": "Door B's name may match Bob too \u2014 but its fingerprint is different. One of these is an impostor. Which one is real?",
             "hint": "Just press Run \u2014 the command is filled in for you.",
             "accept": r"openssl\s+x509.*(doorb|door_?b|b\.pem)",
             "canonical": "openssl x509 -in doorB.pem -noout -fingerprint -sha256 -subject",
             "render": "x509"},
            {"objective": "Show Bob's known-good fingerprint and decide which door is really him.",
             "why": "Trust has to start somewhere out-of-band \u2014 here, a fingerprint Bob gave you in person. Whichever door matches THIS value is the real Bob.",
             "command": "show-trusted",
             "parts": [["show-trusted", "print the fingerprint you confirmed with Bob in person"]],
             "notice": "Only one door's fingerprint matches Bob's trusted value. The other had a padlock and the right name \u2014 and was still the impostor.",
             "hint": "Just press Run \u2014 the command is filled in for you.",
             "accept": r"show-?trusted|cat\s+.*trust|known",
             "canonical": "show-trusted",
             "render": "known_fp"},
        ],
        "lesson": "The names matched and both had padlocks \u2014 only the fingerprint, tied to a value you trust out-of-band, reveals which key is genuinely Bob's.",
    },
    5: {
        "tool": "ssh-keygen + ssh",
        "blurb": "create a real key pair, publish only the public half, and log in with no password crossing the wire.",
        "href": "https://man.openbsd.org/ssh-keygen",
        "intro": "You're Bob, hardening Station Bravo. We'll make a key pair, install the RIGHT half on the server, then log in \u2014 with no password ever sent. Each command is provided.",
        "steps": [
            {"objective": "Generate an Ed25519 key pair.",
             "why": "Key-based login replaces passwords with a math problem only your private key can solve. ssh-keygen creates the pair: a public half to share and a private half that never leaves your laptop.",
             "command": "ssh-keygen -t ed25519 -C bob@field",
             "parts": [["ssh-keygen", "create an SSH key pair"],
                       ["-t ed25519", "a modern, fast, strong key type"],
                       ["-C bob@field", "a comment label for the key"]],
             "notice": "Two files were created. The .pub one is public; the other is private. Next you'll install ONLY the public one \u2014 picking the wrong one is a classic, dangerous mistake.",
             "hint": "Just press Run \u2014 the command is filled in for you.",
             "accept": r"ssh-keygen.*-t\s+ed25519|ssh-keygen",
             "canonical": "ssh-keygen -t ed25519 -C bob@field",
             "render": "sshkeygen"},
            {"objective": "Install the correct half of the pair onto station-bravo.",
             "why": "ssh-copy-id pushes your PUBLIC key to the server's authorized list. The private key stays home \u2014 if you ever put a private key on a server you don't fully control, anyone who breaches it becomes you.",
             "command": "ssh-copy-id bob@station-bravo",
             "parts": [["ssh-copy-id", "append your PUBLIC key to the server"],
                       ["bob@station-bravo", "the account + host to trust your key"]],
             "notice": "Only the public key was installed. The server can now verify you without ever knowing a secret it could leak.",
             "hint": "Just press Run \u2014 the command is filled in for you.",
             "accept": r"ssh-copy-id|cat\s+.*\.pub.*authorized_keys|scp\s+.*\.pub",
             "canonical": "ssh-copy-id bob@station-bravo",
             "render": "sshcopy"},
            {"objective": "Log in to station-bravo and read sealed_orders.txt.",
             "why": "On login the server sends a random challenge; your laptop signs it with the private key locally and sends back only the signature. Watch the output \u2014 no password, no secret, ever crosses the wire.",
             "command": "ssh bob@station-bravo",
             "parts": [["ssh", "open a secure shell"],
                       ["bob@station-bravo", "the account and host to log into"]],
             "notice": "You're in \u2014 and only a one-time signature crossed the wire. Your private key never moved. That's why key auth beats passwords.",
             "hint": "Just press Run \u2014 the command is filled in for you.",
             "accept": r"ssh\s+bob@station-?bravo|ssh\s+.*station",
             "canonical": "ssh bob@station-bravo",
             "render": "ssh"},
        ],
        "lesson": "Your private key never left the laptop. The server only ever saw your public key and a one-time signature \u2014 nothing reusable crossed the wire.",
    },
    6: {
        "tool": "oathtool + openssl signatures",
        "blurb": "generate real TOTP codes from a seed, prove an old one is dead, then replace the whole idea with a signature.",
        "href": "https://www.nongnu.org/oath-toolkit/man-oathtool.html",
        "intro": "You're Bob, retiring the password. We'll generate a real 2FA code, prove an old code is already dead, then go fully passwordless with a signature. Commands provided \u2014 watch what each proves.",
        "steps": [
            {"objective": "Generate the current TOTP code from the shared seed.",
             "why": "That 6-digit app code isn't random \u2014 it's a hash of a shared seed plus the current 30-second time window. Same seed + same clock = same code on both ends, no network needed.",
             "command": "oathtool --totp -b $SEED",
             "parts": [["oathtool", "generate one-time passwords"],
                       ["--totp", "time-based mode (the kind authenticator apps use)"],
                       ["-b $SEED", "the base32 shared seed"]],
             "notice": "That's the same kind of 6-digit code your authenticator app shows. It was computed from the seed + the clock \u2014 nothing was sent to get it.",
             "hint": "Just press Run \u2014 the command is filled in for you.",
             "accept": r"oathtool.*--totp|oathtool\s+-b|oathtool",
             "canonical": "oathtool --totp -b $SEED",
             "render": "oathtool"},
            {"objective": "Try to replay a code captured ~90 seconds ago against the server.",
             "why": "TOTP codes expire fast on purpose. Even if an attacker records one, it's worthless seconds later. This proves it.",
             "command": "replay-old",
             "parts": [["replay-old", "lab wrapper that submits a stale (expired) code"]],
             "notice": "REJECTED. A recorded code is dead within its window \u2014 that short lifetime is the whole point of TOTP.",
             "hint": "Just press Run \u2014 the command is filled in for you.",
             "accept": r"replay-?old|oathtool.*-N|replay",
             "canonical": "replay-old",
             "render": "oath_replay"},
            {"objective": "Go passwordless: have the server issue a challenge and sign it with your private key.",
             "why": "A passkey shares NOTHING secret with the server \u2014 only your public key. The server sends a challenge, your device signs it, the server verifies. There's nothing to phish and nothing in a breach to steal.",
             "command": "passkey-sign",
             "parts": [["passkey-sign", "lab wrapper: real challenge \u2192 sign \u2192 verify against your public key"]],
             "notice": "Signed and verified \u2014 with only your public key on the server. Compare to TOTP: even the seed is gone now. Nothing reusable exists to steal.",
             "hint": "Just press Run \u2014 the command is filled in for you.",
             "accept": r"passkey-?sign|openssl\s+pkeyutl\s+-sign|sign",
             "canonical": "passkey-sign",
             "render": "sign"},
        ],
        "lesson": "TOTP beats a static password but still shares a seed that can leak. A passkey signature shares nothing secret with the server \u2014 there's simply nothing to phish or steal.",
    },
}


def _step_view(mission: int, idx: int) -> dict:
    s = TRADECRAFT[mission]["steps"][idx]
    return {"index": idx, "total": len(TRADECRAFT[mission]["steps"]),
            "objective": s["objective"], "why": s.get("why", ""),
            "command": s.get("command", ""), "parts": s.get("parts", []),
            "hint": s["hint"]}


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
        out["reveal"] = step["canonical"]
        return out

    # Correct \u2014 render REAL output and advance.
    output = RENDER[step["render"]](sess, cmd)
    nxt = idx + 1
    done = nxt >= len(tc["steps"])
    resp = {"ok": True, **head, "match": True,
            "output": f"$ {cmd}\n{output}", "notice": step.get("notice", ""),
            "done": done, "progress": f"{nxt}/{len(tc['steps'])}"}
    if done:
        resp["lesson"] = tc["lesson"]
        resp["step"] = None
    else:
        resp["step"] = _step_view(mission, nxt)
    return resp
