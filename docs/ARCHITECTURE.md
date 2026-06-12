# Operation Quiet Café — Architecture

This document explains how the lab is built, how a request flows end to end, and
**where to look** when you want to change something. If you just want to run the
lab, see the top-level `README.md`.

---

## 1. The big picture

Operation Quiet Café is a single-page web app over a Python backend, plus a real
SSH server used by one mission. Three containers, one published port.

```
                         Browser (http://localhost:8080)
   ┌──────────────────────────────────────────────────────────────┐
   │  React SPA                                                     │
   │  ┌────────────────────── Observation deck ─────────────────┐  │
   │  │  Alice pane     Bob pane     Eve pane    + the "wire"    │  │ live play
   │  └──────────────────────────────────────────────────────────┘ │
   │  ┌────────────────────── Workspace (scrolls) ──────────────┐  │
   │  │  Recall → Predict → Decision/Action → Checkpoint → Code  │  │ the thinking
   │  │  Tradecraft (guided real-CLI terminal)                   │  │
   │  └──────────────────────────────────────────────────────────┘ │
   └───────────┬───────────────────────────────────┬──────────────┘
               │ REST  /api/*  (actions, verify)    │ WebSocket /ws (server push)
   ┌───────────▼───────────────────────────────────▼──────────────┐
   │  frontend container (nginx)                                    │
   │  serves the built SPA, reverse-proxies /api and /ws → backend  │
   └───────────────────────────────┬──────────────────────────────┘
                                    │ internal docker network (quiet-cafe-net)
   ┌────────────────────────────────▼─────────────────────────────┐
   │  backend container (FastAPI, :8000)                            │
   │  sessions · real crypto · missions · tradecraft · event bus   │
   └───────────────────────────────┬──────────────────────────────┘
                                    │ SSH (paramiko), Missions 5
   ┌────────────────────────────────▼─────────────────────────────┐
   │  station-bravo container (Debian + OpenSSH)                    │
   └──────────────────────────────────────────────────────────────┘
```

**Why this shape:**

- The browser only ever talks to **one origin** (`:8080`). nginx proxies `/api`
  and `/ws` to the backend, so there's no CORS and no second exposed port.
- All the "magic" (real crypto, the live café, code release) is **server-side**,
  so confirmation codes are never in the page source and the simulation can stay
  consistent for everyone.
- The only genuinely networked piece is the SSH mission, isolated in its own
  container.

---

## 2. The two interaction systems

Everything the learner experiences is one of two things. Knowing which is which
tells you where to look.

| System | Direction | Transport | What it powers |
|---|---|---|---|
| **Actions** | client → server | REST (`POST /api/mission/{n}/action`) | The learner *doing* something: a decision, a checkpoint answer, a Tradecraft command. The server responds with the result. |
| **Live play** | server → client | WebSocket (`/ws`) | The café *reacting*: actor chatter, packets on the wire, Eve catching a key, "mission unlocked". The server pushes; the client animates. |

Client→server is deliberately kept on REST (easy to test, request/response is
clear). The WebSocket is **push-only** — the client never sends meaningful
messages up it.

---

## 3. Request lifecycle (follow one click)

A learner in Mission 3 picks a key to lock the message with:

1. **Frontend** — a button in `MissionPanels.tsx` calls
   `doAction("lock", {key_owner:"bob"})` from the store (`store.tsx`).
2. `api.ts` issues `POST /api/mission/3/action` with
   `{session_id, action:"lock", params:{key_owner:"bob"}}`.
3. **Backend** — `main.py` routes to `missions.handle(session, 3, "lock", params)`.
4. `missions.py` runs the **real** crypto (`crypto/pubkey.py`), decides whether
   this was the correct/incorrect path, and — on the correct path — returns the
   confirmation code.
5. Along the way it calls `manager.send(...)` (`ws.py`) to **push live events**
   (e.g. the packet to Bob, Eve recording noise).
6. **Frontend** — `store.tsx` reducer receives the REST result (updates the
   workspace) *and* the WebSocket events (animates the observation deck).
7. The learner submits the code; `POST /api/mission/3/verify` confirms it
   server-side, marks the mission complete, and unlocks the next.

---

## 4. Backend (`backend/app/`)

FastAPI app. In-memory state (single user per browser — perfect for laptop-local).

