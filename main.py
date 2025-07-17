import json
import logging
from core.game_engine.game_state import GameState

def load_card_database(path="core/data/card_db.json"):
    """Lädt die Kartendatenbank aus der JSON-Datei."""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def build_simple_deck(card_db, card_names, num_each=1):
    """Erstellt eine einfache Deckliste aus einer Liste von Kartennamen."""
    deck = []
    for name in card_names:
        # Finde die Oracle-ID für den Kartennamen
        oracle_id = next((oid for oid, data in card_db.items() if data['name'] == name), None)
        if oracle_id:
            for _ in range(num_each):
                deck.append(card_db[oracle_id])
    return deck

def run_simulation():
    """
    Führt eine Spielsimulation mit einem regelkonformen Prioritätssystem durch.
    """
    print("Initialisiere MagiCore Simulation mit Prioritätssystem...")


    card_db = load_card_database()

    deck_cards = ["Forest"] * 25 + ["Grizzly Bears"] * 35 # Grizzly Bears ist 2/2
    deck_list = build_simple_deck(card_db, deck_cards)
    
    game = GameState(card_db)
    game.start_game([deck_list, deck_list])

    game_over = False
    max_turns = 10 # Sicherheitsnetz gegen Endlosschleifen

    while not game_over and game.turn_number <= max_turns:
        # Führe zu Beginn eines Schrittes regelbasierte Aktionen aus
        game.phase_manager.execute_current_step_actions()
        game.check_state_based_actions()

        # Nach der Aktion bekommt der aktive Spieler Priorität
        game.grant_priority(game.active_player.player_id)
        
        action_in_step_loop = True
        while action_in_step_loop:
            player_with_prio = game.get_player(game.player_with_priority)
            action = player_with_prio.choose_action()

            if action == "pass_priority":
                game.passed_priority_count += 1
                game.player_with_priority = 1 - game.player_with_priority
            else:
                # AKTION AUSFÜHREN
                if action.startswith("cast_"):
                    card_name = action.replace("cast_", "")
                    card_to_cast = next((c for c in player_with_prio.hand if c.name == card_name), None)
                    if card_to_cast:
                        player_with_prio.cast_spell(card_to_cast)
                
                elif action.startswith("activate_"):
                    # Logik für aktivierbare Fähigkeiten
                    permanent_name = action.replace("activate_", "")
                    permanent_to_activate = next((p for p in player_with_prio.battlefield if p.name == permanent_name), None)
                    
                    if permanent_to_activate and not permanent_to_activate.is_tapped:
                        # Harcoded-Effekt für Llanowar Elfen
                        if permanent_to_activate.name == "Llanowar Elves":
                            logging.info(f"Spieler {player_with_prio.player_id} aktiviert '{permanent_to_activate.name}' für grünes Mana.")
                            permanent_to_activate.is_tapped = True
                            player_with_prio.mana_pool['G'] += 1
                
                # Nach einer erfolgreichen Aktion bekommt der aktive Spieler wieder Priorität
                game.grant_priority(game.active_player.player_id)
            
            # Prüfe, ob der Schritt oder die Phase beendet werden kann
            if game.passed_priority_count >= 2:
                if not game.stack_manager.is_empty():
                    # Beide Spieler passen -> oberstes Element des Stacks verrechnen
                    game.stack_manager.resolve_top_item()
                    game.check_state_based_actions()
                    game.grant_priority(game.active_player.player_id) # Erneut Priorität
                else:
                    # Beide Spieler passen bei leerem Stack -> zum nächsten Schritt gehen
                    game.phase_manager.advance_to_next_step()
                    action_in_step_loop = False # Verlasse die innere Schleife

        if game.players[0].life <= 0 or game.players[1].life <= 0:
            game_over = True

    print("Simulation beendet.")

if __name__ == "__main__":
    run_simulation()