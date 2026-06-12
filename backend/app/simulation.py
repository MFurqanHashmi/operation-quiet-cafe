"""Ambient simulation loops — the 'live play' running around the learner.

Each room has a scripted background life so the cafe always feels alive.
Loops are started on mission enter and cancelled on leave (no leaked tasks).
"""
import asyncio
from .ws import manager

# Scripted ambient chatter per room. Reactive (real) responses live in missions.py.
SCRIPTS = {
    "open_floor": [
        ("alice", "bob", "You there? Testing this cafe wifi.", False),
        ("bob", "alice", "Loud and clear. Nobody's listening, right?", False),
        ("alice", "bob", "Relax. Who'd bother? Anyway — code word is QC{walls_have_ears}", False),
        ("bob", "alice", "Got it. See you at the usual spot.", False),
        ("alice", "bob", "Ordering a flat white. Back in 5.", False),
    ],
    "cipher_bench": [
        ("bob", "alice", "Standing by at the bench. Send it scrambled this time.", False),
    ],
    "key_exchange": [
        ("bob", "alice", "I've pinned my public padlock to the board. Lock it with that.", False),
    ],
    "hall_of_padlocks": [
        ("bob", "alice", "Two doors claim to be my drop site. Only one is mine.", False),
    ],
    "station_bravo": [
        ("eve", "station", "...trying password 'bob123'... denied.", False),
        ("eve", "station", "...trying 'letmein'... denied.", False),
        ("eve", "station", "...trying 'password1'... denied.", False),
    ],
    "the_vault": [
        ("eve", "vault", "Even if I steal the password... there isn't one anymore?", False),
    ],
}

_tasks: dict[str, asyncio.Task] = {}


async def _loop(sid: str, room: str):
    script = SCRIPTS.get(room, [])
    i = 0
    try:
        while True:
            if not script:
                await asyncio.sleep(3)
                continue
            frm, to, text, enc = script[i % len(script)]
            await manager.send(
                sid, "actor.message", room=room,
                **{"from": frm, "to": to, "text": text, "encrypted": enc},
            )
            await manager.send(
                sid, "packet.sent", room=room,
                **{"id": f"{room}-{i}", "from": frm, "to": to,
                   "encrypted": enc, "preview": text if not enc else None},
            )
            i += 1
            await asyncio.sleep(4.5)
    except asyncio.CancelledError:
        pass


async def start(sid: str, room: str):
    await stop(sid)
    _tasks[sid] = asyncio.create_task(_loop(sid, room))


async def stop(sid: str):
    t = _tasks.pop(sid, None)
    if t and not t.done():
        t.cancel()
        try:
            await t
        except asyncio.CancelledError:
            pass
