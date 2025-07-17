from typing import Dict, Any

class Card:
    """
    Repräsentiert eine einzelne Instanz einer Magic-Karte im Spiel.
    Diese Klasse enthält sowohl die statischen Daten der Karte (aus der DB)
    als auch ihren dynamischen Zustand im Spiel (getappt, Schaden, etc.).
    """
    def __init__(self, card_data: Dict[str, Any], owner: 'Player'):
        self.static_data = card_data
        self.owner = owner
        
        # Dynamische Attribute
        self.is_tapped: bool = False
        self.is_attacking: bool = False
        self.damage_marked: int = 0
        self.counters: Dict[str, int] = {}

    @property
    def name(self) -> str:
        return self.static_data['name']

    def __repr__(self) -> str:
        return f"Card(name='{self.name}')"