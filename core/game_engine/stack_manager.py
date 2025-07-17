import logging
from typing import List, TYPE_CHECKING
from .effect_system import ModifyPowerToughness, EffectDuration # NEU

if TYPE_CHECKING:
    from .card import Card
    from .game_state import GameState

class StackManager:
    """Verwaltet den Stapel (Stack)."""
    def __init__(self, game_state: 'GameState'):
        self.game_state = game_state
        self.stack: List['Card'] = []

    def add_to_stack(self, spell: 'Card'):
        """Fügt einen Zauberspruch dem Stapel hinzu."""
        logging.info(f"'{spell.name}' wird auf den Stapel gelegt.")
        self.stack.append(spell)

    def resolve_top_item(self):
        """Verrechnet das oberste Element des Stapels, inkl. gezielter Effekte."""
        if not self.stack:
            return
        
        spell = self.stack.pop()
        
        # Harcoded-Logik für Giant Growth
        if spell.name == "Giant Growth":
            if spell.target:
                logging.info(f"'{spell.name}' wird verrechnet. Ziel: '{spell.target.name}'.")
                effect = ModifyPowerToughness(power_modifier=3, toughness_modifier=3, duration=EffectDuration.END_OF_TURN)
                spell.target.active_effects.append(effect)
            else:
                logging.warning(f"'{spell.name}' wurde ohne Ziel verrechnet (Fizzled).")
        
        # Logik für Kreaturen
        elif 'Creature' in spell.static_data.get('type_line', ''):
            logging.info(f"'{spell.name}' wird verrechnet und kommt ins Spiel.")
            spell.owner.hand.remove(spell)
            spell.owner.battlefield.append(spell)
        
        # Spontanzauber/Hexereien gehen nach der Verrechnung auf den Friedhof
        if "Instant" in spell.static_data.get('type_line', '') or "Sorcery" in spell.static_data.get('type_line', ''):
            spell.owner.graveyard.append(spell)
    def is_empty(self) -> bool:
        """Prüft, ob der Stapel leer ist."""
        return not self.stack