| File | Responsibility | Look here to… |
|---|---|---|
| `main.py` | FastAPI app + all routes (`/api/session`, `/enter`, `/action`, `/verify`, `/ws`). | Add/inspect an endpoint; see how actions and codes are dispatched. |
| `config.py` | **Single source of truth** for confirmation codes, mission metadata, checkpoints, the legit Mission-4 door, station settings. | Change a code, mission title, tagline, or a checkpoint's correct answer. |
| `session.py` | The `Session` dataclass + in-memory `SessionStore`. Holds per-session key material (lazily created in `ensure_keys()`). | See what state a session carries; add a new per-session secret. |
| `missions.py` | Per-mission **action handlers** — the "make them think" model: real decision, visible failure, code released only on the correct path. Also the shared deduction `_checkpoint`. | Change what a mission's main path does, or how a wrong choice plays out. |
| `tradecraft.py` | The engineer-focused **guided terminal** (one `tc` action for all six missions). Renders *real* CLI output from the session's actual keys; guidance-first (command shown + explained). | Edit a Tradecraft step, its command, explanation, or "what to notice". |
| `simulation.py` | Ambient **live-play loops** per room (the scripted background chatter/packets). Started on `enter`, cancelled on leave. | Change the café's ambient script or cadence. |
| `ws.py` | WebSocket connection manager; `manager.send(sid, type, **payload)` is how every live event is pushed. | See the event envelope `{type, room, ts, payload}`. |
| `ssh_client.py` | Real key-based SSH into `station-bravo` (paramiko). Generates a fresh session key, installs it via the baked bootstrap key, reconnects with the new key, reads the flag. | Anything about Mission 5's real login. |
| `crypto/` | The real cryptography (see below). | Change an algorithm or output format. |

### `crypto/` modules

| File | What's real | Used by |
|---|---|---|
| `symmetric.py` | AES-256-GCM encrypt/decrypt + tamper detection | Mission 2 |
| `pubkey.py` | RSA-2048 + OAEP **envelope** encryption (wraps an AES key, like TLS/PGP) | Mission 3 |
| `dh.py` | X25519 Diffie-Hellman — both sides derive the same secret | Mission 3 Tradecraft |
| `certs.py` | Two self-signed X.509 certs (legit vs impostor, different fingerprints) | Mission 4 |
| `totp.py` | RFC-6238 TOTP (pyotp) + a real nonce challenge/response "passkey" | Mission 6 |

> **Design rule:** crypto is *real where it's cheap and convincing*. Only the
> ambient chatter and Eve's password-guessing feed are scripted simulation.

---

## 5. Frontend (`frontend/src/`)

React + Vite + TypeScript, with framer-motion for the (now restrained) motion.
The build uses esbuild via Vite — no `tsc` gate — so loose types won't block a
build.

| File | Responsibility | Look here to… |
|---|---|---|
| `main.tsx` | React entry point. | — |
| `App.tsx` | App shell: header, mission nav, progress bar, phase switch (cold-open → playing → closed), the **sticky observation deck + scrolling workspace** layout. | Change overall layout or navigation. |
| `store.tsx` | Global state via `useReducer` + the WebSocket connection. Merges REST results and live events into one state. Exposes `enter`, `doAction`, `verify`, `reset`. | See how events become UI state; add a new piece of state. |
| `api.ts` | Thin REST client (`/api/...`). | Add/inspect an endpoint call. |
| `types.ts` | Shared TS types (`SessionState`, `WSEvent`, `ChatBubble`, `Packet`, `Actor`). | Match a backend payload shape. |
| `missionsMeta.ts` | **All learner-facing copy**: titles, seats, narration, Recall (talk callbacks), Predict prompts, hints, debriefs, checkpoint questions/options. | Edit any wording without touching logic. |
| `components/Stage.tsx` | The observation deck: three actor panes + the wire. Eve shows a calm idle state when she has nothing to do. | Change the live-play visuals. |
| `components/MissionPanels.tsx` | The six interactive panels (decisions, key choices, cert comparison, the guided terminal mount). | Change a mission's on-screen controls. |
| `components/MissionConsole.tsx` | The workspace flow wrapper: Recall → Predict → action → checkpoint → debrief + the **Next challenge** button; auto-verifies earned codes. | Change the per-mission rhythm. |
| `components/ui.tsx` | Reusable primitives: `Recall`, `Predict`, the guided `Terminal`, buttons, etc. | Edit the Recall ribbon, Predict gate, or terminal behavior. |
| `components/Screens.tsx` | The cold-open briefing and the "Case Closed" wrap-up. | Change the intro/outro. |
| `index.css` | The café-noir theme + all component styles. | Restyle anything. |

---

## 6. Live-play event reference

