from typing import Dict, Any, TYPE_CHECKING, List
from .effect_system import Effect # NEU

if TYPE_CHECKING:
    from .player import Player
class Card:
    """
    Repräsentiert eine einzelne Instanz einer Magic-Karte im Spiel.
    """
    def __init__(self, card_data: Dict[str, Any], owner: 'Player'):
        self.static_data = card_data
        self.owner = owner
        
        # Dynamische Attribute
        self.is_tapped: bool = False
        self.is_attacking: bool = False
        self.summoning_sick: bool = 'Creature' in self.static_data.get('type_line', '')
        self.damage_marked: int = 0
        self.counters: Dict[str, int] = {}
        self.active_effects: List[Effect] = [] # NEU: Liste für temporäre Effekte
        self.target: 'Card' = None # Wird verwendet, wenn die Karte auf dem Stapel ist

    @property
    def name(self) -> str:
        return self.static_data['name']
    
    @property
    def power(self) -> int:
        """Berechnet die aktuelle Stärke inklusive aller Effekte."""
        base_power = int(self.static_data.get('power', 0))
        modifier = sum(effect.power_modifier for effect in self.active_effects if hasattr(effect, 'power_modifier'))
        return base_power + modifier

    @property
    def toughness(self) -> int:
        """Berechnet die aktuelle Widerstandskraft inklusive aller Effekte."""
        base_toughness = int(self.static_data.get('toughness', 0))
        modifier = sum(effect.toughness_modifier for effect in self.active_effects if hasattr(effect, 'toughness_modifier'))
        return base_toughness + modifier

    def is_land(self) -> bool:
        """Prüft, ob die Karte den Typ 'Land' in ihrer Typenzeile hat."""
        return 'Land' in self.static_data.get('type_line', '')

    def toughness(self) -> int:
        return int(self.static_data.get('toughness', 0))

    def is_land(self) -> bool:
        """Prüft, ob die Karte den Typ 'Land' in ihrer Typenzeile hat."""
        return 'Land' in self.static_data.get('type_line', '')
    
    def has_lethal_damage(self) -> bool:
        """Prüft, ob die Kreatur tödlichen Schaden erlitten hat."""
        if self.toughness <= 0: # Gilt für 0/X Kreaturen
            return True
        return self.damage_marked >= self.toughness
    
    def has_keyword(self, keyword: str) -> bool:
        """Prüft, ob die Karte ein bestimmtes Schlüsselwort hat."""
        return keyword.lower() in [k.lower() for k in self.static_data.get('keywords', [])]
    

    
    def __repr__(self) -> str:
        return f"Card(name='{self.name}')"