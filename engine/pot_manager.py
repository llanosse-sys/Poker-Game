class PotManager:
    def __init__(self, game):
        self.game = game

    # Creates main pot and side pots based on how much each player bet
    # Returns a list of pots with elgible players for each
    def build_pots(self, active_players):

        # For each active_players p, sort by there total_bet from smallest to largest
        all_players = sorted(self.game.players, key=lambda p: p.total_bet)
        active_set = set(active_players)

        pots = []
        previous_bet = 0

        # Loops through each player from smallest bet to largets
        for i, player in enumerate(all_players):
            bet_diff = player.total_bet - previous_bet

            if bet_diff > 0:
                # [i:] means from index i to the end of the list
                contributors = all_players[i:]

                pot_amount = bet_diff * len(contributors)

                eligible = [p for p in contributors if p in active_set]
                pots.append({
                    "amount": pot_amount,
                    "eligible_players": eligible
                })

                previous_bet = player.total_bet

        return pots

    # Evaluates hands and distributes each pot to the winner(s)
    async def distribute_pot(self, pots):
        from engine.hand_evaluator import best_hand
        import json

        pot_number = 1

        for pot in pots:
            eligible_players = pot["eligible_players"]
            pot_amount = pot["amount"]

            # Creates an empty dictionary to store each players hand score
            scores = {}

            # Loops through all of eligible_players for this pot
            for player in eligible_players:
                # These 2 lines evaulates which player has the best hands
                seven_cards = player.hand.cards + self.game.community_cards
                scores[player] = best_hand(seven_cards)

            # Finds the highest score(best hand)
            best_score = max(scores.values())
            winners = [p for p, score in scores.items() if score == best_score]

            hand_name = self.get_hand_name(best_score[0])

            split_amount = pot_amount // len(winners)
            remainder = pot_amount % len(winners)
            for winner in winners:
                winner.chips += split_amount
            winners[0].chips += remainder

            await self.game.broadcast({
                "event": "showdown",
                "pot_number": pot_number,
                "pot_amount": pot_amount,
                "is_side_pot": len(pots) > 1,
                "winners": [w.name for w in winners],
                "hand_name": hand_name,
                "split_amount": split_amount
            })

            pot_number += 1

    def get_hand_name(self, hand_rank):
        hand_names = {
            1: "High Card",
            2: "One Pair",
            3: "Two Pair",
            4: "Three of a Kind",
            5: "Straight",
            6: "Flush",
            7: "Full House",
            8: "Four of a Kind",
            9: "Straight Flush"
        }
        return hand_names.get(hand_rank, "Unknown Hand")
