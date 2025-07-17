from enum import Enum, auto
import logging
from typing import TYPE_CHECKING # NEU: Import für Type-Checking

# NEU: Dieser Block bricht den Import-Kreislauf
if TYPE_CHECKING:
    from .game_state import GameState
    from .effect_system import EffectDuration

class TurnPhase(Enum):
    BEGINNING = auto()
    PRECOMBAT_MAIN = auto()
    COMBAT = auto()
    POSTCOMBAT_MAIN = auto()
    ENDING = auto()

class TurnStep(Enum):
    UNTAP = auto()
    UPKEEP = auto()
    DRAW = auto()
    # Main Phase steps are handled by player priority
    BEGIN_COMBAT = auto()
    DECLARE_ATTACKERS = auto()
    DECLARE_BLOCKERS = auto()
    FIRST_STRIKE_DAMAGE = auto() # NEU
    COMBAT_DAMAGE = auto()
    END_OF_COMBAT = auto()
    # Main Phase
    END_STEP = auto()
    CLEANUP = auto()

class PhaseManager:
    """Steuert den Phasen- und Schrittablauf eines Spielzugs."""
    def __init__(self, game_state: 'GameState'):
        self.game_state = game_state
        self.current_phase = TurnPhase.BEGINNING
        self.current_step = TurnStep.UNTAP
        # Definiert die Reihenfolge der Schritte für einen kompletten Zug
        self.step_order = [
            TurnStep.UNTAP, TurnStep.UPKEEP, TurnStep.DRAW,
            # Precombat Main Phase (implizit)
            TurnStep.BEGIN_COMBAT, TurnStep.DECLARE_ATTACKERS, TurnStep.DECLARE_BLOCKERS,
            TurnStep.FIRST_STRIKE_DAMAGE, # NEU
            TurnStep.COMBAT_DAMAGE, TurnStep.END_OF_COMBAT,
            # Postcombat Main Phase (implizit)
            TurnStep.END_STEP, TurnStep.CLEANUP
        ]
        self.step_index = 0

    def advance_to_next_step(self):
        """Schaltet zum nächsten Schritt im Zug weiter und führt die Aktionen aus."""
        # Aktionen des aktuellen Schritts ausführen
        self.execute_current_step_actions()

        # Zum nächsten Schritt wechseln
        self.step_index += 1
        if self.step_index >= len(self.step_order):
            self.end_turn()
        else:
            self.current_step = self.step_order[self.step_index]
            # Phasen-Update für die Logik
            if self.current_step == TurnStep.BEGIN_COMBAT:
                self.current_phase = TurnPhase.COMBAT
            elif self.current_step == TurnStep.END_STEP:
                self.current_phase = TurnPhase.ENDING

    def execute_current_step_actions(self):
        """Führt automatische, regelbasierte Aktionen für den aktuellen Schritt aus."""
        active_player = self.game_state.active_player
        opponent = self.game_state.get_player(1 - active_player.player_id)
        logging.info(f"--- {self.current_step.name} (Spieler {active_player.player_id}) ---")

        if self.current_step == TurnStep.UNTAP:
            for permanent in active_player.battlefield:
                permanent.is_tapped = False
                permanent.is_attacking = False
                permanent.summoning_sick = False
        
        elif self.current_step == TurnStep.DRAW:
            # The draw action happens only if it's the active player's turn,
            # which is handled by the main game loop's logic.
            # In a more complex game, we'd check against turn number.
            if self.game_state.turn_number > 0 or self.game_state.active_player_index == 1:
                 active_player.draw_card()

        elif self.current_step == TurnStep.DECLARE_ATTACKERS:
            active_player.declare_attackers()

        elif self.current_step == TurnStep.DECLARE_BLOCKERS:
            opponent.declare_blockers()

        elif self.current_step == TurnStep.FIRST_STRIKE_DAMAGE:
            self.game_state.assign_combat_damage(first_strike=True)

        elif self.current_step == TurnStep.COMBAT_DAMAGE:
            self.game_state.assign_combat_damage(first_strike=False)
            
        elif self.current_step == TurnStep.CLEANUP:
            # Reset "lands played" count for the active player
            active_player.lands_played_this_turn = 0
            
            # Reset effects and mana for ALL players
            for p in self.game_state.players: # CORRECTED: was self.game
                # Remove "until end of turn" effects
                for permanent in p.battlefield:
                    permanent.active_effects = [
                        effect for effect in permanent.active_effects 
                        if effect.duration != EffectDuration.END_OF_TURN
                    ]
                # Reset mana pools
                p.mana_pool = {k: 0 for k in p.mana_pool}
            
    def end_turn(self):
        """Beendet den aktuellen Zug und übergibt an den nächsten Spieler."""
        print(f"--- Zugende für Spieler {self.game_state.active_player.player_id} ---")
        self.game_state.active_player_index = 1 - self.game_state.active_player_index
        if self.game_state.active_player_index == 0:
            self.game_state.turn_number += 1
        
        self.step_index = 0
        self.current_step = self.step_order[0]
        self.current_phase = TurnPhase.BEGINNING
