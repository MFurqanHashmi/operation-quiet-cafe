# Facilitator Run-Sheet — Operation Quiet Café
**Keep this private. It contains the answer key.**

## Before the room arrives
- [ ] On each laptop (or a shared host): `docker compose up --build` from the project root.
- [ ] Confirm http://localhost:8080 loads and shows the "Operation Quiet Café" cold-open.
- [ ] 30-second smoke test (see bottom) passes.
- [ ] Have this sheet open on your own screen only.

## Timing (target ~45–55 min hands-on, after the 30-min talk)
| Beat | Time |
|---|---|
| Cold-open + "how you'll work" | 3 min |
| M1 Open Floor (Eve) | 5 min |
| M2 Cipher Bench (Alice) | 7 min |
| M3 Key Exchange (Alice) | 8 min |
| M4 Hall of Padlocks (Alice) | 7 min |
| M5 Station Bravo (Bob) | 8 min |
| M6 The Vault (Bob) | 7 min |
| Case Closed debrief | 5 min |

Don't gate on time — the codes are the checkpoint, not the clock. If a table is
flying, point them at the **Tradecraft** drop-downs (real tools + docs).

## Answer key (the confirmation codes)
| # | Code | Surfaces when… |
|---|------|----------------|
| 1 | `QC{walls_have_ears}` | They tap the wire; it's in Alice's third line. |
| 2 | `QC{but_how_do_i_share_the_key}` | Bob's reply, after a real decrypt of their message. |
| 3 | `QC{eve_recorded_only_noise}` | Bob's reply via the public-key path. |
| 4 | `QC{a_padlock_proves_nothing}` | Walking through the legit door (Door A). |
| 5 | `QC{my_secret_never_left_home}` | Read off Station Bravo after key-based SSH login. |
| 6 | `QC{the_password_is_dead}` | Vault opens after the passwordless challenge verifies. |

## The three-act arc (what to reinforce out loud)
1. **Eve (M1):** the problem — open networks are postcards.
2. **Alice (M2–M4):** the fixes — scramble it, swap keys without sharing a secret, verify *who* you're talking to.
3. **Bob (M5–M6):** the defense — kill the password, so there's nothing left to steal.
The M2 → M3 cliffhanger ("but how did Bob get the key?!") is the spine. Let them feel the wall in M2 before relieving it in M3.

## Recovery / facilitation tips
- **Click any mission number** in the top bar to jump there (e.g. to demo, or unstick a table).
- Each mission has progressive **"Stuck?"** nudges — encourage those before you step in.
- A wrong code gives an in-character nudge; reassure them it means re-run the task, not that they typed it wrong.
- **Reset** (top-right) wipes that browser's progress; `docker compose down && up` wipes everything (fresh keys/certs).
- If Station Bravo is slow on first hit, M5 may take a few seconds — that's the real SSH round-trip.

## 30-second smoke test (backend reachable + codes wired)
```bash
SID=$(curl -s -XPOST localhost:8080/api/session | python3 -c "import sys,json;print(json.load(sys.stdin)['session_id'])")
curl -s -XPOST localhost:8080/api/mission/1/enter -H 'Content-Type: application/json' -d "{\"session_id\":\"$SID\"}" >/dev/null
curl -s -XPOST localhost:8080/api/mission/1/action -H 'Content-Type: application/json' -d "{\"session_id\":\"$SID\",\"action\":\"tap\"}" | grep -q 'walls_have_ears' && echo "M1 OK" || echo "M1 FAIL"
curl -s -XPOST localhost:8080/api/mission/1/verify -H 'Content-Type: application/json' -d "{\"session_id\":\"$SID\",\"code\":\"QC{walls_have_ears}\"}" | grep -q '"correct": true' && echo "VERIFY OK" || echo "VERIFY FAIL"
```
Expected: `M1 OK` then `VERIFY OK`.
