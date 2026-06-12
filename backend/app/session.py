"""In-memory session store. Single-user-per-browser; fine for laptop-local."""
import secrets
import time
from dataclasses import dataclass, field
from typing import Optional

from . import config
from .crypto import symmetric, pubkey, totp


@dataclass
class Session:
    id: str
    current_mission: int = 1
    completed: set = field(default_factory=set)
    codes_verified: set = field(default_factory=set)
    # per-session key material (lazy)
    bob_priv: Optional[str] = None
    bob_pub: Optional[str] = None
    sym_key: Optional[str] = None
    totp_seed: Optional[str] = None
    passkey_nonce: Optional[str] = None
    scratch: dict = field(default_factory=dict)
    created: float = field(default_factory=time.time)

    def ensure_keys(self):
        if not self.bob_priv:
            self.bob_priv, self.bob_pub = pubkey.new_keypair()
        if not self.sym_key:
            self.sym_key = symmetric.new_key()
        if not self.totp_seed:
            self.totp_seed = totp.new_seed()

    def to_public(self) -> dict:
        return {
            "session_id": self.id,
            "current_mission": self.current_mission,
            "completed": sorted(self.completed),
            "codes_verified": sorted(self.codes_verified),
            "total": config.TOTAL_MISSIONS,
        }


class SessionStore:
    def __init__(self):
        self._s: dict[str, Session] = {}

    def create(self) -> Session:
        sid = secrets.token_urlsafe(12)
        s = Session(id=sid)
        s.ensure_keys()
        self._s[sid] = s
        return s

    def get(self, sid: str) -> Optional[Session]:
        return self._s.get(sid)

    def get_or_create(self, sid: Optional[str]) -> Session:
        if sid and sid in self._s:
            return self._s[sid]
        return self.create()

    def reset(self, sid: str) -> Session:
        self._s.pop(sid, None)
        return self.create()


store = SessionStore()