Every live event is pushed by the backend via `manager.send` with this envelope:

```json
{ "type": "actor.message", "room": "open_floor", "ts": 1700000000.0,
  "payload": { "from": "alice", "to": "bob", "text": "...", "encrypted": false } }
```

Common event types (consumed by the reducer in `store.tsx`):

| `type` | Meaning / pane effect |
|---|---|
| `connected` | WebSocket handshake acknowledged. |
| `actor.message` | A speech bubble appears in an actor pane. |
| `packet.sent` | A packet animates onto the wire (encrypted → rendered as noise). |
| `key.exposed` | Eve catches a key crossing the wire (her real moment). |
| `eve.capture` | Eve's recorder shows captured noise. |
| `mission.unlocked` | Server confirms a verified code; next mission opens. |

To add a new live reaction: emit it from `missions.py`/`simulation.py` with
`manager.send`, then handle the `type` in the `store.tsx` reducer.

---

## 7. The "make them think" model (per mission)

Each mission follows the same rhythm; the content lives in `missionsMeta.ts`
(copy) and `missions.py` + `config.py` (logic/answers):

1. **Recall** — quotes the exact slide/concept from the talk (anchors the lab to
   what they heard).
2. **Predict** — they commit a hypothesis before acting; the action stays locked
   until they do.
3. **Decision / action** — a real, tempting choice with a possible wrong answer.
   The mistake **plays out on the live stage**, then they retry.
4. **Checkpoint** — a server-validated deduction question (answers never ship to
   the client; see `config.CHECKPOINTS`).
5. **Code** — released by the server **only on the genuinely correct path**, then
   confirmed via `/verify`.

**Tradecraft** is the optional engineer deep-end for each mission: a guided
terminal where they run *real* commands (openssl, ssh-keygen, oathtool,
tcpdump…) and get real output from the session's keys. It's guidance-first — the
command is shown and explained, so nobody has to guess in a timed room.

---

## 8. Confirmation codes (the "flags")

- Defined **only** in `backend/app/config.py` (`CODES`).
- Released by the server when the corresponding task genuinely completes; Mission
  5's code also physically lives on `station-bravo` and is read over real SSH.
- Verified at `POST /api/mission/{n}/verify` — never compared client-side, so
  they can't be found by viewing source.

---

## 9. Containers & networking

`docker-compose.yml` defines three services on the `quiet-cafe-net` network:

| Service | Base | Exposes | Notes |
|---|---|---|---|
| `frontend` | `nginx:alpine` (multi-stage: node build → nginx) | `8080:80` | Serves the SPA; proxies `/api` + `/ws` to backend (`frontend/nginx.conf`). |
| `backend` | `python:3.12-slim` + openssl/oathtool/openssh-client | internal `8000` | Reaches the station via `STATION_HOST`/`STATION_PORT` env. |
| `station-bravo` | Debian + OpenSSH | internal `22` | Bootstrap public key baked in so the backend can install session keys. |

Only `8080` is published. No runtime internet needed.

---

## 10. Where to make common changes

| I want to… | Edit |
|---|---|
| Change a confirmation code | `backend/app/config.py` → `CODES` |
| Reword narration / hints / debriefs | `frontend/src/missionsMeta.ts` |
| Change a mission's correct answer / checkpoint | `backend/app/config.py` + `backend/app/missions.py` |
| Edit a Tradecraft command or explanation | `backend/app/tradecraft.py` |
| Change the café's ambient chatter | `backend/app/simulation.py` → `SCRIPTS` |
| Restyle the UI / theme | `frontend/src/index.css` |
| Change the page layout (deck vs workspace) | `frontend/src/App.tsx` |
| Add a new live animation | emit in `missions.py`/`simulation.py`, handle in `store.tsx` |
| Touch the real SSH flow | `backend/app/ssh_client.py` + `station-bravo/Dockerfile` |

---

## 11. Notes & gotchas

- **Single-user state is in memory.** Restarting the backend clears all sessions
  (intended for laptop-local use). Don't expect multi-tenant persistence.
- **Frontend wasn't compiled in-place** during authoring (no local npm
  registry). The first `docker compose build` runs the real `npm install &&
  vite build`; if a dependency version needs nudging, it surfaces there.
- **Ambient loops must be cancelled on room change** — `simulation.start`
  cancels any prior loop so navigating between missions can't leak tasks or
  duplicate chatter.
- **Errors never leak stack traces to the room** — `main.py`'s action handler
  returns a friendly in-character message on exception.
