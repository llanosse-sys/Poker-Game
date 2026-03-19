class Hand:
    def __init__(self):
        self.cards = []

    def add_card(self, card):
        if len(self.cards) < 2:
            self.cards.append(card)
        else:
            raise ValueError("A hand can only have 2 cards.")

    def reset(self):
        self.cards.clear()

    def __str__(self):
        return ' '.join(str(card) for card in self.cards)
