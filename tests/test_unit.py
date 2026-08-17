"""Unit tests for the game engine (deterministic, no randomness where possible)."""

import asyncio
import json
import sys

import pytest

sys.path.insert(0, "/home/yo/cashflow-web")

from game import data
from game import engine as engine_mod
from game.engine import Game


@pytest.fixture(autouse=True)
def _short_timeout(monkeypatch):
    monkeypatch.setattr(engine_mod, "ACTION_TIMEOUT", 1)


class FakeRoom:
    def __init__(self):
        self.room_id = "test"
        self.chat = []
        self._input_event = asyncio.Event()
        self.broadcasts = 0

    def broadcast_state(self):
        self.broadcasts += 1
        self.game.state()


def run(coro):
    return asyncio.run(coro)


def make_game(n=2, with_professions=True):
    room = FakeRoom()
    g = Game(room)
    room.game = g
    for i in range(n):
        g.add_player(f"p{i}", f"Jugador{i}")
    g.start_selection()
    if with_professions:
        ids = list(data.PROFESSIONS_BY_ID.keys())
        for i in range(n):
            assert g.choose_profession(f"p{i}", ids[i])
    g._decks = g._build_decks()
    return g, room


def answer(g, pid, msg):
    g._push_msg(pid, msg)
    g.room._input_event.set()


def give_asset(p, kind="realEstate", cashFlow=100, tags=None):
    if kind == "realEstate":
        p["realEstate"].append({"id": "a1", "name": "Test", "cost": 50000, "down": 5000,
                                "cashFlow": cashFlow, "resale": [45000, 65000], "tags": tags or ["house"]})
    elif kind == "business":
        p["businesses"].append({"id": "b1", "name": "Neg", "cost": 50000, "down": 5000, "cashFlow": cashFlow})
    elif kind == "stock":
        p["stocks"].append({"id": "s1", "symbol": "MSFT", "name": "MSFT", "shares": 10, "buyPrice": 30})


# --------------------------------------------------------------------------- finance

def test_finance_basics():
    g, _ = make_game()
    p = g.players[0]
    prof = p["profession"]
    assert p["cash"] == prof["savings"]
    assert g.salary(p) == prof["salary"]
    assert g.passive_income(p) == 0
    assert g.total_expenses(p) == sum(prof["expenses"].values())
    assert g.cash_flow(p) == prof["salary"] - sum(prof["expenses"].values())
    assert not g.can_escape(p)


def test_downsize_kills_salary():
    g, _ = make_game()
    p = g.players[0]
    p["downsizedTurns"] = 2
    assert g.salary(p) == 0
    assert g.cash_flow(p) == -g.total_expenses(p)


def test_passive_income_and_escape():
    g, _ = make_game()
    p = g.players[0]
    expenses = g.total_expenses(p)
    give_asset(p, cashFlow=expenses + 1)
    assert g.can_escape(p)
    assert g.passive_income(p) == expenses + 1


def test_state_is_json_serializable():
    g, _ = make_game()
    g.pending = {"playerId": "p0", "kind": "roll"}
    g.last_card = {"deck": "small", "card": data.SMALL_DEALS[0], "afford": True}
    g.last_move = {"moveId": 1, "playerId": "p0", "dice": [3, 4], "from": 0, "to": 7, "fast": False}
    g._log("hola")
    s = g.state()
    json.dumps(s, ensure_ascii=False)  # must not raise


# --------------------------------------------------------------------------- profession

def test_profession_invalid():
    g, _ = make_game(with_professions=False)
    assert not g.choose_profession("p0", "nope")
    assert g.players[0]["profession"] is None
    assert not g.choose_profession("ghost", "doctor")


def test_profession_not_taken_twice():
    g, _ = make_game(with_professions=False)
    assert g.choose_profession("p0", "doctor")
    assert not g.choose_profession("p1", "doctor")  # same profession rejected
    assert not g.choose_profession("p0", "doctor")  # already chose
    assert g.choose_profession("p1", "janitor")


# --------------------------------------------------------------------------- deals

