from collections import Counter
from itertools import combinations

RANK_VALUES = {
    "2": 2, "3": 3, "4": 4, "5": 5, "6": 6,
    "7": 7, "8": 8, "9": 9, "10": 10,
    "J": 11, "Q": 12, "K": 13, "A": 14
}

HAND_RANKS = {
    "HIGH_CARD": 1,
    "PAIR": 2,
    "TWO_PAIR": 3,
    "THREE_KIND": 4,
    "STRAIGHT": 5,
    "FLUSH": 6,
    "FULL_HOUSE": 7,
    "FOUR_KIND": 8,
    "STRAIGHT_FLUSH": 9
}


def evaluate_five_cards(cards):
    ranks = sorted([RANK_VALUES[c.rank] for c in cards], reverse=True)
    suits = [c.suit for c in cards]

    rank_counts = Counter(ranks)
    counts = sorted(rank_counts.values(), reverse=True)
    unique_ranks = sorted(rank_counts.keys(), reverse=True)

    is_flush = len(set(suits)) == 1
    is_straight = len(unique_ranks) == 5 and unique_ranks[0] - unique_ranks[-1] == 4

    # Ace-low straight (A-2-3-4-5)
    ace_low = set(ranks) == {14, 5, 4, 3, 2}
    if ace_low:
        is_straight = True
        ranks = [5, 4, 3, 2, 1]

    # Build tiebreak list: sort unique ranks by (count desc, rank desc), then expand.
    # This is done using rank_counts BEFORE any ace-low rank remapping, which is safe
    # because rank_counts was built from the original ranks and ace-low straights
    # never need tiebreak_ranks (they always use the remapped `ranks` list directly).
    tiebreak_ranks = []
    for r in sorted(rank_counts.keys(), key=lambda r: (rank_counts[r], r), reverse=True):
        tiebreak_ranks.extend([r] * rank_counts[r])

    if is_straight and is_flush:
        return (HAND_RANKS["STRAIGHT_FLUSH"], ranks)

    if counts[0] == 4:
        return (HAND_RANKS["FOUR_KIND"], tiebreak_ranks)

    if counts[0] == 3 and counts[1] == 2:
        return (HAND_RANKS["FULL_HOUSE"], tiebreak_ranks)

    if is_flush:
        return (HAND_RANKS["FLUSH"], ranks)

    if is_straight:
        return (HAND_RANKS["STRAIGHT"], ranks)

    if counts[0] == 3:
        return (HAND_RANKS["THREE_KIND"], tiebreak_ranks)

    if counts[0] == 2 and counts[1] == 2:
        return (HAND_RANKS["TWO_PAIR"], tiebreak_ranks)

    if counts[0] == 2:
        return (HAND_RANKS["PAIR"], tiebreak_ranks)

    return (HAND_RANKS["HIGH_CARD"], ranks)


def best_hand(seven_cards):
    best = None
    for combo in combinations(seven_cards, 5):
        score = evaluate_five_cards(combo)
        if best is None or score > best:
            best = score
    return best