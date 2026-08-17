"""Property-based randomized games: run many full games and verify invariants."""

import asyncio
import json
import random
import sys

import pytest

sys.path.insert(0, "/home/yo/cashflow-web")

from game import data
from game.engine import Game


class FakeRoom:
    def __init__(self):
        self.room_id = "t"
        self.chat = []
        self._input_event = asyncio.Event()

    def broadcast_state(self):
        check_invariants(self.game)


def check_invariants(g):
    for p in g.players:
        assert 0 <= p["position"] < 24
        assert 0 <= p["fastTrackPosition"] < 12
        assert g.passive_income(p) == sum(a["cashFlow"] for a in p["realEstate"]) + sum(b["cashFlow"] for b in p["businesses"])
        assert g.total_expenses(p) == sum(p["expenses"].values()) + p["extraExpenses"]
        ids = [a["id"] for a in p["realEstate"]] + [b["id"] for b in p["businesses"]] + [s["id"] for s in p["stocks"]]
        assert len(ids) == len(set(ids)), f"duplicate asset ids for {p['name']}"
        for s in p["stocks"]:
            assert s["shares"] > 0
        assert p["downsizedTurns"] >= 0
        assert p["children"] >= 0
    profs = [p["profession"]["id"] for p in g.players if p["profession"]]
    assert len(profs) == len(set(profs)), "duplicate professions"
    if g.phase == "over":
        assert g.winner_id is not None
        winner = next(p for p in g.players if p["id"] == g.winner_id)
        assert winner["won"]
    json.dumps(g.state(), ensure_ascii=False)


async def responder(g, rng):
    """Random bot with a bias toward smart moves; checks invariants after each reply."""
    while True:
        pend = g.pending
        if pend:
            pid = pend["playerId"]
            p = next((q for q in g.players if q["id"] == pid), None)
            if pend["kind"] == "roll":
                g._push_msg(pid, {"type": "roll"})
            elif pend["kind"] == "continue":
                g._push_msg(pid, {"type": "continue"})
            else:
                lc = getattr(g, "last_card", None)
                val = {"buy": False}
                if lc and p:
                    deck = lc["deck"]
                    if deck in ("small", "big"):
                        card = lc["card"]
                        if card["kind"] == "stock":
                            val = {"shares": rng.randint(0, min(10, lc.get("maxShares", 0)))} if lc.get("maxShares", 0) > 0 else {"shares": 0}
                        else:
                            val = {"buy": rng.random() < 0.6 and p["cash"] >= card["down"]}
                    elif deck == "doodad":
                        val = {"buy": rng.random() < 0.15}
                    elif deck == "charity":
                        val = {"pay": rng.random() < 0.3}
                    elif deck == "market":
                        card = lc["card"]
                        if card["kind"] == "stockBuy":
                            val = {"shares": rng.randint(0, min(10, lc.get("maxShares", 0)))} if lc.get("maxShares", 0) > 0 else {"shares": 0}
                        else:
                            val = {"buy": False}
                    elif deck == "marketSell":
                        if lc["kind"] == "realEstate":
                            a = lc["assets"][rng.randrange(len(lc["assets"]))]
                            val = {"assetId": a["id"], "price": rng.randint(a["resale"][0], a["resale"][1])}
                        elif lc["kind"] == "business":
                            a = lc["assets"][rng.randrange(len(lc["assets"]))]
                            val = {"assetId": a["id"], "multiplier": rng.uniform(lc["card"]["multiplier"][0], lc["card"]["multiplier"][1])}
                        else:
                            val = {"price": rng.randint(lc["priceRange"][0], lc["priceRange"][1])}
                g._push_msg(pid, {"type": "choice", "value": val})
            g.room._input_event.set()
            check_invariants(g)
        await asyncio.sleep(0.001)


async def run_seed(seed, n_players, finish_if_fast=True):
    rng = random.Random(seed)
    room = FakeRoom()
    g = Game(room)
    room.game = g
    for i in range(n_players):
        g.add_player(f"p{i}", f"J{i}")
    g.start_selection()
    ids = list(data.PROFESSIONS_BY_ID.keys())
    rng.shuffle(ids)
    for i in range(n_players):
        assert g.choose_profession(f"p{i}", ids[i])
    resp = asyncio.create_task(responder(g, rng))
    try:
        await asyncio.wait_for(g.begin(), timeout=12)
    except asyncio.TimeoutError:
        # game still ongoing but invariants hold; that's OK unless nothing ever escapes
        assert g.phase == "playing"
    finally:
        resp.cancel()
    check_invariants(g)
    if g.phase == "over":
        assert g.winner_id is not None
    return g


@pytest.mark.parametrize("seed,np", [
    (1, 2), (2, 2), (3, 3), (4, 3), (5, 4), (6, 4),
    (7, 5), (8, 6),
])
def test_random_games_invariants(seed, np):
    asyncio.run(run_seed(seed, np))


def test_many_finish():
    finished = 0
    for seed in range(11, 26):
        g = asyncio.run(run_seed(seed, 2))
        if g.phase == "over":
            finished += 1
    # most 2-player games with smart bots should finish within the budget
    assert finished >= 10, f"only {finished}/15 finished"
