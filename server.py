"""Cashflow web server: FastAPI + WebSocket + static files."""

import json
import logging

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles

from game.rooms import RoomManager

log = logging.getLogger("cashflow")

app = FastAPI(title="Cashflow Online")
manager = RoomManager()


@app.get("/healthz")
async def healthz():
    return {"ok": True}


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    pid = None
    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                continue  # ignore malformed frames
            if msg.get("type") == "join":
                name = (msg.get("name") or "Jugador").strip()[:20] or "Jugador"
                room_id = (msg.get("roomId") or "").strip()
                room = manager.get(room_id) if room_id else None
                if room_id and room is None:
                    await ws.send_text(json.dumps({"type": "error", "message": "Sala no encontrada"}, ensure_ascii=False))
                    continue
                if room is not None and room.game.phase != "lobby":
                    await ws.send_text(json.dumps({"type": "error", "message": "La partida ya comenzó"}, ensure_ascii=False))
                    continue
                if room is None:
                    room = manager.create_room()
                pid = room.add_player(ws, name)
                await ws.send_text(json.dumps({
                    "type": "joined",
                    "yourId": pid,
                    "roomId": room.room_id,
                    "isHost": pid == room.host,
                    "state": room.game.state(),
                }, ensure_ascii=False))
                room.broadcast_state()
            elif pid is not None:
                room = next((r for r in manager.rooms.values() if pid in r.players), None)
                if room is not None:
                    try:
                        await room.handle_message(ws, pid, msg)
                    except Exception:  # a bad message must never kill the connection
                        log.exception("error manejando mensaje del cliente")
    except WebSocketDisconnect:
        pass
    finally:
        if pid is not None:
            room = next((r for r in manager.rooms.values() if pid in r.players), None)
            if room is not None:
                room.remove_player(ws)


app.mount("/", StaticFiles(directory="public", html=True), name="static")
