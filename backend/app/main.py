"""Operation Quiet Cafe — FastAPI backend entrypoint."""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Body
from fastapi.responses import JSONResponse

from . import config, simulation, missions
from .session import store
from .ws import manager

app = FastAPI(title="Operation Quiet Cafe")


@app.get("/api/health")
async def health():
    return {"ok": True, "missions": config.TOTAL_MISSIONS}


@app.post("/api/session")
async def create_session():
    s = store.create()
    return s.to_public()


@app.get("/api/session/{sid}")
async def get_session(sid: str):
    s = store.get(sid)
    if not s:
        return JSONResponse({"error": "not found"}, status_code=404)
    return s.to_public()


@app.post("/api/reset")
async def reset(body: dict = Body(default={})):
    sid = body.get("session_id")
    await simulation.stop(sid or "")
    s = store.reset(sid) if sid else store.create()
    return s.to_public()


@app.get("/api/missions")
async def list_missions():
    return config.MISSIONS


@app.post("/api/mission/{n}/enter")
async def enter(n: int, body: dict = Body(default={})):
    s = store.get(body.get("session_id"))
    if not s:
        return JSONResponse({"error": "no session"}, status_code=400)
    meta = config.MISSIONS.get(n)
    if not meta:
        return JSONResponse({"error": "no such mission"}, status_code=404)
    await simulation.start(s.id, meta["room"])
    return {"ok": True, "mission": n, "meta": meta}


@app.post("/api/mission/{n}/action")
async def action(n: int, body: dict = Body(...)):
    s = store.get(body.get("session_id"))
    if not s:
        return JSONResponse({"error": "no session"}, status_code=400)
    try:
        result = await missions.handle(s, n, body.get("action", ""),
                                       body.get("params", {}))
    except Exception as e:  # noqa - never leak a stack trace to the room
        return JSONResponse(
            {"ok": False, "error": "Something jammed at the backend. Try again."},
            status_code=200,
        )
    return result


@app.post("/api/mission/{n}/verify")
async def verify(n: int, body: dict = Body(...)):
    s = store.get(body.get("session_id"))
    if not s:
        return JSONResponse({"error": "no session"}, status_code=400)
    code = (body.get("code") or "").strip()
    expected = config.CODES.get(n)
    if expected and code == expected:
        s.completed.add(n)
        s.codes_verified.add(n)
        s.current_mission = min(n + 1, config.TOTAL_MISSIONS)
        await manager.send(s.id, "mission.unlocked", mission=n)
        nxt = n + 1 if n < config.TOTAL_MISSIONS else None
        return {"ok": True, "correct": True, "next": nxt,
                "state": s.to_public()}
    return {"ok": True, "correct": False,
            "nudge": "That's not the code on record. Re-run the task — the real "
                     "code only appears when the work actually lands."}


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    sid = ws.query_params.get("session")
    if not sid or not store.get(sid):
        await ws.close(code=1008)
        return
    await manager.connect(sid, ws)
    try:
        await manager.send(sid, "connected", room="")
        while True:
            await ws.receive_text()  # client->server kept on REST; ignore pings
    except WebSocketDisconnect:
        await manager.disconnect(sid)
    except Exception:
        await manager.disconnect(sid)
