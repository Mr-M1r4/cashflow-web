"""Game engine for the Cashflow board game (rat race + fast track)."""

import asyncio
import random
import uuid

from . import data

ACTION_TIMEOUT = 180  # seconds before an idle player is auto-resolved


def fmt(n):
    return f"${n:,.0f}".replace(",", ".")


class Game:
    def __init__(self, room):
        self.room = room
        self.phase = "lobby"  # lobby -> selecting -> playing -> over
        self.players = []
        self.turn_index = 0
        self.pending = None
        self.logs = []
        self.winner_id = None
        self.last_move = None
        self.last_card = None
        self._move_seq = 0
        self._player_input = {}
        self._decks = {}

    # ------------------------------------------------------------------ helpers

    def _log(self, text):
        self.logs.append(text)
        self.room.broadcast_state()

    def _push_msg(self, player_id, msg):
        self._player_input.setdefault(player_id, []).append(msg)

    async def wait_for(self, player_id, kinds, default=None):
        """Wait until `player_id` sends a message of the given kinds, or timeout."""
        kinds = tuple(kinds)
        self.pending = {"playerId": player_id, "kind": kinds[0] if len(kinds) == 1 else "any"}
        self.room.broadcast_state()
        player = next((p for p in self.players if p["id"] == player_id), None)
        timeout = ACTION_TIMEOUT if (player and player["connected"]) else 60
        loop = asyncio.get_event_loop()
        deadline = loop.time() + timeout
        while True:
            remaining = deadline - loop.time()
            if remaining <= 0:
                self.pending = None
                self._log("⏱ Tiempo agotado, se decide automáticamente.")
                if default is not None:
                    return default
                return {"type": "timeout"}
            q = self._player_input.get(player_id, [])
            if q:
                msg = q.pop(0)
                if msg["type"] in kinds:
                    self.pending = None
                    return msg
                continue  # drop unexpected messages
            self.room._input_event.clear()
            if self._player_input.get(player_id):
                continue
            try:
                await asyncio.wait_for(self.room._input_event.wait(), timeout=min(remaining, 30))
            except asyncio.TimeoutError:
                continue

    @staticmethod
    def roll_die():
        return random.randint(1, 6)

    # ------------------------------------------------------------------ finance

    @staticmethod
    def salary(p):
        prof = p["profession"]
        return prof["salary"] if p["downsizedTurns"] <= 0 else 0

    @staticmethod
    def passive_income(p):
        return sum(a["cashFlow"] for a in p["realEstate"]) + sum(b["cashFlow"] for b in p["businesses"])

    @staticmethod
    def total_expenses(p):
        return sum(p["expenses"].values()) + p["extraExpenses"]

    @staticmethod
    def cash_flow(p):
        return Game.salary(p) + Game.passive_income(p) - Game.total_expenses(p)

    @staticmethod
    def can_escape(p):
        return Game.passive_income(p) > Game.total_expenses(p)

    # ------------------------------------------------------------------ setup

    def add_player(self, pid, name, icon="", color="", photo=""):
        p = {
            "id": pid,
            "name": name,
            "icon": icon,
            "color": color,
            "photo": photo,
            "profession": None,
            "cash": 0,
            "stocks": [],
            "realEstate": [],
            "businesses": [],
            "expenses": {},
            "liabilities": {},
            "extraExpenses": 0,
            "children": 0,
            "downsizedTurns": 0,
            "charityOneDie": False,
            "position": 0,
            "fastTrackPosition": 0,
            "inFastTrack": False,
            "dream": None,
            "won": False,
            "connected": True,
        }
        self.players.append(p)

    def start_selection(self):
        self.phase = "selecting"
        dreams = random.sample(data.DREAMS, len(data.DREAMS))
        for i, p in enumerate(self.players):
            p["dream"] = dreams[i % len(dreams)]
        self._log("Se reparten las profesiones. ¡Elegí la tuya!")
        self.room.broadcast_state()

    def choose_profession(self, pid, prof_id):
        if self.phase != "selecting":
            return False
        if prof_id not in data.PROFESSIONS_BY_ID:
            return False
        if any(p["profession"] and p["profession"]["id"] == prof_id for p in self.players):
            return False
        p = next((p for p in self.players if p["id"] == pid), None)
        if p is None or p["profession"] is not None:
            return False
        prof = data.PROFESSIONS_BY_ID[prof_id]
        p["profession"] = prof
        p["cash"] = prof["savings"]
        p["expenses"] = dict(prof["expenses"])
        p["liabilities"] = dict(prof["liabilities"])
        self._log(f"{p['name']} eligió {prof['name']}.")
        return True

    def all_chose(self):
        return all(p["profession"] is not None for p in self.players)

    async def begin(self):
        self.phase = "playing"
        random.shuffle(self.players)
        self._decks = self._build_decks()
        self._log("Comienza el juego. ¡Carrera de ratas!")
        self.room.broadcast_state()
        await self.run()

    def _build_decks(self):
        decks = {}
        for key, pool in (
            ("small", data.SMALL_DEALS),
            ("big", data.BIG_DEALS),
            ("market", data.MARKET_CARDS),
            ("doodad", data.DOODADS),
            ("baby", data.BABY_CARDS),
            ("downsize", data.DOWNSIZE_CARDS),
        ):
            deck = list(pool)
            random.shuffle(deck)
            decks[key] = deck
        return decks

    def _draw(self, deck_key):
        deck = self._decks[deck_key]
        card = deck.pop(0)
        deck.append(card)  # reinsert at bottom so it never runs out
        return card

    # ------------------------------------------------------------------ run loop

    async def run(self):
        while self.phase == "playing" and self.winner_id is None:
            p = self.players[self.turn_index]
            self._log(f"▶ Turno de {p['name']}.")
            await self.do_turn(p)
            if self.winner_id is not None:
                break
            if self.phase == "playing":
                self.turn_index = (self.turn_index + 1) % len(self.players)
        if self.winner_id is not None:
            self.phase = "over"
            self._log("🏆 ¡Fin del juego!")
        self.room.broadcast_state()

    async def do_turn(self, p):
        if p["downsizedTurns"] > 0:
            p["downsizedTurns"] -= 1
            self._log(f"💼 {p['name']} sigue despedido ({p['downsizedTurns']} turnos sin salario).")

        await self.wait_for(p["id"], {"roll"}, default={"type": "roll"})
        d1 = self.roll_die()
        d2 = self.roll_die()
        if p["charityOneDie"]:
            p["charityOneDie"] = False
            steps = d1
            self._log(f"🎲 {p['name']} (caridad, 1 dado) sacó {d1}.")
        elif p["inFastTrack"]:
            steps = d1
            self._log(f"🎲 {p['name']} (pista rápida, 1 dado) sacó {d1}.")
        else:
            steps = d1 + d2
            self._log(f"🎲 {p['name']} sacó {d1} y {d2} = {steps}.")

        if p["inFastTrack"]:
            old = p["fastTrackPosition"]
            p["fastTrackPosition"] = (old + steps) % 12
            self._move_seq += 1
            self.last_move = {"moveId": self._move_seq, "playerId": p["id"], "dice": [d1, d2], "from": old, "to": p["fastTrackPosition"], "fast": True}
            self._log(f"🚀 {p['name']} se mueve a la casilla {p['fastTrackPosition']}.")
            await self.resolve_fast_track(p)
        else:
            old = p["position"]
            p["position"] = (old + steps) % 24
            self._move_seq += 1
            self.last_move = {"moveId": self._move_seq, "playerId": p["id"], "dice": [d1, d2], "from": old, "to": p["position"], "fast": False}
            self._log(f"🏃 {p['name']} avanza a la casilla {p['position']}.")
            await self.resolve_rat_race(p)
            if self.phase == "playing" and not p["inFastTrack"] and self.can_escape(p) and self.total_expenses(p) > 0:
                await self.enter_fast_track(p)
                if p["inFastTrack"] and self.cash_flow(p) >= 50000:
                    self.declare_winner(p, "alcanzaste $50.000 de flujo de caja")
                    return

        if self.cash_flow(p) >= 50000 and p["inFastTrack"] and self.winner_id is None:
            self.declare_winner(p, "alcanzaste $50.000 de flujo de caja")

    # ------------------------------------------------------------------ rat race

    async def resolve_rat_race(self, p):
        sq = data.RAT_RACE_BOARD[p["position"]]
        if sq == "PAYDAY":
            cf = self.cash_flow(p)
            p["cash"] += cf
            self._log(f"💰 {p['name']} cobra su día de pago: +{fmt(cf)}.")
        elif sq == "SMALL":
            card = self._draw("small")
            await self.handle_deal(p, card, "small")
        elif sq == "BIG":
            card = self._draw("big")
            await self.handle_deal(p, card, "big")
        elif sq == "MARKET":
            card = self._draw("market")
            self._log(f"📈 Mercado: {card['title']} — {card['text']}")
            await self.handle_market(p, card)
        elif sq == "DOODAD":
            card = self._draw("doodad")
            await self.handle_doodad(p, card)
        elif sq == "CHARITY":
            await self.handle_charity(p)
        elif sq == "BABY":
            card = self._draw("baby")
            p["children"] += 1
            p["expenses"]["children"] = p["expenses"].get("children", 0) + card["expense"]
            self._log(f"👶 {p['name']} cae en BEBÉ: {card['name']} ({card['text']})")
        elif sq == "DOWNSIZE":
            card = self._draw("downsize")
            p["downsizedTurns"] += card["turns"]
            self._log(f"💼 {p['name']} cae en DESPIDO: {card['text']}")

    # ------------------------------------------------------------------ fast track

    async def resolve_fast_track(self, p):
        sq = data.FAST_TRACK_BOARD[p["fastTrackPosition"]]
        if sq == "CASHFLOW":
            cf = self.cash_flow(p)
            p["cash"] += cf
            self._log(f"💰 {p['name']} cobra su día de flujo de efectivo: +{fmt(cf)}.")
        elif sq == "OPPORTUNITY":
            card = self._draw("big")
            await self.handle_deal(p, card, "big")
        elif sq == "DREAM":
            if p["cash"] >= p["dream"]["cost"]:
                p["cash"] -= p["dream"]["cost"]
                self.declare_winner(p, f"compraste tu sueño: {p['dream']['name']}")
            else:
                self._log(f"😢 {p['name']} llega a su sueño ({p['dream']['name']}, {fmt(p['dream']['cost'])}) pero no le alcanza el efectivo ({fmt(p['cash'])}).")
        elif sq == "MARKET":
            card = self._draw("market")
            self._log(f"📈 Mercado: {card['title']} — {card['text']}")
            await self.handle_market(p, card)
        elif sq == "DOODAD":
            card = self._draw("doodad")
            await self.handle_doodad(p, card)
        elif sq == "DOWNSIZE":
            fine = max(1000, int(p["cash"] * 0.1))
            p["cash"] -= fine
            self._log(f"📉 Crisis en el mercado: {p['name']} paga una multa de {fmt(fine)}.")

    # ------------------------------------------------------------------ actions

    async def handle_deal(self, p, card, deck_key):
        self.last_card = {"deck": deck_key, "card": card}
        if card["kind"] == "stock":
            max_shares = int(p["cash"] // card["price"])
            self.last_card["maxShares"] = max_shares
            self.room.broadcast_state()
            if max_shares <= 0:
                self._log(f"📊 {p['name']} no tiene efectivo para comprar {card['name']}.")
                return
            msg = await self.wait_for(p["id"], {"choice"}, default={"type": "choice", "value": {"shares": 0}})
            val = msg["value"]
            shares = int(val.get("shares", 0) or 0)
            if shares > 0:
                shares = min(shares, max_shares)
                cost = shares * card["price"]
                p["cash"] -= cost
                lot = next((s for s in p["stocks"] if s["symbol"] == card["symbol"]), None)
                if lot:
                    total = lot["shares"] + shares
                    lot["buyPrice"] = (lot["buyPrice"] * lot["shares"] + cost) / total
                    lot["shares"] = total
                else:
                    p["stocks"].append({
                        "id": uuid.uuid4().hex[:8], "symbol": card["symbol"],
                        "name": card["name"], "shares": shares, "buyPrice": card["price"],
                    })
                self._log(f"📊 {p['name']} compró {shares} acciones de {card['symbol']} por {fmt(cost)}.")
            else:
                self._log(f"{p['name']} pasa la oportunidad de {card['name']}.")
        else:
            afford = p["cash"] >= card["down"]
            self.last_card["afford"] = afford
            self.room.broadcast_state()
            if not afford:
                self._log(f"{p['name']} no puede pagar el anticipo de {fmt(card['down'])} para {card['name']}.")
                return
            msg = await self.wait_for(p["id"], {"choice"}, default={"type": "choice", "value": {"buy": False}})
            val = msg["value"]
            if val.get("buy") and p["cash"] >= card["down"]:
                p["cash"] -= card["down"]
                if card["kind"] == "realEstate":
                    p["realEstate"].append({
                        "id": uuid.uuid4().hex[:8], "name": card["name"],
                        "cost": card["cost"], "down": card["down"],
                        "cashFlow": card["cashFlow"], "resale": card["resale"], "tags": card["tags"],
                    })
                else:
                    p["businesses"].append({
                        "id": uuid.uuid4().hex[:8], "name": card["name"],
                        "cost": card["cost"], "down": card["down"], "cashFlow": card["cashFlow"],
                    })
                self._log(f"✅ {p['name']} compró {card['name']} por {fmt(card['down'])} de anticipo. Flujo pasivo +{fmt(card['cashFlow'])}/mes.")
            else:
                self._log(f"{p['name']} pasa la oportunidad de {card['name']}.")

    async def handle_doodad(self, p, card):
        afford = p["cash"] >= card["cost"]
        self.last_card = {"deck": "doodad", "card": card, "afford": afford}
        self.room.broadcast_state()
        if not afford:
            self._log(f"{p['name']} no puede pagar {card['name']} ({fmt(card['cost'])}).")
            return
        msg = await self.wait_for(p["id"], {"choice"}, default={"type": "choice", "value": {"buy": False}})
        if msg["value"].get("buy") and p["cash"] >= card["cost"]:
            p["cash"] -= card["cost"]
            if card["expense"]:
                p["extraExpenses"] += card["expense"]
            self._log(f"🛍 {p['name']} compró {card['name']} por {fmt(card['cost'])}.")
        else:
            self._log(f"{p['name']} resistió la tentación de {card['name']}.")

    async def handle_charity(self, p):
        salary = self.salary(p)
        if salary <= 0:
            self._log(f"🤝 {p['name']} pasa por caridad sin salario.")
            return
        cost = int(salary * 0.1)
        self.last_card = {"deck": "charity", "amount": cost}
        self.room.broadcast_state()
        msg = await self.wait_for(p["id"], {"choice"}, default={"type": "choice", "value": {"pay": False}})
        if msg["value"].get("pay") and p["cash"] >= cost:
            p["cash"] -= cost
            p["charityOneDie"] = True
            self._log(f"🤝 {p['name']} dona {fmt(cost)} a la caridad. El próximo turno tirará 1 solo dado.")
        else:
            self._log(f"{p['name']} no dona a la caridad.")

    async def handle_market(self, p, card):
        if card["kind"] == "stockBuy":
            max_shares = int(p["cash"] // card["price"])
            if max_shares <= 0:
                self._log(f"{p['name']} no tiene efectivo para aprovechar la oferta de {card['symbol']}.")
                return
            self.last_card = {"deck": "market", "card": card, "maxShares": max_shares}
            self.room.broadcast_state()
            msg = await self.wait_for(p["id"], {"choice"}, default={"type": "choice", "value": {"shares": 0}})
            shares = int(msg["value"].get("shares", 0) or 0)
            if shares > 0:
                shares = min(shares, max_shares)
                cost = shares * card["price"]
                p["cash"] -= cost
                lot = next((s for s in p["stocks"] if s["symbol"] == card["symbol"]), None)
                if lot:
                    total = lot["shares"] + shares
                    lot["buyPrice"] = (lot["buyPrice"] * lot["shares"] + cost) / total
                    lot["shares"] = total
                else:
                    p["stocks"].append({
                        "id": uuid.uuid4().hex[:8], "symbol": card["symbol"],
                        "name": card["symbol"], "shares": shares, "buyPrice": card["price"],
                    })
                self._log(f"📊 {p['name']} aprovecha el consejo y compra {shares} de {card['symbol']} por {fmt(cost)}.")
            else:
                self._log(f"{p['name']} ignora el consejo del broker.")
            return

        # Sales: ask every owner in order (current player first)
        if card["kind"] == "buy":
            eligible = []
            for q in self._owner_order(p):
                assets = [a for a in q["realEstate"] if set(a["tags"]) & set(card["buyTags"])]
                if assets:
                    eligible.append((q, assets))
            for q, assets in eligible:
                await self.ask_sell_real_estate(q, card, assets)
        elif card["kind"] == "buyBusiness":
            for q in self._owner_order(p):
                if q["businesses"]:
                    await self.ask_sell_business(q, card, list(q["businesses"]))
        elif card["kind"] == "stockSell":
            for q in self._owner_order(p):
                lots = [s for s in q["stocks"] if s["symbol"] == card["symbol"] and s["shares"] > 0]
                if lots:
                    await self.ask_sell_stock(q, card, lots)

    def _owner_order(self, current):
        idx = next(i for i, q in enumerate(self.players) if q["id"] == current["id"])
        order = self.players[idx:] + self.players[:idx]
        return order

    async def ask_sell_real_estate(self, p, card, assets):
        self.last_card = {"deck": "marketSell", "card": card, "assets": assets, "kind": "realEstate"}
        self.room.broadcast_state()
        msg = await self.wait_for(p["id"], {"choice"}, default={"type": "choice", "value": {"pass": True}})
        val = msg["value"]
        if val.get("pass"):
            self._log(f"{p['name']} no vende ninguna propiedad.")
            return
        asset_id = val.get("assetId")
        price = int(val.get("price", 0) or 0)
        asset = next((a for a in assets if a["id"] == asset_id), None)
        if asset is None or price <= 0:
            self._log(f"{p['name']} no vende ninguna propiedad.")
            return
        p["cash"] += price
        p["realEstate"] = [a for a in p["realEstate"] if a["id"] != asset_id]
        self._log(f"💵 {p['name']} vendió {asset['name']} por {fmt(price)} (flujo pasivo -{fmt(asset['cashFlow'])}/mes).")

    async def ask_sell_business(self, p, card, assets):
        self.last_card = {"deck": "marketSell", "card": card, "assets": assets, "kind": "business"}
        self.room.broadcast_state()
        msg = await self.wait_for(p["id"], {"choice"}, default={"type": "choice", "value": {"pass": True}})
        val = msg["value"]
        if val.get("pass"):
            self._log(f"{p['name']} no vende ningún negocio.")
            return
        asset_id = val.get("assetId")
        mult = float(val.get("multiplier", 0) or 0)
        asset = next((a for a in assets if a["id"] == asset_id), None)
        if asset is None or mult <= 0:
            self._log(f"{p['name']} no vende ningún negocio.")
            return
        price = int(asset["cashFlow"] * 12 * mult)
        p["cash"] += price
        p["businesses"] = [a for a in p["businesses"] if a["id"] != asset_id]
        self._log(f"💵 {p['name']} vendió {asset['name']} por {fmt(price)} (flujo pasivo -{fmt(asset['cashFlow'])}/mes).")

    async def ask_sell_stock(self, p, card, lots):
        total_shares = sum(s["shares"] for s in lots)
        lo, hi = card["priceRange"]
        self.last_card = {"deck": "marketSell", "card": card, "symbol": card["symbol"], "shares": total_shares, "priceRange": [lo, hi], "kind": "stock"}
        self.room.broadcast_state()
        msg = await self.wait_for(p["id"], {"choice"}, default={"type": "choice", "value": {"pass": True}})
        val = msg["value"]
        if val.get("pass"):
            self._log(f"{p['name']} conserva sus acciones de {card['symbol']}.")
            return
        price = int(val.get("price", 0) or 0)
        if price <= 0:
            self._log(f"{p['name']} conserva sus acciones de {card['symbol']}.")
            return
        gain = price * total_shares
        p["cash"] += gain
        p["stocks"] = [s for s in p["stocks"] if s["symbol"] != card["symbol"]]
        self._log(f"💵 {p['name']} vendió {total_shares} acciones de {card['symbol']} por {fmt(price)} c/u (+{fmt(gain)}).")

    # ------------------------------------------------------------------ transitions

    async def enter_fast_track(self, p):
        p["inFastTrack"] = True
        p["fastTrackPosition"] = 0
        self._log(f"🚀 ¡{p['name']} ESCAPA DE LA CARRERA DE RATAS! Su ingreso pasivo ({fmt(self.passive_income(p))}) supera sus gastos ({fmt(self.total_expenses(p))}). ¡A la pista rápida!")

    def declare_winner(self, p, reason):
        self.winner_id = p["id"]
        p["won"] = True
        self._log(f"🏆 ¡{p['name']} GANA el juego! {reason}.")

    # ------------------------------------------------------------------ state

    def state(self):
        return {
            "phase": self.phase,
            "roomId": self.room.room_id,
            "players": self.players,
            "turnIndex": self.turn_index,
            "pending": self.pending,
            "lastCard": getattr(self, "last_card", None),
            "lastMove": self.last_move,
            "winnerId": self.winner_id,
            "logs": self.logs[-60:],
            "chat": self.room.chat[-60:],
            "ratBoard": data.RAT_RACE_BOARD,
            "ratLabels": data.RAT_RACE_SPACE_LABELS,
            "fastBoard": data.FAST_TRACK_BOARD,
            "fastLabels": data.FAST_TRACK_SPACE_LABELS,
            "boardMeta": {
                "ratColors": data.RAT_RACE_COLORS,
                "fastColors": data.FAST_TRACK_COLORS,
            },
            "availableProfessions": [p for p in data.PROFESSIONS
                                     if p["id"] not in {pl["profession"]["id"] for pl in self.players if pl["profession"]}],
        }
