# Operation Quiet Café — Interactive Lab

A guided, story-driven lab that lets a mixed room (POs → engineers) *apply* the
ideas from the "How the Internet Keeps Secrets" talk. You step into Eve, then
Alice, then Bob across six missions while the rest of the café plays out live
around you. No terminal required — the browser is the whole experience.

## Run it (one command)

```bash
docker compose up --build
```

Then open **http://localhost:8080**.

That's it. Three containers come up:

| Service | What it is |
|---|---|
| `frontend` | The React lab UI (nginx), served on :8080. Proxies `/api` + `/ws` to the backend. |
| `backend` | FastAPI: session state, **real** crypto, the live-play event bus. |
| `station-bravo` | A real SSH server the team logs into for Missions 5–6. |

Only port **8080** is published. Everything else talks over the internal Docker
network. The lab needs **no internet access at runtime**.

## What's real vs. simulated

Real (genuinely executed on the backend):
- AES-256-GCM symmetric encryption / decryption + tamper detection (Mission 2)
- RSA-2048 + OAEP envelope public-key encryption (Mission 3)
- X25519 Diffie-Hellman key agreement (Mission 3 tradecraft)
- Self-signed X.509 certificate generation + inspection (Mission 4)
- Real key-based SSH login into `station-bravo` via paramiko (Mission 5)
- RFC-6238 TOTP + a real challenge/response "passkey" signature (Mission 6)

Simulated (scripted for immersion):
- The ambient actor chatter and packet flow on the wire
- Eve's password-guessing feed in Mission 5

## The six missions

| # | Room | You are | Concept | Code |
|---|------|---------|---------|------|
| 1 | The Open Floor | Eve | data is a postcard | `QC{walls_have_ears}` |
| 2 | The Cipher Bench | Alice | symmetric encryption + the key-sharing wall | `QC{but_how_do_i_share_the_key}` |
| 3 | The Key Exchange | Alice | public/private keys | `QC{eve_recorded_only_noise}` |
| 4 | The Hall of Padlocks | Alice | certificates ≠ trust | `QC{a_padlock_proves_nothing}` |
| 5 | Station Bravo | Bob | SSH key-based login | `QC{my_secret_never_left_home}` |
| 6 | The Vault | Bob | TOTP + passwordless | `QC{the_password_is_dead}` |

Codes are validated **server-side** — they're never in the page source, and the
only way to get one is to actually complete the task.

## Resetting between sessions

- In-app: the **Reset** button (top-right) clears progress for that browser.
- Full wipe (fresh keys/certs/state for everyone):
  ```bash
  docker compose down && docker compose up --build
  ```

## Offline / air-gapped laptops

First `--build` needs network (to pull base images + npm/pip deps). To run on
laptops with no network, pre-build once on a connected machine and ship images:

```bash
docker compose build
docker save quiet-cafe-frontend quiet-cafe-backend quiet-cafe-station-bravo -o quiet-cafe-images.tar
# on the target laptop:
docker load -i quiet-cafe-images.tar
docker compose up
```
(Image names may be prefixed by your compose project; adjust to `docker images` output.)

## Project layout

```
operation-quiet-cafe/
├─ docker-compose.yml
├─ backend/        FastAPI app (app/), real crypto (app/crypto/), SSH, missions
├─ frontend/       React + Vite + framer-motion SPA (src/)
├─ station-bravo/  Debian + OpenSSH target
└─ facilitator/    RUN_SHEET.md — answer key + run-of-show (keep private)
```

## Notes for whoever extends this

- Mission content (narration, hints, debriefs) lives in
  `frontend/src/missionsMeta.ts` — edit copy without touching logic.
- Backend codes + mission metadata live in `backend/app/config.py`.
- The live-play events are documented inline in `backend/app/ws.py` /
  `simulation.py` and consumed by the reducer in `frontend/src/store.tsx`.
- The frontend build uses esbuild via Vite (no `tsc` gate), so it builds even
  with loose types; tighten `tsconfig.json` if you want stricter checks.
- This project was authored without a local npm registry, so the frontend was
  not compiled in-place. The first `docker compose build` performs the real
  `npm install && vite build`; if any dependency version needs nudging, it'll
  surface there.
