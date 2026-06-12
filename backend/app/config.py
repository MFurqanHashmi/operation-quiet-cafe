"""Central config: confirmation codes (server-only), mission metadata, theme.

Codes never leave the server except when a task is genuinely completed.
Content is config-driven so copy can be tweaked without touching logic.
"""
import os

STATION_HOST = os.environ.get("STATION_HOST", "station-bravo")
STATION_PORT = int(os.environ.get("STATION_PORT", "22"))
STATION_USER = "bob"
BOOTSTRAP_KEY_PATH = os.environ.get("BOOTSTRAP_KEY_PATH", "/srv/bootstrap_key")

# ---------------------------------------------------------------------------
# Confirmation codes (the "flags"). Released ONLY by the server on real
# completion. Mission 5's code also physically lives on station-bravo.
# ---------------------------------------------------------------------------
CODES = {
    1: "QC{walls_have_ears}",
    2: "QC{but_how_do_i_share_the_key}",
    3: "QC{eve_recorded_only_noise}",
    4: "QC{a_padlock_proves_nothing}",
    5: "QC{my_secret_never_left_home}",
    6: "QC{the_password_is_dead}",
}

# Which drop-site door is the real Bob in Mission 4.
LEGIT_DOOR = "left"

# ---------------------------------------------------------------------------
# Mission metadata (drives the frontend rhythm + role banners).
# ---------------------------------------------------------------------------
MISSIONS = {
    1: {
        "room": "open_floor",
        "room_name": "The Open Floor",
        "actor": "eve",
        "you_are": "now",
        "title": "The Open Road",
        "concept": "How data moves",
        "tagline": "Nobody locked the door. Let's see what's leaking.",
    },
    2: {
        "room": "cipher_bench",
        "room_name": "The Cipher Bench",
        "actor": "alice",
        "you_are": "now",
        "title": "Scramble It",
        "concept": "Encryption & symmetric keys",
        "tagline": "Make it unreadable. Then realize the catch.",
    },
    3: {
        "room": "key_exchange",
        "room_name": "The Key Exchange",
        "actor": "alice",
        "you_are": "still",
        "title": "Two Keys",
        "concept": "Asymmetric / public-key",
        "tagline": "One key you hand out. One you never do.",
    },
    4: {
        "room": "hall_of_padlocks",
        "room_name": "The Hall of Padlocks",
        "actor": "alice",
        "you_are": "still",
        "title": "The Padlock Lies",
        "concept": "Certificates & trust",
        "tagline": "A padlock proves the line is locked, not who's holding it.",
    },
    5: {
        "room": "station_bravo",
        "room_name": "Station Bravo",
        "actor": "bob",
        "you_are": "now",
        "title": "No Password on the Wire",
        "concept": "SSH & key-based login",
        "tagline": "Flip sides. Defend the post everyone's chasing.",
    },
    6: {
        "room": "the_vault",
        "room_name": "The Vault",
        "actor": "bob",
        "you_are": "still",
        "title": "Kill the Password",
        "concept": "TOTP & passkeys",
        "tagline": "The password is the thing that gets stolen. So delete it.",
    },
}

TOTAL_MISSIONS = len(MISSIONS)


# ===========================================================================
# INTERACTION DATA  (decisions, decoys, deduction checkpoints)
# Added for the "make them think" redesign. Decoys are deliberately tempting;
# checkpoint answers live server-side only so they never ship to the page.
# ===========================================================================

