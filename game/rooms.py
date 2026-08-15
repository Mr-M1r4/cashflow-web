"""Room and connection management."""

import asyncio
import json
import uuid

from .engine import Game


class RoomManager:
    def __init__(self):
        self.rooms = {}

    def create_room(self):
        room_id = uuid.uuid4().hex[:6]
        room = Room(room_id)
        self.rooms[room_id] = room
        return room

    def get(self, room_id):
        return self.rooms.get(room_id)


class Room:
    def __init__(self, room_id):
        self.room_id = room_id
        self.host = None
        self.players = {}  # pid -> {name, ws, connected}
        self.chat = []
        self.game = Game(self)
        self._input_event = asyncio.Event()
        self._send_locks = {}
        self.game_started = False

    # ------------------------------------------------------------- connections

    def add_player(self, ws, name):
        pid = uuid.uuid4().hex[:8]
        self.players[pid] = {"name": name, "ws": ws, "connected": True}
        if self.host is None:
            self.host = pid
        self.game.add_player(pid, name)
        self._send_locks[ws] = asyncio.Lock()
        return pid

    def remove_player(self, ws):
        for pid, info in list(self.players.items()):
            if info["ws"] is ws:
                info["connected"] = False
                info["ws"] = None
                for p in self.game.players:
                    if p["id"] == pid:
                        p["connected"] = False
                if self.host == pid:
                    next_host = next((i for i, q in self.players.items() if q["connected"]), None)
                    self.host = next_host
                break
        self.broadcast_state()

    # ----------------------------------------------------------------- sending

    async def _send(self, ws, obj):
        lock = self._send_locks.get(ws)
        if lock is None:
            return
        async with lock:
            try:
                await ws.send_text(json.dumps(obj, ensure_ascii=False))
            except Exception:  # noqa: BLE001, S110 - socket gone mid-send; ignore
                pass

    def broadcast_state(self):
        state = self.game.state()
        for pid, info in list(self.players.items()):
            if info["connected"] and info["ws"] is not None:
                asyncio.ensure_future(self._send(info["ws"], {"type": "state", "state": state, "yourId": pid}))

    async def send_to(self, pid, obj):
        info = self.players.get(pid)
        if info and info["connected"] and info["ws"] is not None:
            await self._send(info["ws"], obj)

    def new_input_event(self):
        return self._input_event.wait()

    # ----------------------------------------------------------------- messages

    async def handle_message(self, ws, pid, msg):
        t = msg.get("type")
        if t == "chat":
            text = (msg.get("text") or "").strip()[:300]
            if text:
                self.chat.append({"name": self.players[pid]["name"], "text": text})
                self.broadcast_state()
        elif t == "choose_profession":
            if self.game.phase != "selecting":
                return
            self.game.choose_profession(pid, msg.get("value"))
            if self.game.all_chose() and not self.game_started:
                self.game_started = True
                asyncio.ensure_future(self.game.begin())
            else:
                self.broadcast_state()
        elif t == "start":
            if pid == self.host and self.game.phase == "lobby" and len(self.players) >= 2:
                self.game.start_selection()
        elif t in ("roll", "choice"):
            if self.game.phase in ("playing", "over"):
                self.game._push_msg(pid, msg)
                self._input_event.set()
