from typing import List, Optional, Dict
import random
import logging

from .player import Player
from .card import Card
from .phase_manager import PhaseManager
from .stack_manager import StackManager



class GameState:
    """
    Verwaltet den gesamten Zustand einer einzelnen Magic-Partie.
    Dies ist das zentrale Objekt, das die Regel-Engine antreibt.
    """
    def __init__(self, card_db: Dict):
        self.card_db = card_db
        self.players: List[Player] = [Player(self, 0), Player(self, 1)]
        self.active_player_index: int = 0
        self.turn_number: int = 1
        self.phase_manager = PhaseManager(self)
        self.stack_manager = StackManager(self)

        self.player_with_priority: Optional[int] = None
        self.passed_priority_count: int = 0
       
        
    def grant_priority(self, player_id: int):
        """Übergibt die Priorität an einen Spieler."""
        self.player_with_priority = player_id
        self.passed_priority_count = 0

    def get_player(self, player_id: int) -> Player:
        """Gibt das Spielerobjekt für eine gegebene ID zurück."""
        return self.players[player_id]

    @property
    def active_player(self) -> Player:
        """Gibt den derzeit aktiven Spieler zurück."""
        return self.players[self.active_player_index]

    def start_game(self, decks: List[List[Dict]]):
        """Initialisiert das Spiel, indem Decks geladen und Starthände gezogen werden."""
        for i, player in enumerate(self.players):
            deck_list = decks[i]
            # Erstellt Karteninstanzen aus der Deckliste und lädt sie in die Bibliothek
            player.library = [Card(card_info, player) for card_info in deck_list]
            random.shuffle(player.library)
            
            # Spieler ziehen ihre Starthand von 7 Karten
            for _ in range(7):
                player.draw_card()
        
        # Zufälliger Startspieler
        self.active_player_index = random.randint(0, 1)
        print(f"Spiel beginnt. Spieler {self.active_player.player_id} ist am Zug.")


    

    def assign_combat_damage(self, first_strike: bool):
        """Verrechnet Kampfschaden, getrennt nach Erstschlag."""
        log_prefix = "Erstschlag" if first_strike else "Regulärer"
        logging.info(f"--- {log_prefix} Kampfschaden ---")
        
        attacking_player = self.active_player
        defending_player = self.get_player(1 - attacking_player.player_id)
        
        all_attackers = [c for c in attacking_player.battlefield if c.is_attacking]

        for attacker in all_attackers:
            # Kreaturen mit Erstschlag teilen im ersten Segment Schaden aus.
            # Kreaturen ohne Erstschlag teilen im zweiten Segment Schaden aus.
            # Kreaturen mit Doppelschlag (Double Strike) teilen in beiden Segmenten Schaden aus.
            deals_damage_this_segment = (
                (first_strike and (attacker.has_keyword('First Strike') or attacker.has_keyword('Double Strike'))) or
                (not first_strike and not attacker.has_keyword('First Strike'))
            )

            if not deals_damage_this_segment:
                continue

            damage = int(attacker.static_data.get('power', 0))
            if damage <= 0: continue
            
            if hasattr(attacker, 'blocker'):
                blocker = attacker.blocker
                lethal_damage_to_blocker = blocker.toughness - blocker.damage_marked
                
                # Weist Schaden dem Blocker zu
                actual_damage_to_blocker = min(damage, lethal_damage_to_blocker)
                blocker.damage_marked += actual_damage_to_blocker
                logging.info(f"'{attacker.name}' fügt '{blocker.name}' {actual_damage_to_blocker} Schaden zu.")

                # Prüfe auf Trampelschaden
                if attacker.has_keyword('Trample'):
                    trample_damage = damage - actual_damage_to_blocker
                    if trample_damage > 0:
                        logging.info(f"Trampelschaden: '{attacker.name}' fügt Spieler {defending_player.player_id} {trample_damage} Schaden zu.")
                        defending_player.life -= trample_damage
                
                # Schaden vom Blocker an den Angreifer
                # (Diese Logik bleibt unverändert)
            else:
                # Ungeblockter Schaden
                logging.info(f"'{attacker.name}' fügt Spieler {defending_player.player_id} {damage} Schaden zu.")
                defending_player.life -= damage

    def check_state_based_actions(self):
        """
        Überprüft und wendet zustandsbasierte Aktionen an, bis keine mehr anfallen.
        Momentan nur für tödlichen Schaden implementiert.
        """
        action_happened = True
        while action_happened:
            action_happened = False
            
            # Überprüfe alle Kreaturen aller Spieler
            for player in self.players:
                creatures_on_battlefield = [c for c in player.battlefield if 'Creature' in c.static_data.get('type_line', '')]
                
                for creature in creatures_on_battlefield:
                    if creature.has_lethal_damage():
                        # Bewege die Kreatur vom Schlachtfeld in den Friedhof
                        player.battlefield.remove(creature)
                        player.graveyard.append(creature)
                        action_happened = True
                        logging.info(f"Zustandsbasierte Aktion: '{creature.name}' wird wegen tödlichen Schadens auf den Friedhof gelegt.")
                        # Breche die Schleife ab und starte die Überprüfung von vorne,
                        # da sich der Spielzustand geändert hat.
                        break 
                if action_happened:
                    break   
     


    def __repr__(self) -> str:
        return (f"Turn {self.turn_number}, "
                f"Active Player: {self.active_player.player_id}")