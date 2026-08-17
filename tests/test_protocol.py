"""Protocol / server tests over real WebSockets (uvicorn subprocess)."""

import asyncio
import json
import random
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest
import websockets

ROOT = Path(__file__).resolve().parent.parent


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.fixture(scope="module")
def server():
    port = free_port()
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "server:app", "--host", "127.0.0.1", "--port", str(port)],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    url = f"ws://127.0.0.1:{port}/ws"
    for _ in range(80):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.3):
                break
        except OSError:
            time.sleep(0.2)
    else:
        proc.kill()
        raise RuntimeError("server did not start")
    yield url
    proc.terminate()
    proc.wait(timeout=10)


class Client:
    def __init__(self, ws, pid):
        self.ws = ws
        self.pid = pid
        self.state = None

    async def send(self, obj):
        await self.ws.send(json.dumps(obj))

    async def send_raw(self, text):
        await self.ws.send(text)

    async def recv(self, timeout=5):
        return json.loads(await asyncio.wait_for(self.ws.recv(), timeout))

    async def recv_until(self, pred, timeout=15):
        while True:
            msg = await self.recv(timeout)
            if msg["type"] == "state" or msg["type"] == "joined":
                self.state = msg["state"]
                if pred(msg["state"]):
                    return msg["state"]


async def join(url, name, room_id=None):
    ws = await websockets.connect(url)
    await ws.send(json.dumps({"type": "join", "name": name, "roomId": room_id or ""}))
    msg = json.loads(await ws.recv())
    assert msg["type"] == "joined", msg
    c = Client(ws, msg["yourId"])
    c.state = msg["state"]
    return c, msg["roomId"]


# ------------------------------------------------------------------- basics

@pytest.mark.asyncio
async def test_create_room_and_reject_bad_join(server):
    a, room = await join(server, "Ana")
    assert room and a.pid
    # join with wrong room code
    ws = await websockets.connect(server)
    await ws.send(json.dumps({"type": "join", "name": "X", "roomId": "zzzzzz"}))
    msg = json.loads(await ws.recv())
    assert msg["type"] == "error" and "no encontrada" in msg["message"]
    await ws.close()


@pytest.mark.asyncio
async def test_two_players_same_room(server):
    a, room = await join(server, "Ana")
    _, room2 = await join(server, "Beto", room)
    assert room == room2
    # broadcast after b joined reaches a
    st = await a.recv_until(lambda s: len(s["players"]) == 2)
    assert {p["name"] for p in st["players"]} == {"Ana", "Beto"}


@pytest.mark.asyncio
async def test_malformed_json_ignored(server):
    a, room = await join(server, "Ana")
    await a.send_raw("este no es json")
    await a.send_raw("{invalid")
    # connection still alive
    b, _ = await join(server, "Beto", room)
    st = await b.recv_until(lambda s: len(s["players"]) == 2)
    assert len(st["players"]) == 2


@pytest.mark.asyncio
async def test_messages_before_join_ignored(server):
    ws = await websockets.connect(server)
    await ws.send(json.dumps({"type": "start"}))  # before join
    await ws.send(json.dumps({"type": "chat", "text": "hola"}))
    await ws.send(json.dumps({"type": "join", "name": "Tardio"}))
    msg = json.loads(await ws.recv())
    assert msg["type"] == "joined"
    await ws.close()


@pytest.mark.asyncio
async def test_start_requires_2_players(server):
    a, _ = await join(server, "Solo")
    await a.send({"type": "start"})
    # start is ignored with < 2 players: phase stays lobby
    await a.send({"type": "chat", "text": "ping"})
    st = await a.recv_until(lambda s: s["chat"] and s["chat"][-1]["text"] == "ping")
    assert st["phase"] == "lobby"
    assert st["players"][0]["name"] == "Solo"


@pytest.mark.asyncio
async def test_non_host_cannot_start(server):
    _, room = await join(server, "Ana")
    b, _ = await join(server, "Beto", room)
    await b.send({"type": "start"})  # b is not host
    await b.send({"type": "chat", "text": "ping"})
    st = await b.recv_until(lambda s: s["chat"] and s["chat"][-1]["text"] == "ping")
    assert st["phase"] == "lobby"


@pytest.mark.asyncio
async def test_join_started_game_rejected(server):
    a, room = await join(server, "Ana")
    b, _ = await join(server, "Beto", room)
    await a.send({"type": "start"})
    await a.recv_until(lambda s: s["phase"] == "selecting")
    # pick professions
    await a.send({"type": "choose_profession", "value": "janitor"})
    await b.send({"type": "choose_profession", "value": "doctor"})
    await a.recv_until(lambda s: s["phase"] == "playing")
    # third player tries to join
    ws = await websockets.connect(server)
    await ws.send(json.dumps({"type": "join", "name": "Tarde", "roomId": room}))
    msg = json.loads(await ws.recv())
    assert msg["type"] == "error" and "comenzó" in msg["message"]
    await ws.close()