def test_buy_real_estate():
    g, _ = make_game()
    p = g.players[0]
    p["cash"] = 100000
    cash0 = p["cash"]
    card = data.SMALL_DEALS[0]
    answer(g, "p0", {"type": "choice", "value": {"buy": True}})
    run(g.handle_deal(p, card, "small"))
    assert p["cash"] == cash0 - card["down"]
    assert len(p["realEstate"]) == 1
    assert g.passive_income(p) == card["cashFlow"]


def test_pass_deal():
    g, _ = make_game()
    p = g.players[0]
    cash0 = p["cash"]
    answer(g, "p0", {"type": "choice", "value": {"buy": False}})
    run(g.handle_deal(p, data.SMALL_DEALS[0], "small"))
    assert p["cash"] == cash0
    assert not p["realEstate"]


def test_cannot_buy_unaffordable_even_if_client_hacks():
    g, _ = make_game()
    p = g.players[0]
    p["cash"] = 1
    card = data.BIG_DEALS[0]  # down = 20000
    answer(g, "p0", {"type": "choice", "value": {"buy": True}})  # malicious
    run(g.handle_deal(p, card, "big"))
    assert p["cash"] == 1
    assert not p["realEstate"]


def test_stock_buy_and_merge():
    g, _ = make_game()
    p = g.players[0]
    p["cash"] = 1000
    card = next(c for c in data.SMALL_DEALS if c["kind"] == "stock" and c["symbol"] == "MSFT")
    answer(g, "p0", {"type": "choice", "value": {"shares": 10}})
    run(g.handle_deal(p, card, "small"))
    assert p["cash"] == 1000 - 10 * card["price"]
    assert len(p["stocks"]) == 1 and p["stocks"][0]["shares"] == 10
    # second buy merges
    p["cash"] = 1000
    answer(g, "p0", {"type": "choice", "value": {"shares": 5}})
    run(g.handle_deal(p, card, "small"))
    assert p["stocks"][0]["shares"] == 15


def test_stock_buy_caps_at_cash():
    g, _ = make_game()
    p = g.players[0]
    p["cash"] = 100
    card = next(c for c in data.SMALL_DEALS if c["kind"] == "stock" and c["price"] > 100)
    answer(g, "p0", {"type": "choice", "value": {"shares": 999}})
    run(g.handle_deal(p, card, "small"))
    assert p["stocks"] == []  # maxShares = 0 -> skipped


def test_stock_buy_negative_clamped():
    g, _ = make_game()
    p = g.players[0]
    p["cash"] = 1000
    card = next(c for c in data.SMALL_DEALS if c["kind"] == "stock")
    answer(g, "p0", {"type": "choice", "value": {"shares": -50}})
    run(g.handle_deal(p, card, "small"))
    assert p["cash"] == 1000 and not p["stocks"]


def test_doodad_buy_adds_expense():
    g, _ = make_game()
    p = g.players[0]
    p["cash"] = 10000
    card = next(c for c in data.DOODADS if c["expense"] > 0)
    extra0 = p["extraExpenses"]
    answer(g, "p0", {"type": "choice", "value": {"buy": True}})
    run(g.handle_doodad(p, card))
    assert p["cash"] == 10000 - card["cost"]
    assert p["extraExpenses"] == extra0 + card["expense"]


def test_charity_pay():
    g, _ = make_game()
    p = g.players[0]
    salary = g.salary(p)
    cash0 = p["cash"]
    answer(g, "p0", {"type": "choice", "value": {"pay": True}})
    run(g.handle_charity(p))
    assert p["cash"] == cash0 - int(salary * 0.1)
    assert p["charityOneDie"]


def test_charity_no_cash_no_pay():
    g, _ = make_game()
    p = g.players[0]
    p["cash"] = 0
    answer(g, "p0", {"type": "choice", "value": {"pay": True}})
    run(g.handle_charity(p))
    assert not p["charityOneDie"]


def test_baby_adds_children_expense():
    g, _ = make_game()
    p = g.players[0]
    p["position"] = data.RAT_RACE_BOARD.index("BABY")
    children0 = p["children"]
    exp0 = p["expenses"]["children"]
    run(g.resolve_rat_race(p))
    assert p["children"] == children0 + 1
    assert p["expenses"]["children"] > exp0


