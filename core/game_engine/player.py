from typing import List, Dict, Optional, TYPE_CHECKING
import logging
import copy             # <-- HINZUGEFÜGT
import itertools        # <-- HINZUGEFÜGT
from collections import defaultdict

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
        
        self.hand: List['Card'] = []
        self.library: List['Card'] = []
        self.graveyard: List['Card'] = []
        self.exile: List['Card'] = []
        self.battlefield: List['Card'] = []
        
        self.lands_played_this_turn: int = 0

    def draw_card(self) -> Optional['Card']:
        """Zieht die oberste Karte der Bibliothek und fügt sie der Hand hinzu."""
        if not self.library:
            logging.warning(f"Spieler {self.player_id} versucht, von einer leeren Bibliothek zu ziehen.")
            # TODO: Handle game loss due to empty library
            return None
        
        card = self.library.pop(0)
        self.hand.append(card)
        logging.info(f"Spieler {self.player_id} zieht {card.name}.")
        return card


    def get_available_actions(self) -> List[str]:
        """Gibt eine Liste aller möglichen Aktionen zurück, inkl. Spontanzauber und aktivierbarer Fähigkeiten."""
        actions = ["pass_priority"]

        # 1. Prüfe auf Zauber von der Hand
        for card in self.hand:
            # Ist es ein Spontanzauber ODER sind wir in unserer Hauptphase bei leerem Stack?
            is_main_phase = "MAIN" in self.game.phase_manager.current_phase.name
            is_our_turn = self.game.active_player.player_id == self.player_id
            
            if "Instant" in card.static_data.get('type_line', '') or (is_main_phase and is_our_turn and self.game.stack_manager.is_empty()):
                cost = int(card.static_data.get('cmc', 99))
                # TODO: Verfeinere Manaprüfung für farbige Kosten
                available_mana = sum(1 for p in self.battlefield if p.is_land() and not p.is_tapped)
                if available_mana >= cost:
                    actions.append(f"cast_{card.name}")

        # 2. Prüfe auf aktivierbare Fähigkeiten von Kreaturen auf dem Schlachtfeld
        for permanent in self.battlefield:
            if permanent.name == "Llanowar Elves" and not permanent.is_tapped:
                actions.append(f"activate_{permanent.name}")

        return actions


    def play_land(self, card_in_hand: 'Card') -> bool:
        """Versucht, eine Landkarte von der Hand auf das Schlachtfeld zu spielen."""
        if not card_in_hand.is_land():
            logging.error(f"Aktion fehlgeschlagen: {card_in_hand.name} ist kein Land.")
            return False
        
        if self.lands_played_this_turn > 0:
            logging.error(f"Aktion fehlgeschlagen: Spieler {self.player_id} hat bereits ein Land gespielt.")
            return False

        # Bewege die Karte von der Hand auf das Schlachtfeld
        self.hand.remove(card_in_hand)
        self.battlefield.append(card_in_hand)
        self.lands_played_this_turn += 1
        
        logging.info(f"Spieler {self.player_id} spielt {card_in_hand.name}.")
        return True

    def _parse_cost_string(self, cost_string: str) -> Dict[str, int]:
        """A helper function to parse mana cost strings like '{2}{W}{U}' into a dictionary."""
        cost = defaultdict(int)
        if not cost_string:
            return cost
        
        parts = cost_string.replace('{', '').split('}')[:-1]
        for part in parts:
            if part.isdigit():
                cost['generic'] += int(part)
            else:
                cost[part.upper()] += 1
        return cost

    def tap_for_cost(self, cost_dict: Dict[str, int]) -> List['Card']:
        """
        An intelligent method to tap lands for a specific cost.
        It prioritizes tapping lands for required colors first.
        Returns a list of the lands that were tapped.
        """
        tapped_lands = []
        # A simple map for basic land types. This can be expanded.
        color_map = {'Forest': 'G', 'Island': 'U', 'Swamp': 'B', 'Mountain': 'R', 'Plains': 'W'}
        
        untapped_lands = [p for p in self.battlefield if p.is_land() and not p.is_tapped]
        
        # 1. Pay for specific colored costs first
        for color, amount in cost_dict.items():
            if color == 'generic': continue
            
            needed = amount
            for land in untapped_lands:
                if needed == 0: break
                if color_map.get(land.name) == color and land not in tapped_lands:
                    self.mana_pool[color] += 1
                    tapped_lands.append(land)
                    needed -= 1

        # 2. Pay for generic costs with remaining lands
        generic_needed = cost_dict.get('generic', 0)
        for land in untapped_lands:
            if generic_needed == 0: break
            if land not in tapped_lands:
                # Any land can produce mana for generic costs.
                # For simplicity, we add its primary color to the pool.
                color_produced = color_map.get(land.name, 'C') 
                self.mana_pool[color_produced] += 1
                tapped_lands.append(land)
                generic_needed -= 1
        
        # Physically tap all lands used in the transaction
        for land in tapped_lands:
            land.is_tapped = True
            logging.info(f"Spieler {self.player_id} tappt '{land.name}' für Mana.")

        return tapped_lands


    def cast_spell(self, card_in_hand: 'Card') -> bool:
        """
        Orchestrates casting a spell with precise mana payment and rollback on failure.
        """
        cost_string = card_in_hand.static_data.get('mana_cost', '')
        if not cost_string:
            logging.error(f"'{card_in_hand.name}' hat keine Manakosten.")
            return False

        cost_dict = self._parse_cost_string(cost_string)
        
        # Step 1: Tap lands and fill the mana pool.
        tapped_lands = self.tap_for_cost(cost_dict)

        # Step 2: Try to pay the cost from the pool.
        mana_pool_backup = self.mana_pool.copy()
        
        # Pay colored costs
        for color, amount in cost_dict.items():
            if color == 'generic': continue
            if self.mana_pool[color] < amount:
                # FAILURE: Rollback and exit
                logging.error(f"Bezahlung für '{card_in_hand.name}' fehlgeschlagen. Mache Aktion rückgängig.")
                self.mana_pool = mana_pool_backup
                for land in tapped_lands: land.is_tapped = False
                return False
            self.mana_pool[color] -= amount

        # Pay generic costs
        generic_cost = cost_dict.get('generic', 0)
        for color in ['W', 'U', 'B', 'R', 'G', 'C']:
            payable = min(generic_cost, self.mana_pool[color])
            self.mana_pool[color] -= payable
            generic_cost -= payable
            if generic_cost <= 0: break
        
        if generic_cost > 0:
            # FAILURE: Rollback and exit if generic costs couldn't be paid
            logging.error(f"Bezahlung für '{card_in_hand.name}' fehlgeschlagen. Mache Aktion rückgängig.")
            self.mana_pool = mana_pool_backup
            for land in tapped_lands: land.is_tapped = False
            return False

        # SUCCESS
        logging.info(f"Kosten für '{card_in_hand.name}' erfolgreich bezahlt.")
        self.game.stack_manager.add_to_stack(card_in_hand)
        return True


    def declare_attackers(self):
        """
        KI-Logik: Findet die optimale Kombination von Angreifern durch Simulation
        aller möglichen Angriffsszenarien.
        """
        potential_attackers = [
            c for c in self.battlefield 
            if 'Creature' in c.static_data.get('type_line', '') 
            and not c.is_tapped 
            and (not c.summoning_sick or c.has_keyword('Haste'))
        ]
        
        best_attack_combination = []
        # Der Basis-Score ist der Zustand, in dem nicht angegriffen wird.
        best_score = self.evaluate_state() 
        logging.info(f"KI-Angriffsanalyse: Basis-Score (kein Angriff) = {best_score:.2f}")

        # Iteriere durch alle möglichen Kombinationen von Angreifern (von 1 bis alle)
        for i in range(1, len(potential_attackers) + 1):
            for combo in itertools.combinations(potential_attackers, i):
                # Simuliere den Angriff für diese spezifische Kombination
                sim_game = copy.deepcopy(self.game)
                sim_player = sim_game.get_player(self.player_id)
                
                # Holen der Karten-Äquivalente im simulierten Spiel
                sim_combo_ids = [card.static_data['name'] for card in combo] # Vereinfacht über Namen
                sim_attackers = [c for c in sim_player.battlefield if c.name in sim_combo_ids]
                
                for attacker in sim_attackers:
                    attacker.is_attacking = True
                
                # Lasse den Gegner auf den simulierten Angriff reagieren
                sim_opponent = sim_game.get_player(1 - self.player_id)
                sim_opponent.declare_blockers() # Gegner nutzt seine Block-Logik
                sim_game.assign_combat_damage()
                sim_game.check_state_based_actions()

                # Bewerte das Ergebnis
                current_score = sim_player.evaluate_state()

                if current_score > best_score:
                    best_score = current_score
                    best_attack_combination = combo
        
        if best_attack_combination:
            logging.info(f"Entscheidung: Optimaler Angriff gefunden mit Score {best_score:.2f}. Greife an mit: {[c.name for c in best_attack_combination]}")
            # Führe den besten gefundenen Angriff im echten Spiel aus
            for attacker_card in best_attack_combination:
                # Finde die echte Karte im Spielzustand
                real_attacker = next(c for c in self.battlefield if c.static_data['oracle_id'] == attacker_card.static_data['oracle_id'])
                real_attacker.is_attacking = True
                real_attacker.is_tapped = True
        else:
            logging.info("Entscheidung: Kein vorteilhafter Angriff gefunden.")

    def declare_blockers(self):
        """
        KI-Logik: Findet die beste Verteidigung durch eine wertorientierte Zuweisung
        von Blockern zu Angreifern.
        """
        attackers = [c for c in self.game.active_player.battlefield if c.is_attacking]
        potential_blockers = [c for c in self.battlefield if 'Creature' in c.static_data.get('type_line', '') and not c.is_tapped]
        
        if not attackers or not potential_blockers:
            return

        # Bewerte jeden möglichen Block
        for attacker in attackers:
            best_blocker_for_this_attacker = None
            # Der Basis-Fall ist, nicht zu blocken. Schaden geht durch.
            best_trade_value = -int(attacker.static_data.get('power', 0)) # Negativer Wert des Lebensverlusts

            for blocker in potential_blockers:
                # Simuliere den Trade-Wert
                attacker_power = int(attacker.static_data.get('power', 0))
                attacker_toughness = attacker.toughness
                blocker_power = int(blocker.static_data.get('power', 0))
                blocker_toughness = blocker.toughness

                # Bewertet, welche Kreaturen sterben würden
                attacker_dies = blocker_power >= attacker_toughness
                blocker_dies = attacker_power >= blocker_toughness

                # Wert der Kreaturen (Power + Toughness als Heuristik)
                attacker_value = attacker_power + attacker_toughness
                blocker_value = blocker_power + blocker_toughness

                trade_value = 0
                if attacker_dies:
                    trade_value += attacker_value
                if blocker_dies:
                    trade_value -= blocker_value
                
                if trade_value > best_trade_value:
                    best_trade_value = trade_value
                    best_blocker_for_this_attacker = blocker

            if best_blocker_for_this_attacker:
                logging.info(f"KI-Block-Analyse: Bester Block für '{attacker.name}' ist '{best_blocker_for_this_attacker.name}' (Trade-Wert: {best_trade_value}).")
                # Weist den Blocker zu, aber nur, wenn er noch nicht verwendet wird
                if not hasattr(best_blocker_for_this_attacker, 'is_blocking'):
                    attacker.blocker = best_blocker_for_this_attacker
                    best_blocker_for_this_attacker.is_blocking = True # Markiere als verwendet

    def evaluate_state(self) -> float:
        """
        Berechnet einen Score für den aktuellen Spielzustand aus Sicht dieses Spielers.
        Dies ist eine einfache, heuristische Bewertungsfunktion.
        """
        score = 0.0
        opponent = self.game.get_player(1 - self.player_id)

        # 1. Lebenspunkte sind der wichtigste Faktor
        score += self.life * 1.5
        score -= opponent.life * 1.5

        # 2. Kreaturen auf dem Schlachtfeld (Board Presence)
        for creature in self.battlefield:
            if 'Creature' in creature.static_data.get('type_line', ''):
                # Wert einer Kreatur = Power + Toughness
                score += int(creature.static_data.get('power', 0))
                score += creature.toughness

        for creature in opponent.battlefield:
             if 'Creature' in creature.static_data.get('type_line', ''):
                score -= int(creature.static_data.get('power', 0))
                score -= creature.toughness
        
        # 3. Karten auf der Hand (Card Advantage)
        score += len(self.hand) * 0.5
        score -= len(opponent.hand) * 0.5

        return score


    

    def choose_action(self) -> str:
        """
        Die KI wählt die beste Aktion aus der Liste der verfügbaren Aktionen.
        Momentan wird immer die erste Nicht-Passen-Aktion gewählt.
        """
        available_actions = self.get_available_actions()
        # In einer echten KI würde hier die Zustandsbewertung für jede Aktion erfolgen.
        if len(available_actions) > 1:
            # Wähle die erste Aktion, die nicht "pass_priority" ist.
            action_to_take = next((a for a in available_actions if a != "pass_priority"), "pass_priority")
            logging.info(f"KI Spieler {self.player_id} wählt Aktion: {action_to_take}")
            return action_to_take

        return "pass_priority"

    def __repr__(self) -> str:
        return f"Player(id={self.player_id}, life={self.life}, hand_size={len(self.hand)})"