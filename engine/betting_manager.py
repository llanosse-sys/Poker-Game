import json
import asyncio

class BettingManager:
    def __init__(self, game):
        self.game = game

    # Forces small blind and big blind to post their bets
    def post_blinds(self):
        for player in self.game.players:
            if player.position == "SB":
                amount = player.bet(self.game.small_blind_amount)
                self.game.pot += amount
            elif player.position == "BB":
                amount = player.bet(self.game.big_blind_amount)
                self.game.pot += amount

        self.game.current_bet = self.game.big_blind_amount
        self.game.last_raise = self.game.big_blind_amount

    # Resets bets for a new post-flop betting round and sets action to start from SB
    def reset_bets(self):
        self.game.current_bet = 0
        self.game.last_raise = self.game.big_blind_amount
        for player in self.game.players:
            player.current_bet = 0
        # Post-flop action starts from the first active player left of the dealer (SB position)
        num_players = len(self.game.players)
        sb_index = (self.game.dealer_index + 1) % num_players
        self.game.current_player_index = sb_index

    # Run a full betting round until all players have acted
    async def betting_round(self):
        num_players = len(self.game.players)
        i = self.game.current_player_index

        players_done = set()

        while True:
            player = self.game.players[i]

            if not player.folded and not player.all_in:
                to_call = self.game.current_bet - player.current_bet
                action, raise_amount = await self.get_player_action(player, to_call)

                # All of the actions that a player can act on
                if action == "fold":
                    player.fold()
                elif action == "call":
                    amount = player.bet(to_call)
                    self.game.pot += amount
                    players_done.add(player)
                elif action == "check":
                    players_done.add(player)
                elif action == "raise":
                    total = to_call + raise_amount
                    amount = player.bet(total)
                    self.game.pot += amount
                    self.game.current_bet = player.current_bet
                    self.game.last_raise = raise_amount
                    players_done.clear()
                    players_done.add(player)
                
                await self.game.broadcast({
                    "event": "player_action",
                    "player": player.name,
                    "action": action,
                    "raise_amount": raise_amount,
                    "pot": self.game.pot,
                    "current_bet": self.game.current_bet,
                    "chips": player.chips
                })

            # This line moves on to the next player that is still in this betting round
            i = (i + 1) % num_players

            active_players = [p for p in self.game.players if not p.folded]

            if len(active_players) <= 1:
                break

            non_allin_active = [p for p in active_players if not p.all_in]
            if not non_allin_active or all(p in players_done for p in non_allin_active):
                break

    # Asks the player what they want to do
    async def get_player_action(self, player, to_call):
        actions = []
        if to_call > 0:
            actions = ["fold", "call", "raise"]
        else:
            actions = ["check", "raise"]

        await player.safe_send(json.dumps({
            "event": "your_turn",
            "actions": actions,
            "to_call": to_call,
            "pot": self.game.pot,
            "current_bet": self.game.current_bet,
            "your_chips": player.chips
        }))

        try:
            raw = await asyncio.wait_for(player.websocket.recv(), timeout=120.0)
        except Exception:
            return "fold", 0

        data = json.loads(raw)

        action = data.get("action")
        raise_amount = data.get("raise_amount", 0)

        # Validate action is one of the expected values
        if action not in actions:
            action = "fold"

        # Validate raise amount meets minimum raise requirement
        if action == "raise":
            try:
                raise_amount = int(raise_amount)
            except (TypeError, ValueError):
                raise_amount = self.game.last_raise
            raise_amount = max(raise_amount, self.game.last_raise)

        return action, raise_amount