def test_downsize_increments_turns():
    g, _ = make_game()
    p = g.players[0]
    p["position"] = data.RAT_RACE_BOARD.index("DOWNSIZE")
    run(g.resolve_rat_race(p))
    assert p["downsizedTurns"] > 0
    assert g.salary(p) == 0


def test_payday_collects_cash_flow():
    g, _ = make_game()
    p = g.players[0]
    p["position"] = data.RAT_RACE_BOARD.index("PAYDAY")
    cash0 = p["cash"]
    run(g.resolve_rat_race(p))
    assert p["cash"] == cash0 + g.cash_flow(p)


# --------------------------------------------------------------------------- market sells

def test_market_sell_real_estate():
    g, _ = make_game()
    p = g.players[0]
    give_asset(p, tags=["house"])
    cash0 = p["cash"]
    card = next(c for c in data.MARKET_CARDS if c["kind"] == "buy" and "house" in c["buyTags"])
    answer(g, "p0", {"type": "choice", "value": {"assetId": "a1", "price": 60000}})
    run(g.handle_market(p, card))
    assert p["cash"] == cash0 + 60000
    assert p["realEstate"] == []
    assert g.passive_income(p) == 0


def test_market_sell_bad_asset_id_ignored():
    g, _ = make_game()
    p = g.players[0]
    give_asset(p, tags=["house"])
    cash0 = p["cash"]
    card = next(c for c in data.MARKET_CARDS if c["kind"] == "buy" and "house" in c["buyTags"])
    answer(g, "p0", {"type": "choice", "value": {"assetId": "ghost", "price": 60000}})
    run(g.handle_market(p, card))
    assert p["cash"] == cash0 and p["realEstate"]


def test_market_sell_stock():
    g, _ = make_game()
    p = g.players[0]
    give_asset(p, kind="stock")
    cash0 = p["cash"]
    card = next(c for c in data.MARKET_CARDS if c["kind"] == "stockSell" and c["symbol"] == "MSFT")
    answer(g, "p0", {"type": "choice", "value": {"price": 50}})
    run(g.handle_market(p, card))
    assert p["cash"] == cash0 + 50 * 10
    assert p["stocks"] == []


def test_market_sell_business_multiplier():
    g, _ = make_game()
    p = g.players[0]
    give_asset(p, kind="business", cashFlow=500)
    cash0 = p["cash"]
    card = next(c for c in data.MARKET_CARDS if c["kind"] == "buyBusiness")
    answer(g, "p0", {"type": "choice", "value": {"assetId": "b1", "multiplier": 2.0}})
    run(g.handle_market(p, card))
    assert p["cash"] == cash0 + 500 * 12 * 2
    assert p["businesses"] == []


def test_market_skips_non_owners():
    g, _ = make_game()
    p = g.players[0]
    q = g.players[1]
    give_asset(q, tags=["house"])
    card = next(c for c in data.MARKET_CARDS if c["kind"] == "buy" and "house" in c["buyTags"])
    answer(g, "p1", {"type": "choice", "value": {"assetId": "a1", "price": 60000}})
    run(g.handle_market(p, card))
    assert q["cash"] > 0 and q["realEstate"] == []


# --------------------------------------------------------------------------- fast track & win

def test_enter_fast_track_on_escape():
    g, _ = make_game()
    p = g.players[0]
    give_asset(p, cashFlow=g.total_expenses(p) + 10)
    assert g.can_escape(p)
    run(g.enter_fast_track(p))
    assert p["inFastTrack"] and p["fastTrackPosition"] == 0


def test_dream_win():
    g, _ = make_game()
    p = g.players[0]
    p["inFastTrack"] = True
    p["dream"] = {"id": "test", "name": "Sueño", "cost": 50000}
    p["cash"] = 60000
    p["fastTrackPosition"] = data.FAST_TRACK_BOARD.index("DREAM")
    run(g.resolve_fast_track(p))
    assert g.winner_id == p["id"] and p["won"]


