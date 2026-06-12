# Operation Quiet Café

An interactive, story-driven lab where a mixed room (product owners → engineers)
*applies* the ideas from the **"How the Internet Keeps Secrets"** talk. You play
Eve, then Alice, then Bob across six missions while the café plays out live
around you. Everything runs in the browser — no terminal required.

---

## Run it

You need **Docker Desktop** (or Docker Engine + Compose) installed and running.

From this folder:

```bash
docker compose up --build
```

Wait for the three containers to report ready, then open:

### → http://localhost:8080

That's the whole experience. Only port **8080** is published; the lab needs
**no internet access at runtime**.

---

## Resetting between sessions

- **One person, fresh start:** click **Reset** (top-right). Clears that
  browser's progress only.
- **Full wipe before a new group** (new keys, certs, and state for everyone):
  ```bash
  docker compose down && docker compose up --build
  ```

---

## Running on laptops with no internet

The first build needs network (to pull base images and dependencies). To run on
air-gapped laptops, build once on a connected machine and ship the images:

```bash
# on a connected machine:
docker compose build
docker save quiet-cafe-frontend quiet-cafe-backend quiet-cafe-station-bravo \
  -o quiet-cafe-images.tar

# on each target laptop:
docker load -i quiet-cafe-images.tar
docker compose up
```

(Image names may be prefixed by your Compose project name — check `docker images`
and adjust.)

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `localhost:8080` won't load | Give it ~20s after `up`; confirm all three containers are running with `docker compose ps`. |
| Port 8080 already in use | Stop the other process, or change the left side of `"8080:80"` in `docker-compose.yml`. |
| Mission 5 (SSH) fails | Make sure `station-bravo` is healthy: `docker compose ps`. A full restart (`down` then `up`) usually clears it. |
| Progress stuck / weird state | Click **Reset**, or do a full wipe (see above). |

---

## More documentation

- **`docs/ARCHITECTURE.md`** — how the whole thing works and where to find what
  (for anyone extending or maintaining the lab).
- **`facilitator/RUN_SHEET.md`** — answer key + run-of-show for whoever is
  leading the session. **Keep this one private.**
