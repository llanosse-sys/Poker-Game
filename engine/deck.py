import random
from .card import Card


class Deck:
    def __init__(self):
        ranks = ["2", "3", "4", "5", "6", "7",
                "8", "9", "10", "J", "Q", "K", "A"]
        suits = ["♠", "♥", "♦", "♣"]
        self.cards = [Card(rank, suit) for suit in suits for rank in ranks]

    def shuffle(self):
        random.shuffle(self.cards)

    def deal_card(self):
        return self.cards.pop()
