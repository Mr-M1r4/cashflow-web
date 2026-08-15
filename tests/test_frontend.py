"""Frontend smoke test with a real headless browser (Brave/Chromium) via CDP."""

import asyncio
import json
import socket
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import pytest
import websockets

ROOT = Path(__file__).resolve().parent.parent
BRAVE = "/opt/brave.com/brave/brave-browser"


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def wait_port(port, tries=60):
    for _ in range(tries):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.3):
                return True
        except OSError:
            time.sleep(0.25)
    return False


@pytest.fixture(scope="module")
def server_url():
    port = free_port()
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "server:app", "--host", "127.0.0.1", "--port", str(port)],
        cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    assert wait_port(port), "server did not start"
    yield f"http://127.0.0.1:{port}"
    proc.terminate()
    proc.wait(timeout=10)


@pytest.fixture(scope="module")
def browser():
    if not Path(BRAVE).exists():
        pytest.skip("Brave no disponible")
    port = free_port()
    profile = f"/tmp/opencode/brave-{port}"
    import shutil
    shutil.rmtree(profile, ignore_errors=True)
    proc = subprocess.Popen(
        [BRAVE, "--headless=new", "--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage",
         "--no-first-run", "--no-default-browser-check",
         f"--remote-debugging-port={port}", f"--user-data-dir={profile}",
         "about:blank"],
        stdout=subprocess.DEVNULL, stderr=open(f"/tmp/opencode/brave-test-{port}.log", "w"),  # noqa: SIM115 - kept open for process lifetime
    )
    assert wait_port(port, tries=160), "browser did not start"
    yield port
    proc.terminate()
    proc.wait(timeout=10)


class CDP:
    def __init__(self, ws_url):
        self.ws_url = ws_url
        self._next_id = 0
        self._pending = {}
        self.errors = []
        self._recv_task = None

    async def connect(self):
        self.ws = await websockets.connect(self.ws_url)
        self._recv_task = asyncio.ensure_future(self._recv_loop())

    async def _recv_loop(self):
        try:
            while True:
                msg = json.loads(await self.ws.recv())
                if "id" in msg:
                    fut = self._pending.pop(msg["id"], None)
                    if fut and not fut.done():
                        fut.set_result(msg)
                elif msg.get("method") == "Runtime.exceptionThrown":
                    d = msg["params"]["exceptionDetails"]
                    self.errors.append("EXC: " + d.get("text", "") + " " + str(d.get("exception", {}).get("description", ""))[:300])
                elif msg.get("method") == "Runtime.consoleAPICalled":
                    if msg["params"]["type"] == "error":
                        text = " ".join(str(a.get("value", a.get("description", ""))) for a in msg["params"]["args"])
                        self.errors.append("CONSOLE: " + text[:300])
        except Exception:  # noqa: BLE001, S110 - background listener; stop on close
            pass

    async def cmd(self, method, params=None):
        self._next_id += 1
        fut = asyncio.get_event_loop().create_future()
        self._pending[self._next_id] = fut
        await self.ws.send(json.dumps({"id": self._next_id, "method": method, "params": params or {}}))
        resp = await asyncio.wait_for(fut, 15)
        if "error" in resp:
            raise RuntimeError(f"CDP error {method}: {resp['error']}")
        return resp.get("result", {})

    async def enable(self):
        await self.cmd("Runtime.enable")
        await self.cmd("Page.enable")

    async def eval(self, expr):
        r = await self.cmd("Runtime.evaluate", {"expression": expr, "returnByValue": True, "awaitPromise": True})
        if r.get("exceptionDetails"):
            raise RuntimeError(f"JS error: {r['exceptionDetails']['text']}")
        return r.get("result", {}).get("value")

    async def wait_js(self, expr, timeout=15):
        deadline = time.time() + timeout
        while time.time() < deadline:
            if await self.eval(expr):
                return True
            await asyncio.sleep(0.2)
        raise TimeoutError(f"JS condition never true: {expr}")


def open_tab(port, url):
    req = urllib.request.Request(f"http://127.0.0.1:{port}/json/new?{urllib.parse.quote(url, safe='')}", method="PUT")
    with urllib.request.urlopen(req, timeout=5) as resp:
        return json.loads(resp.read())


