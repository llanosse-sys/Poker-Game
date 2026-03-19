import json

from .deck import Deck
from .hand_evaluator import best_hand
from .betting_manager import BettingManager
from .pot_manager import PotManager
from .position_manager import PositionManager

class Game:
    def __init__(self, players, small_blind=5, big_blind=10):
        self.players = players
        self.small_blind_amount = small_blind
        self.big_blind_amount = big_blind

        self.deck = Deck()
        self.pot = 0
        self.community_cards = []
        self.current_bet = 0

        self.dealer_index = 0
        self.current_player_index = 0
        self.last_raise = self.big_blind_amount

        self.betting_manager = BettingManager(self)
        self.pot_manager = PotManager(self)
        self.position_manager = PositionManager(self)

    async def broadcast(self, message):
        import json
        import asyncio
        payload = json.dumps(message)
        await asyncio.gather(*[p.websocket.send(payload) for p in self.players], return_exceptions=True)

    # Runs a complete hand of poker form deal to showdown
    async def gamePlay(self):
        self.deck = Deck()
        self.deck.shuffle()
        self.pot = 0
        self.community_cards.clear()
        self.current_bet = 0

        for player in self.players:
            player.reset_for_new_hand()
        
        self.position_manager.assign_positions()

        await self.broadcast({
            "event": "positions_update",
            "positions": {p.name: p.position for p in self.players}
        })

        await self.preflop()

        active = [p for p in self.players if not p.folded]
        if len(active) > 1:
            await self.flop()

        active = [p for p in self.players if not p.folded]
        if len(active) > 1:
            await self.turn()

        active = [p for p in self.players if not p.folded]
        if len(active) > 1:
            await self.river()

        await self.showdown()
        await self.wait_for_new_round()

        self.position_manager.rotate_dealer()

    # Waits for all players to confirm they're ready for the next hand
    async def wait_for_new_round(self):
        import asyncio
        ready_count = 0

        await self.broadcast({
            "event": "round_over",
            "total_players": len(self.players)
        })

        async def wait_for_player(player):
            nonlocal ready_count
            try:
                raw = await asyncio.wait_for(player.websocket.recv(), timeout=60.0)
            except (asyncio.TimeoutError, Exception):
                return
            data = json.loads(raw)
            if data.get("action") == "new_round_ready":
                ready_count += 1
                await self.broadcast({
                    "event": "new_round_player_ready",
                    "player": player.name,
                    "ready_count": ready_count,
                    "total_players": len(self.players)
                })

        await asyncio.gather(*[wait_for_player(p) for p in self.players])
        await self.broadcast({"event": "new_round_starting"})

    # Deals 2 cards to each player, post blinds, and run betting
    async def preflop(self):
        for _ in range(2):
            for player in self.players:
                player.hand.add_card(self.deck.deal_card())

        for player in self.players:
            await player.safe_send(json.dumps({
                "event": "hole_cards",
                "cards": [str(card) for card in player.hand.cards]
            }))

        self.betting_manager.post_blinds()
        await self.broadcast({
            "event": "chips_update",
            "chips": {p.name: p.chips for p in self.players}
        })
        await self.betting_manager.betting_round()

    # Deals another community card and runs another betting round
    async def flop(self):
        for _ in range(3):
            self.community_cards.append(self.deck.deal_card())

        await self.broadcast({
            "event": "community_cards",
            "stage": "flop",
            "cards": [str(card) for card in self.community_cards]
        })

        self.betting_manager.reset_bets()
        await self.betting_manager.betting_round()

    # Deals another community card and runs another betting round
    async def turn(self):
        self.community_cards.append(self.deck.deal_card())

        await self.broadcast({
            "event": "community_cards",
            "stage": "turn",
            "cards": [str(card) for card in self.community_cards]
        })

        self.betting_manager.reset_bets()
        await self.betting_manager.betting_round()

    # Deals another community card and runs another betting round
    async def river(self):
        self.community_cards.append(self.deck.deal_card())

        await self.broadcast({
            "event": "community_cards",
            "stage": "river",
            "cards": [str(card) for card in self.community_cards]
        })

        self.betting_manager.reset_bets()
        await self.betting_manager.betting_round()

    # Last and final round, determines a winner and distributes pot
    async def showdown(self):
        active_players = [p for p in self.players if not p.folded]
        
        # If only one player left, they win without hand evaluation
        if len(active_players) == 1:
            winner = active_players[0]
            winner.chips += self.pot
            await self.broadcast({
                "event": "showdown",
                "pot_number": 1,
                "pot_amount": self.pot,
                "is_side_pot": False,
                "winners": [winner.name],
                "hand_name": "Everyone folded",
                "split_amount": self.pot
            })
            self.pot = 0
            await self.broadcast({
                "event": "chips_update",
                "chips": {p.name: p.chips for p in self.players}
            })
            return
        
        await self.broadcast({
            "event": "reveal_cards",
            "hands": {
                p.name: [str(card) for card in p.hand.cards]
                for p in active_players
            }
        })

        pots = self.pot_manager.build_pots(active_players)
        await self.pot_manager.distribute_pot(pots)
        self.pot = 0

        await self.broadcast({
            "event": "chips_update",
            "chips": {p.name: p.chips for p in self.players}
        })
