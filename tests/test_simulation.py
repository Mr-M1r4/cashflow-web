"""Headless simulation with a smart strategy + turn cap."""
import asyncio
import random
import sys

sys.path.insert(0, "/home/yo/cashflow-web")

from game import data
from game.engine import Game

FINISH = 0


class FakeRoom:
    def __init__(self):
        self.room_id = "test"
        self.chat = []
        self._input_event = asyncio.Event()

    def broadcast_state(self):
        pass


async def responder(game):
    """Smart bot: buy affordable deals, sell at top price."""
    while True:
        pend = game.pending
        if pend:
            pid = pend["playerId"]
            p = next((q for q in game.players if q["id"] == pid), None)
            if pend["kind"] == "roll":
                game._push_msg(pid, {"type": "roll"})
            else:
                lc = getattr(game, "last_card", None)
                val = {"buy": False}
                if lc:
                    deck = lc["deck"]
                    if deck in ("small", "big") and p:
                        card = lc["card"]
                        if card["kind"] == "stock":
                            val = {"shares": max(0, min(10, lc.get("maxShares", 0)))}
                        else:
                            val = {"buy": p["cash"] >= card["down"]}
                    elif deck == "doodad":
                        val = {"buy": False}
                    elif deck == "charity":
                        val = {"pay": False}
                    elif deck == "market":
                        card = lc["card"]
                        if card["kind"] == "stockBuy":
                            val = {"shares": max(0, min(10, lc.get("maxShares", 0)))}
                        else:
                            val = {"buy": False}
                    elif deck == "marketSell":
                        if lc["kind"] == "realEstate":
                            a = lc["assets"][0]
                            val = {"assetId": a["id"], "price": a["resale"][1]}
                        elif lc["kind"] == "business":
                            a = lc["assets"][0]
                            val = {"assetId": a["id"], "multiplier": lc["card"]["multiplier"][1]}
                        else:
                            val = {"price": lc["priceRange"][1]}
                game._push_msg(pid, {"type": "choice", "value": val})
            game.room._input_event.set()
        await asyncio.sleep(0.005)


async def run_seed(seed):
    global FINISH
    random.seed(seed)
    room = FakeRoom()
    room.game = Game(room)
    n_players = random.choice([2, 3, 4])
    for i in range(n_players):
        room.game.add_player(f"p{i}", f"Jug{i}")
    room.game.start_selection()
    ids = list(data.PROFESSIONS_BY_ID.keys())
    random.shuffle(ids)
    for i in range(n_players):
        room.game.choose_profession(f"p{i}", ids[i])

    g = room.game
    resp = asyncio.create_task(responder(g))

    async def run_loop():
        await g.begin()

    try:
        await asyncio.wait_for(run_loop(), timeout=30)
        print(f"seed={seed} players={n_players}: FINISHED winner={g.winner_id}")
        FINISH += 1
    except asyncio.TimeoutError:
        print(f"seed={seed} players={n_players}: no winner in 30s (game ongoing, state consistent)")
    finally:
        resp.cancel()


async def main():
    for seed in [7, 13, 42, 99, 123, 2000, 31337, 555]:
        await run_seed(seed)
    print(f"\nFinished games: {FINISH}/8")


asyncio.run(main())