@pytest.mark.asyncio
async def test_frontend_renders_and_plays(server_url, browser):
    tab = open_tab(browser, server_url)
    cdp = CDP(tab["webSocketDebuggerUrl"])
    await cdp.connect()
    await cdp.enable()

    tab2 = open_tab(browser, server_url)
    cdp2 = CDP(tab2["webSocketDebuggerUrl"])
    await cdp2.connect()
    await cdp2.enable()

    # --- host creates a room
    await cdp.wait_js("document.readyState === 'complete' && !!document.getElementById('lobby-name')")
    await cdp.eval("document.getElementById('lobby-name').value = 'Ana'")
    await cdp.eval("document.getElementById('btn-create').click()")
    await cdp.wait_js("!document.getElementById('game').classList.contains('hidden')")
    room = await cdp.eval("document.getElementById('room-id').textContent")
    assert room and len(room) == 6
    # la ventana de ingreso debe OCULTARSE de verdad (no solo quitar una clase)
    assert await cdp.eval("getComputedStyle(document.getElementById('lobby')).display === 'none'")
    assert await cdp.eval("getComputedStyle(document.getElementById('game')).display !== 'none'")

    # solo con 1 jugador se muestra el aviso de espera (y no el botón de inicio)
    assert await cdp.eval("!document.getElementById('waiting-hint').classList.contains('hidden')")
    assert "mínimo 2" in await cdp.eval("document.getElementById('waiting-hint').textContent")
    assert await cdp.eval("document.getElementById('btn-start').classList.contains('hidden')")

    # --- second player joins the same room
    await cdp2.wait_js("document.readyState === 'complete' && !!document.getElementById('lobby-name')")
    await cdp2.eval("document.getElementById('lobby-name').value = 'Beto'")
    await cdp2.eval(f"document.getElementById('lobby-room').value = '{room}'")
    await cdp2.eval("document.getElementById('btn-join').click()")
    await cdp2.wait_js("!document.getElementById('game').classList.contains('hidden')")

    # --- host starts
    await cdp.eval("document.getElementById('btn-start').click()")
    await cdp.wait_js("document.getElementById('turn-info').textContent.includes('Eligiendo')")

    # --- profession selection: the guest picks first, the host tries the SAME one → error toast
    await cdp2.wait_js("!!document.querySelector('.prof-item:not(.taken)')")
    await cdp2.eval("document.querySelector('.prof-item:not(.taken)').click()")
    await cdp.wait_js("state.players.filter(p => p.profession).length === 1")
    taken_id = await cdp2.eval("state.players.find(p => p.profession).profession.id")
    await cdp.eval(f"chooseProf({json.dumps(taken_id)})")
    await cdp.wait_js("!document.getElementById('game-error').classList.contains('hidden')")
    toast = await cdp.eval("document.getElementById('game-error').textContent")
    assert toast and "ocupada" in toast.lower(), f"toast inesperado: {toast!r}"
    # el host elige otra disponible
    await cdp.eval("document.querySelector('.prof-item:not(.taken)').click()")

    # --- playing
    await cdp.wait_js("document.getElementById('turn-info').textContent.startsWith('Turno de')")

    # --- board fully rendered: 24 + 12 cells and 2 tokens
    assert await cdp.eval("document.querySelectorAll('#board .cell').length") == 36
    assert await cdp.eval("document.querySelectorAll('#board .token').length") == 2
    assert await cdp.eval("!!document.querySelector('.player-card')")
    cash = await cdp.eval("document.querySelector('.player-card .statement .value').textContent")
    assert "$" in cash

    # --- play ~25 actions by clicking the real buttons in both tabs
    clicker = """(() => {
      const pill = document.getElementById('turn-pill');
      if (pill && !pill.classList.contains('hidden')) {
        const pb = pill.querySelector('button');
        if (pb && /dados/i.test(pb.textContent)) { pb.click(); return 'roll'; }
      }
      const m = document.getElementById('modal');
      if (!m || m.classList.contains('hidden')) return 'none';
      const btns = [...m.querySelectorAll('button')];
      const pass = btns.find(b => /Pasar|No |Ignorar|resististe/i.test(b.textContent));
      const buy = btns.find(b => /Comprar/i.test(b.textContent));
      const dona = btns.find(b => /Donar/i.test(b.textContent));
      if (dona) { dona.click(); return 'donar'; }
      if (pass) { pass.click(); return 'pass'; }
      if (buy) { buy.click(); return 'buy'; }
      return 'other';
    })()"""
    acted = 0
    for _ in range(120):
        r1 = await cdp.eval(clicker)
        r2 = await cdp2.eval(clicker)
        if r1 not in ("none", "other") or r2 not in ("none", "other"):
            acted += 1
        if acted >= 25:
            break
        await asyncio.sleep(0.15)
    assert acted >= 10, f"solo {acted} acciones del DOM se ejecutaron"

    # --- log got entries, chat works
    await cdp.eval("document.getElementById('chat-text').value = 'hola beto'")
    await cdp.eval("document.getElementById('chat-send').click()")
    await cdp.wait_js("document.querySelectorAll('#chat-list .msg').length > 0")
    await cdp.wait_js("document.querySelectorAll('#log-list .entry').length > 2")

    # --- no JS errors on the host tab
    await asyncio.sleep(0.5)
    assert cdp.errors == [], f"errores JS en pestaña host: {cdp.errors}"
    assert cdp2.errors == [], f"errores JS en pestaña invitado: {cdp2.errors}"

    await cdp.ws.close()
    await cdp2.ws.close()
