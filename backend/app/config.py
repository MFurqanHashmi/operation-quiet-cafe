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
