class PositionManager:
    def __init__(self, game):

        # Takes in the main Game object as a paremeter
        self.game = game

    # Assigns positions to players based on dealer button.
    # Dealer -> Small Blind -> Big Blind -> UTG -> Middle Position
    def assign_positions(self):
        num_players = len(self.game.players)
        dealer = self.game.dealer_index

        if num_players == 2:
            self.game.players[dealer].position = "SB"
            bb_index = (dealer + 1) % num_players
            self.game.players[bb_index].position = "BB"
            self.game.current_player_index = dealer
        else:
            sb_index = (dealer + 1) % num_players
            bb_index = (dealer + 2) % num_players
            utg_index = (dealer + 3) % num_players

            for i, player in enumerate(self.game.players):
                if i == dealer:
                    player.position = "Dealer"
                elif i == sb_index:
                    player.position = "SB"
                elif i == bb_index:
                    player.position = "BB"
                elif i == utg_index:
                    player.position = "UTG"
                else:
                    player.position = "MP"

            self.game.current_player_index = (bb_index + 1) % num_players

    # Moves dealer button to the next player

    def rotate_dealer(self):
        self.game.dealer_index = (
            self.game.dealer_index + 1) % len(self.game.players)