# --- Mission 1: Eve sifts a noisy wire. Only ONE line is the real op secret.
M1_INTERCEPTS = [
    {"id": "i1", "who": "barista", "text": "Oat-milk latte up for table four!"},
    {"id": "i2", "who": "ad-beacon", "text": "FLASH SALE -- use promo code SAVE20 at checkout"},
    {"id": "i3", "who": "router", "text": "DHCP lease 192.168.1.42 renewed (8h)"},
    {"id": "i4", "who": "alice", "text": "btw the cafe wifi is GuestCafe / coffee123 if you need it"},
    {"id": "i5", "who": "bob", "text": "safe combo 4-19-77, meet back table at six, bring the dossier"},
    {"id": "i6", "who": "alice", "text": "haha did you catch the game last night"},
]
M1_ANSWER = "i5"
M1_NUDGES = {
    "i2": "A promo code, sure -- but it's a public ad blast, worthless to an attacker. What would actually compromise the operation?",
    "i3": "An internal IP looks technical, but it leaks nothing an outsider can use. Keep reading for an *operational* secret.",
    "i4": "A real password -- but it's the cafe's PUBLIC guest wifi. Low value. Which line exposes the mission itself?",
    "i1": "Just cafe chatter. Look for a line that would actually help someone hurt the operation.",
    "i6": "Small talk. Nothing exploitable here.",
}

# --- Mission 3: Alice's keyring. Lock with the RECIPIENT's public key.
M3_KEY_CHOICES = ["bob", "eve", "alice"]

# --- Mission 5: which key goes on the server you log into.
M5_INSTALL_CHOICES = ["public", "private", "both"]

# --- Deduction checkpoints (validated server-side; nudges never give the answer)
CHECKPOINTS = {
    "m2_why": {
        "q": "Eve read your message the instant the key crossed the wire. Why?",
        "options": [
            "The AES encryption was too weak to hold up",
            "The same key both locks and unlocks -- and it travelled in the open",
            "Bob accidentally used the wrong key to decrypt",
        ],
        "answer": 1,
        "nudges": {
            0: "Not the cipher -- AES-256-GCM is rock solid. Think about the KEY, not the algorithm.",
            2: "Bob decrypted fine. The problem happened earlier -- on the wire. Who else got the key?",
        },
        "reveal": "Exactly. Symmetric crypto uses ONE shared key. Anyone who grabs it off the wire can read everything. That's the wall Mission 3 breaks.",
    },
    "m4_tell": {
        "q": "Both doors showed a padlock and an encrypted line. What actually exposed the impostor?",
        "options": [
            "The impostor had no padlock / no encryption",
            "The impostor's name was different from Bob's",
            "The impostor's fingerprint didn't match Bob's known-good one",
        ],
        "answer": 2,
        "nudges": {
            0: "Both doors were encrypted -- both had padlocks. Encryption was never the question. Identity was.",
            1: "Look again: the names matched. Anyone can copy a name. What's the part that can't be faked?",
        },
        "reveal": "Right. A padlock proves the line is locked, not WHO holds the other end. Only the fingerprint ties the key to the real Bob.",
    },
    "m5_travels": {
        "q": "You logged in with a key, no password typed. During that login, what actually crossed the wire?",
        "options": [
            "Your password, but encrypted",
            "Your private key, sent securely to the server",
            "Only a signature proving you hold the private key -- the key itself never moved",
        ],
        "answer": 2,
        "nudges": {
            0: "No password existed to send. That's the whole point of key-based auth.",
            1: "Never. If your private key ever leaves your machine, the scheme is broken. Re-read what the server checks.",
        },
        "reveal": "Correct. The server checks a signature against your PUBLIC key. Your private key never leaves home -- nothing reusable ever crosses the wire.",
    },
    "m6_safe": {
        "q": "Phishing thrives on stealing a secret you type. Why are passkeys phishing-resistant?",
        "options": [
            "The password is just much longer and harder to guess",
            "There's no shared secret stored on the server for anyone to steal or phish",
            "The 6-digit code rotates every 30 seconds",
        ],
        "answer": 1,
        "nudges": {
            0: "There's no password at all here -- long or short. Think about what the SERVER stores.",
            2: "That's TOTP, the prior step. Passkeys go further: what is there left to steal?",
        },
        "reveal": "Exactly. The server only holds your PUBLIC key. Nothing secret sits there to leak, and there's nothing to type into a fake site. The password is dead.",
    },
}
