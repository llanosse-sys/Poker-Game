from .hand import Hand

class Player:
    def __init__(self, name, chips, websocket):
        self.name = name
        self.chips = chips
        self.hand = Hand()
        self.position = None

        self.websocket = websocket

        self.current_bet = 0
        self.total_bet = 0

        self.folded = False
        self.all_in = False

    def fold(self):
        self.folded = True

    def check(self):
        pass

    def bet(self, amount):
        if amount >= self.chips:
            amount = self.chips
            self.chips = 0
            self.current_bet += amount
            self.total_bet += amount
            self.all_in = True
            return amount

        self.chips -= amount
        self.current_bet += amount
        self.total_bet += amount
        return amount

    def reset_for_new_hand(self):
        self.hand.reset()
        self.total_bet = 0
        self.current_bet = 0
        self.folded = False
        self.all_in = False

    async def safe_send(self, message):
        try:
            await self.websocket.send(message)
        except Exception:
            pass