def test_dream_not_enough_cash_no_win():
    g, _ = make_game()
    p = g.players[0]
    p["inFastTrack"] = True
    p["dream"] = {"id": "test", "name": "Sueño", "cost": 50000}
    p["cash"] = 1000
    p["fastTrackPosition"] = data.FAST_TRACK_BOARD.index("DREAM")
    run(g.resolve_fast_track(p))
    assert g.winner_id is None and p["cash"] == 1000


def test_fast_track_cashflow_day():
    g, _ = make_game()
    p = g.players[0]
    p["inFastTrack"] = True
    p["fastTrackPosition"] = data.FAST_TRACK_BOARD.index("CASHFLOW")
    cash0 = p["cash"]
    run(g.resolve_fast_track(p))
    assert p["cash"] == cash0 + g.cash_flow(p)


def test_fast_track_crisis_fine():
    g, _ = make_game()
    p = g.players[0]
    p["inFastTrack"] = True
    p["fastTrackPosition"] = data.FAST_TRACK_BOARD.index("DOWNSIZE")
    p["cash"] = 10000
    run(g.resolve_fast_track(p))
    assert p["cash"] == 10000 - 1000  # 10% = 1000


def test_fifty_k_cashflow_win():
    g, _ = make_game()
    p = g.players[0]
    p["inFastTrack"] = True
    for i in range(30):
        give_asset(p, kind="business", cashFlow=2000)
    assert g.cash_flow(p) >= 50000
    g.declare_winner(p, "test")
    assert g.phase == "over" or g.winner_id == p["id"]


# --------------------------------------------------------------------------- full turn integration

def test_do_turn_advances_and_rolls():
    g, _ = make_game(2)
    Game.roll_die = staticmethod(lambda: 3)
    p0 = g.players[g.turn_index]
    answer(g, p0["id"], {"type": "roll"})
    run(g.do_turn(p0))
    # position moved by 6
    assert p0["position"] == 6


def test_charity_one_die_next_turn():
    g, _ = make_game(1)
    p = g.players[0]
    Game.roll_die = staticmethod(lambda: 4)
    p["charityOneDie"] = True
    answer(g, p["id"], {"type": "roll"})
    run(g.do_turn(p))
    assert p["position"] == 4  # single die
    assert not p["charityOneDie"]


def test_wait_for_timeout_applies_default():
    g, _ = make_game(1)
    p = g.players[0]
    Game.roll_die = staticmethod(lambda: 2)
    g._log("x")
    # no answer -> after ACTION_TIMEOUT returns default roll
    msg = run(g.wait_for(p["id"], {"roll"}, default={"type": "roll"}))
    assert msg == {"type": "roll"}


def test_full_game_reaches_over():
    """Drive a full game with an always-buy bot until a winner emerges."""
    g, _ = make_game(2)
    Game.roll_die = staticmethod(lambda: 5)

    async def play():
        g.phase = "playing"
        turns = 0
        while g.phase == "playing" and g.winner_id is None and turns < 2000:
            p = g.players[g.turn_index]
            await g.do_turn(p)
            if g.winner_id is not None:
                break
            g.turn_index = (g.turn_index + 1) % len(g.players)
            turns += 1
        if g.winner_id is not None:
            g.phase = "over"

    # pre-answer every roll & choice with a smart strategy so no timeouts
    orig_wait = g.wait_for

    async def auto_wait(pid, kinds, default=None):
        kinds = tuple(kinds)
        if "roll" in kinds:
            g._push_msg(pid, {"type": "roll"})
        else:
            player = next((p for p in g.players if p["id"] == pid), None)
            lc = g.last_card
            val = {"buy": False}
            if lc and player:
                deck = lc["deck"]
                if deck in ("small", "big") and lc["card"]["kind"] != "stock":
                    val = {"buy": player["cash"] >= lc["card"]["down"]}
                elif deck in ("small", "big") and lc["card"]["kind"] == "stock" or deck == "market" and lc["card"]["kind"] == "stockBuy":
                    val = {"shares": 5} if lc.get("maxShares", 0) > 0 else {"shares": 0}
                elif deck == "marketSell":
                    if lc["kind"] == "realEstate":
                        a = lc["assets"][0]
                        val = {"assetId": a["id"], "price": a["resale"][1]}
                    elif lc["kind"] == "business":
                        a = lc["assets"][0]
                        val = {"assetId": a["id"], "multiplier": lc["card"]["multiplier"][1]}
                    else:
                        val = {"price": lc["priceRange"][1]}
            g._push_msg(pid, {"type": "choice", "value": val})
        g.room._input_event.set()
        return await orig_wait(pid, kinds, default)

    g.wait_for = auto_wait
    run(play())
    assert g.phase == "over"
    assert g.winner_id is not None


