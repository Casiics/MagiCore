from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from .card import Card
    from .game_state import GameState

class Player:
    """Repräsentiert einen Spieler im Spiel."""
    def __init__(self, game: 'GameState', player_id: int):
        self.game = game
        self.player_id = player_id
        
        self.life: int = 20
        self.mana_pool: Dict[str, int] = {
            'W': 0, 'U': 0, 'B': 0, 'R': 0, 'G': 0, 'C': 0
        }
        
        # Spielzonen
        self.hand: List['Card'] = []
        self.library: List['Card'] = []
        self.graveyard: List['Card'] = []
        self.exile: List['Card'] = []
        self.battlefield: List['Card'] = []

    def __repr__(self) -> str:
        return f"Player(id={self.player_id}, life={self.life})"