@pytest.mark.asyncio
async def test_chat_capped_length(server):
    a, _ = await join(server, "Ana")
    await a.send({"type": "chat", "text": "x" * 5000})
    st = await a.recv_until(lambda s: s["chat"])
    assert len(st["chat"][-1]["text"]) <= 300


@pytest.mark.asyncio
async def test_disconnect_marks_player(server):
    a, room = await join(server, "Ana")
    b, _ = await join(server, "Beto", room)
    await b.ws.close()
    st = await a.recv_until(lambda s: any(not p["connected"] for p in s["players"]))
    assert next(p for p in st["players"] if p["name"] == "Beto")["connected"] is False


@pytest.mark.asyncio
async def test_two_rooms_isolated(server):
    a1, r1 = await join(server, "A1")
    a2, r2 = await join(server, "A2")
    assert r1 != r2
    _, _ = await join(server, "B1", r1)
    st1 = await a1.recv_until(lambda s: len(s["players"]) == 2)
    assert len(st1["players"]) == 2 and all(p["name"] in {"A1", "B1"} for p in st1["players"])
    # room2 still has only its player
    st2 = await a2.recv_until(lambda s: len(s["players"]) == 1, timeout=1)
    await a2.send({"type": "chat", "text": "ping"})
    st2 = await a2.recv_until(lambda s: s["chat"] and s["chat"][-1]["text"] == "ping")
    assert len(st2["players"]) == 1


# ------------------------------------------------------------------- full game

class Bot(Client):
    async def play(self):
        while True:
            st = await self.recv_until(
                lambda s: s["phase"] == "over" or (s["pending"] and s["pending"]["playerId"] == self.pid)
            )
            if st["phase"] == "over":
                return
            pend = st["pending"]
            if pend["kind"] == "roll":
                await self.send({"type": "roll"})
                continue
            if pend["kind"] == "continue":
                await self.send({"type": "continue"})
                continue
            lc = st.get("lastCard") or {}
            deck = lc.get("deck")
            rng = random
            val = {"buy": False}
            if deck in ("small", "big"):
                card = lc["card"]
                if card["kind"] == "stock":
                    val = {"shares": rng.randint(0, min(10, lc.get("maxShares", 0)))}
                else:
                    me = next(p for p in st["players"] if p["id"] == self.pid)
                    val = {"buy": rng.random() < 0.6 and me["cash"] >= card["down"]}
            elif deck == "doodad":
                val = {"buy": False}
            elif deck == "charity":
                val = {"pay": False}
            elif deck == "market":
                if lc["card"]["kind"] == "stockBuy":
                    val = {"shares": rng.randint(0, min(10, lc.get("maxShares", 0)))}
            elif deck == "marketSell":
                if lc["kind"] == "realEstate":
                    a = lc["assets"][0]
                    val = {"assetId": a["id"], "price": a["resale"][1]}
                elif lc["kind"] == "business":
                    a = lc["assets"][0]
                    val = {"assetId": a["id"], "multiplier": lc["card"]["multiplier"][1]}
                else:
                    val = {"price": lc["priceRange"][1]}
            await self.send({"type": "choice", "value": val})


@pytest.mark.asyncio
async def test_full_game_over_websockets(server):
    a, room = await join(server, "Ana")
    b, _ = await join(server, "Beto", room)
    c, _ = await join(server, "Carlos", room)
    await a.send({"type": "start"})
    await a.recv_until(lambda s: s["phase"] == "selecting")
    await a.send({"type": "choose_profession", "value": "janitor"})
    await b.send({"type": "choose_profession", "value": "teacher"})
    await c.send({"type": "choose_profession", "value": "engineer"})
    # wait until all chose -> playing
    await a.recv_until(lambda s: s["phase"] == "playing")
    # everyone bots until game over
    bots = [Bot(a.ws, a.pid), Bot(b.ws, b.pid), Bot(c.ws, c.pid)]
    await asyncio.gather(*(bot.play() for bot in bots), return_exceptions=True)
    # final state must show over + winner
    st = await a.recv_until(lambda s: s["phase"] == "over", timeout=30)
    assert st["phase"] == "over"
    assert st["winnerId"] is not None
    winner = next(p for p in st["players"] if p["won"])
    assert winner["id"] == st["winnerId"]