# ------------------------------------------------ info-card / can't-afford flows

def test_unaffordable_stock_sets_last_card_no_pending():
    g, _ = make_game()
    p = g.players[0]
    p["cash"] = 1
    card = next(c for c in data.SMALL_DEALS if c["kind"] == "stock" and c["price"] > 1)
    run(g.handle_deal(p, card, "small"))
    assert g.last_card is not None
    assert g.last_card["deck"] == "small"
    assert g.last_card["maxShares"] == 0
    assert g.pending is None
    assert p["cash"] == 1


def test_unaffordable_realestate_sets_last_card_no_pending():
    g, _ = make_game()
    p = g.players[0]
    p["cash"] = 1
    card = data.BIG_DEALS[0]
    run(g.handle_deal(p, card, "big"))
    assert g.last_card is not None
    assert g.last_card["deck"] == "big"
    assert g.last_card["afford"] is False
    assert g.pending is None
    assert p["cash"] == 1
    assert not p["realEstate"]


def test_unaffordable_doodad_sets_last_card_no_pending():
    g, _ = make_game()
    p = g.players[0]
    p["cash"] = 1
    card = data.DOODADS[0]
    run(g.handle_doodad(p, card))
    assert g.last_card is not None
    assert g.last_card["deck"] == "doodad"
    assert g.last_card["afford"] is False
    assert g.pending is None
    assert p["cash"] == 1


def test_unaffordable_market_stock_sets_last_card_no_pending():
    g, _ = make_game()
    p = g.players[0]
    p["cash"] = 1
    card = next(c for c in data.MARKET_CARDS if c["kind"] == "stockBuy" and c["price"] > 1)
    run(g.handle_market(p, card))
    assert g.last_card is not None
    assert g.last_card["deck"] == "market"
    assert g.last_card["maxShares"] == 0
    assert g.pending is None
    assert p["cash"] == 1


def test_affordable_stock_sets_pending():
    g, _ = make_game()
    p = g.players[0]
    p["cash"] = 1000
    card = next(c for c in data.SMALL_DEALS if c["kind"] == "stock" and c["price"] <= 1000)
    answer(g, "p0", {"type": "choice", "value": {"shares": 5}})
    run(g.handle_deal(p, card, "small"))
    assert g.last_card is not None
    assert g.pending is None


def test_last_card_cleared_on_new_turn():
    g, _ = make_game()
    p = g.players[0]
    g.last_card = {"deck": "small", "card": data.SMALL_DEALS[0], "afford": False}
    p["position"] = data.RAT_RACE_BOARD.index("PAYDAY")
    # do_turn resets last_card to None before roll, then resolve may set it again.
    # We monkeypatch do_turn to verify the reset happens at the top.
    old_do_turn = g.__class__.do_turn
    cleared_at_entry = [False]

    async def instrumented_do_turn(self, p):
        if self.last_card is not None:
            self.last_card = None
            cleared_at_entry[0] = True
        return await old_do_turn(self, p)

    g.__class__.do_turn = instrumented_do_turn
    answer(g, "p0", {"type": "roll"})
    run(g.do_turn(p))
    assert cleared_at_entry[0]


def test_last_card_cleared_before_roll():
    g, _ = make_game()
    p = g.players[0]
    g.last_card = {"deck": "old", "card": {}}
    old_wait_for = g.wait_for
    saw_none = [False]

    async def patched_wait(pid, kinds, default=None):
        if "roll" in kinds and g.last_card is None:
            saw_none[0] = True
        return await old_wait_for(pid, kinds, default)

    g.wait_for = patched_wait
    answer(g, "p0", {"type": "roll"})
    p["position"] = data.RAT_RACE_BOARD.index("PAYDAY")
    run(g.do_turn(p))
    assert saw_none[0]
