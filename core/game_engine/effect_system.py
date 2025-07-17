from enum import Enum, auto
from .card import Card

class EffectDuration(Enum):
    PERMANENT = auto()
    END_OF_TURN = auto()

class Effect:
    """Eine abstrakte Basisklasse für alle Effekte im Spiel."""
    def __init__(self, duration: EffectDuration):
        self.duration = duration
        self.target: 'Card' = None # Das Ziel des Effekts

class ModifyPowerToughness(Effect):
    """Ein Effekt, der Power/Toughness einer Kreatur modifiziert."""
    def __init__(self, power_modifier: int, toughness_modifier: int, duration: EffectDuration):
        super().__init__(duration)
        self.power_modifier = power_modifier
        self.toughness_modifier = toughness_modifier



#TODO: Implementieren von allen weiteren im Spiel befindlichen effekten

